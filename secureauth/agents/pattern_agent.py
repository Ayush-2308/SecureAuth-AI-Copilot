from datetime import datetime, timedelta, timezone

from secureauth.db.supabase_client import get_user_login_history
from secureauth.schemas.models import LoginEvent, RiskFeatures

# A handful of prior logins is required before an hour can be called unusual.
_MIN_LOGINS_FOR_HOUR_PATTERN = 3
_ATTEMPT_WINDOW = timedelta(hours=1)


def extract_features(
    event: LoginEvent, user_history: list[dict] | None = None
) -> RiskFeatures:
    """Compare a login with the user's past logins and return risk features.

    When ``user_history`` is omitted, the most recent rows are loaded from
    Supabase. Passed-in rows use the same fields as ``LoginEvent``.
    ``timestamp`` may be a ``datetime`` or an ISO-8601 string. The current
    attempt is included in ``login_attempts_last_hour``. Hour-of-day is
    unusual only when the user already has a pattern and has not logged in
    during this hour before.
    """
    if user_history is None:
        user_history = get_user_login_history(event.user_id)
    records = _records_for_user(event, user_history)
    prior_timestamps = _prior_timestamps(event, records)

    return RiskFeatures(
        is_new_device=_is_new_device(event, records),
        is_new_location=_is_new_location(event, records),
        time_since_last_login_minutes=_minutes_since_last_login(
            event, prior_timestamps
        ),
        login_attempts_last_hour=_login_attempts_last_hour(event, records),
        is_unusual_hour=_is_unusual_hour(event, prior_timestamps),
        ip_reputation_flag=_ip_reputation_flag(event.ip_address),
    )


def _records_for_user(event: LoginEvent, user_history: list[dict]) -> list[dict]:
    matched: list[dict] = []
    for row in user_history:
        if not isinstance(row, dict):
            continue
        row_user = row.get("user_id")
        if row_user is not None and str(row_user) != event.user_id:
            continue
        matched.append(row)
    return matched


def _is_new_device(event: LoginEvent, records: list[dict]) -> bool:
    known = {
        str(row["device_id"])
        for row in records
        if row.get("device_id") not in (None, "")
    }
    return event.device_id not in known


def _is_new_location(event: LoginEvent, records: list[dict]) -> bool:
    current = _normalize_location(event.location)
    if current is None:
        return False
    known = {
        location
        for row in records
        if (location := _normalize_location(row.get("location"))) is not None
    }
    return current not in known


def _minutes_since_last_login(
    event: LoginEvent, prior_timestamps: list[datetime]
) -> float | None:
    if not prior_timestamps:
        return None
    delta = event.timestamp - max(prior_timestamps)
    return delta.total_seconds() / 60.0


def _login_attempts_last_hour(event: LoginEvent, records: list[dict]) -> int:
    window_start = event.timestamp - _ATTEMPT_WINDOW
    count = 0
    current_seen = False
    for row in records:
        timestamp = _event_timestamp(row.get("timestamp"), event.timestamp)
        if timestamp is None or timestamp < window_start or timestamp > event.timestamp:
            continue
        count += 1
        if _is_same_attempt(event, row, timestamp):
            current_seen = True
    if not current_seen:
        count += 1
    return count


def _is_unusual_hour(event: LoginEvent, prior_timestamps: list[datetime]) -> bool:
    if len(prior_timestamps) < _MIN_LOGINS_FOR_HOUR_PATTERN:
        return False
    typical_hours = {timestamp.hour for timestamp in prior_timestamps}
    return event.timestamp.hour not in typical_hours


def _ip_reputation_flag(ip_address: str) -> bool:
    # TODO: replace this placeholder with a real IP reputation API lookup.
    del ip_address
    return False


def _prior_timestamps(event: LoginEvent, records: list[dict]) -> list[datetime]:
    timestamps: list[datetime] = []
    for row in records:
        timestamp = _event_timestamp(row.get("timestamp"), event.timestamp)
        if timestamp is not None and timestamp < event.timestamp:
            timestamps.append(timestamp)
    return timestamps


def _event_timestamp(value: object, reference: datetime) -> datetime | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return _align_timezone(parsed, reference)


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _align_timezone(timestamp: datetime, reference: datetime) -> datetime:
    if reference.tzinfo is None:
        if timestamp.tzinfo is None:
            return timestamp
        return timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=reference.tzinfo)
    return timestamp.astimezone(reference.tzinfo)


def _normalize_location(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.casefold()


def _is_same_attempt(event: LoginEvent, row: dict, timestamp: datetime) -> bool:
    return (
        timestamp == event.timestamp
        and str(row.get("device_id", "")) == event.device_id
        and str(row.get("ip_address", "")) == event.ip_address
    )
