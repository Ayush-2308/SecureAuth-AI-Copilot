import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from secureauth.agents.verification_agent import verify_otp
from secureauth.db.supabase_client import log_security_event
from secureauth.graph import run_pipeline
from secureauth.profiles import DEMO_ACCOUNT, matches_demo_user
from secureauth.schemas.models import LoginEvent, RiskAssessment

logger = logging.getLogger("secureauth.api")

app = FastAPI(title="SecureAuth AI Copilot")

_PAGE = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/")
def home() -> FileResponse:
    return FileResponse(_PAGE)


@app.get("/demo-profile")
def demo_profile() -> dict:
    phone = DEMO_ACCOUNT["phone"]
    return {
        "name": DEMO_ACCOUNT["name"],
        "user_id": DEMO_ACCOUNT["user_id"],
        "phone": phone,
        "phone_hint": f"ending {phone[-4:]}",
        "usual_device_id": DEMO_ACCOUNT["usual_device_id"],
        "usual_location": DEMO_ACCOUNT["usual_location"],
    }

_CHALLENGE_ACTIONS = {"challenge_otp", "challenge_biometric"}


class LoginEventResponse(BaseModel):
    assessment: RiskAssessment
    recommended_action: str
    challenge_sent: bool
    message: str


class VerifyOtpRequest(BaseModel):
    user_id: str
    otp: str


class VerifyOtpResponse(BaseModel):
    success: bool


@app.post("/login-event", response_model=LoginEventResponse)
def login_event(event: LoginEvent) -> LoginEventResponse:
    try:
        state = run_pipeline(event)
        if state.assessment is None:
            raise RuntimeError("Pipeline finished without a risk assessment")
        return _login_response(state.assessment, state)
    except Exception as exc:
        _record_failure("login-event", event.user_id, exc)
        raise HTTPException(status_code=500, detail=_public_error(exc, "Login assessment failed")) from exc


@app.post("/verify-otp", response_model=VerifyOtpResponse)
def verify_otp_endpoint(body: VerifyOtpRequest) -> VerifyOtpResponse:
    try:
        success = verify_otp(body.user_id, body.otp)
    except Exception as exc:
        _record_failure("verify-otp", body.user_id, exc)
        raise HTTPException(status_code=500, detail="OTP verification failed") from exc
    return VerifyOtpResponse(success=success)


def _login_response(assessment: RiskAssessment, state) -> LoginEventResponse:
    action = assessment.recommended_action
    challenge_sent = action in _CHALLENGE_ACTIONS
    sms_sent = bool((state.verification_result or {}).get("sms_sent"))
    if action == "challenge_otp" and matches_demo_user(state.login_event.user_id):
        hint = DEMO_ACCOUNT["phone"][-4:]
        if sms_sent:
            message = f"OTP sent to Ayush's phone ending {hint}."
        else:
            message = (
                f"OTP should go to Ayush's phone ending {hint}, "
                "but the free SMS for today was already used."
            )
    elif action == "challenge_otp":
        message = "A one-time passcode challenge was sent."
    elif action == "challenge_biometric":
        message = "A biometric challenge was sent."
    elif action == "block":
        message = "Login denied."
    else:
        message = "Login allowed."
    return LoginEventResponse(
        assessment=assessment,
        recommended_action=action,
        challenge_sent=challenge_sent,
        message=message,
    )


def _public_error(exc: Exception, fallback: str) -> str:
    if "SUPABASE_URL and SUPABASE_KEY must be set" in str(exc):
        return "Add SUPABASE_URL and SUPABASE_KEY in a .env file, then restart the app."
    return fallback


def _record_failure(operation: str, user_id: str, exc: Exception) -> None:
    detail = f"{operation} failed for user {user_id}: {exc.__class__.__name__}"
    logger.exception(detail)
    try:
        log_security_event(str(uuid4()), detail)
    except Exception:
        logger.exception("Could not write the security event for %s", operation)
