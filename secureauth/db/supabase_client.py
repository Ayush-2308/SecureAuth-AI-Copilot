from datetime import datetime

from supabase import Client, create_client

from secureauth.config import SUPABASE_KEY, SUPABASE_URL
from secureauth.schemas.models import PipelineState

_client: Client | None = None


def get_supabase() -> Client:
    """Create the Supabase client from config on first use."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def get_user_login_history(user_id: str, limit: int = 20) -> list[dict]:
    """Return the user's most recent login rows, newest first."""
    response = (
        get_supabase()
        .table("login_history")
        .select("user_id,timestamp,ip_address,device_id,location,login_method")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return list(response.data or [])


def save_assessment(state: PipelineState) -> None:
    """Store the assessed login and its risk result.

    The login row is what later history lookups read. The assessment row is
    the audit record for this pipeline run.
    """
    if state.assessment is None:
        raise ValueError("Cannot save a pipeline state without an assessment")
    event = state.login_event
    client = get_supabase()
    client.table("login_history").insert(
        {
            "user_id": event.user_id,
            "timestamp": _as_iso(event.timestamp),
            "ip_address": event.ip_address,
            "device_id": event.device_id,
            "location": event.location,
            "login_method": event.login_method,
        }
    ).execute()
    client.table("risk_assessments").insert(
        {
            "event_id": state.event_id,
            "user_id": event.user_id,
            "risk_score": state.assessment.risk_score,
            "risk_level": state.assessment.risk_level,
            "recommended_action": state.assessment.recommended_action,
            "reasons": state.assessment.reasons,
        }
    ).execute()


def store_otp(user_id: str, otp_hash: str, expires_at: datetime) -> None:
    """Store a SHA-256 OTP hash. The plaintext code is never written."""
    get_supabase().table("otp_challenges").insert(
        {
            "user_id": user_id,
            "otp_hash": otp_hash,
            "expires_at": _as_iso(expires_at),
            "verified": False,
        }
    ).execute()


def latest_unverified_otp(user_id: str) -> dict | None:
    """Return the newest unused OTP hash for this user, if one exists."""
    response = (
        get_supabase()
        .table("otp_challenges")
        .select("id,otp_hash,expires_at,verified")
        .eq("user_id", user_id)
        .eq("verified", False)
        .order("expires_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = list(response.data or [])
    return rows[0] if rows else None


def mark_otp_verified(challenge_id: str) -> None:
    get_supabase().table("otp_challenges").update({"verified": True}).eq(
        "id", challenge_id
    ).execute()


def log_security_event(event_id: str, detail: str) -> None:
    """Append one security audit line for a pipeline event."""
    get_supabase().table("security_events").insert(
        {
            "event_id": event_id,
            "detail": detail,
        }
    ).execute()


def _as_iso(value: datetime) -> str:
    return value.isoformat()
