import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx

from secureauth.config import TEXTBELT_KEY
from secureauth.db.supabase_client import latest_unverified_otp, mark_otp_verified
from secureauth.profiles import phone_for

logger = logging.getLogger(__name__)

OTP_TTL = timedelta(minutes=5)
_OTP_DIGITS = 6

# user_id -> (sha256 hex of the OTP, expiry). The code itself is never stored.
_otp_challenges: dict[str, tuple[str, datetime]] = {}


def trigger_verification(action: str, user_id: str) -> dict:
    """Simulate the step-up check for a decided action."""
    if action == "allow":
        return {
            "action": "allow",
            "user_id": user_id,
            "status": "success",
            "message": "Login allowed.",
        }
    if action == "challenge_otp":
        return _issue_otp(user_id)
    if action == "challenge_biometric":
        return {
            "action": "challenge_biometric",
            "user_id": user_id,
            "status": "pending",
            "challenge": "reprompt_biometric",
            "message": "Re-prompt the user for biometric authentication.",
        }
    if action == "block":
        logger.warning("Login blocked for user_id=%s", user_id)
        return {
            "action": "block",
            "user_id": user_id,
            "status": "denied",
            "message": "Login denied.",
        }
    logger.warning("Unknown verification action=%s for user_id=%s", action, user_id)
    return {
        "action": action,
        "user_id": user_id,
        "status": "denied",
        "message": "Login denied.",
    }


def verify_otp(user_id: str, submitted_otp: str) -> bool:
    """Return whether the submitted code matches the stored hash and is unexpired."""
    submitted_hash = _hash_otp(submitted_otp.strip())
    record = _otp_challenges.get(user_id)
    if record is not None:
        otp_hash, expires_at = record
        if datetime.now(timezone.utc) > expires_at:
            _otp_challenges.pop(user_id, None)
        elif hmac.compare_digest(submitted_hash, otp_hash):
            _otp_challenges.pop(user_id, None)
            _mark_remote_verified(user_id, submitted_hash)
            return True
    remote = _remote_challenge(user_id)
    if remote is None:
        return False
    expires_at = _parse_expiry(remote.get("expires_at"))
    if expires_at is None or datetime.now(timezone.utc) > expires_at:
        return False
    if not hmac.compare_digest(submitted_hash, str(remote.get("otp_hash", ""))):
        return False
    _otp_challenges.pop(user_id, None)
    mark_otp_verified(str(remote["id"]))
    return True


def _issue_otp(user_id: str) -> dict:
    otp = f"{secrets.randbelow(10**_OTP_DIGITS):0{_OTP_DIGITS}d}"
    expires_at = datetime.now(timezone.utc) + OTP_TTL
    otp_hash = _hash_otp(otp)
    _otp_challenges[user_id] = (otp_hash, expires_at)
    sms_sent, sms_error = _send_otp_sms(user_id, otp)
    if not sms_sent:
        logger.warning("OTP SMS was not sent for user_id=%s: %s", user_id, sms_error)
    return {
        "action": "challenge_otp",
        "user_id": user_id,
        "status": "pending",
        "otp_hash": otp_hash,
        "expires_at": expires_at.isoformat(),
        "sms_sent": sms_sent,
        "message": "A one-time passcode was sent by SMS."
        if sms_sent
        else "A one-time passcode was created, but the SMS could not be sent.",
    }


def _send_otp_sms(user_id: str, otp: str) -> tuple[bool, str]:
    phone = phone_for(user_id)
    if not phone:
        return False, "no phone on the demo account"
    try:
        response = httpx.post(
            "https://textbelt.com/text",
            data={
                "phone": phone,
                "message": (
                    f"SecureAuth: your login code is {otp}. "
                    "It expires in 5 minutes."
                ),
                "key": TEXTBELT_KEY,
            },
            timeout=15.0,
        )
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return False, exc.__class__.__name__
    if body.get("success"):
        return True, ""
    return False, str(body.get("error") or "SMS was not accepted")


def _remote_challenge(user_id: str) -> dict | None:
    try:
        return latest_unverified_otp(user_id)
    except Exception:
        logger.exception("Could not read the stored OTP challenge")
        return None


def _mark_remote_verified(user_id: str, otp_hash: str) -> None:
    remote = _remote_challenge(user_id)
    if remote is None or remote.get("otp_hash") != otp_hash:
        return
    try:
        mark_otp_verified(str(remote["id"]))
    except Exception:
        logger.exception("Could not mark the OTP challenge verified")


def _parse_expiry(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()
