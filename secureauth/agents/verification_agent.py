import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

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
    record = _otp_challenges.get(user_id)
    if record is None:
        return False
    otp_hash, expires_at = record
    if datetime.now(timezone.utc) > expires_at:
        _otp_challenges.pop(user_id, None)
        return False
    submitted_hash = _hash_otp(submitted_otp.strip())
    if not hmac.compare_digest(submitted_hash, otp_hash):
        return False
    _otp_challenges.pop(user_id, None)
    return True


def _issue_otp(user_id: str) -> dict:
    otp = f"{secrets.randbelow(10**_OTP_DIGITS):0{_OTP_DIGITS}d}"
    expires_at = datetime.now(timezone.utc) + OTP_TTL
    _otp_challenges[user_id] = (_hash_otp(otp), expires_at)
    return {
        "action": "challenge_otp",
        "user_id": user_id,
        "status": "pending",
        "expires_at": expires_at.isoformat(),
        "message": "A one-time passcode was issued.",
    }


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()
