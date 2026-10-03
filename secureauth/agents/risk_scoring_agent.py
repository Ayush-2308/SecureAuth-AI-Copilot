import json

import httpx

from secureauth.config import (
    LLM_API_KEY,
    LLM_PROVIDER,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
)
from secureauth.schemas.models import RiskAssessment, RiskFeatures

_NEW_DEVICE_WEIGHT = 0.3
_NEW_LOCATION_WEIGHT = 0.2
_UNUSUAL_HOUR_WEIGHT = 0.15
_HIGH_ATTEMPT_WEIGHT = 0.25
_BAD_IP_WEIGHT = 0.4
# The current attempt is already included, so one login is normal.
_HIGH_ATTEMPT_COUNT = 3
_GEMINI_MODEL = "gemini-3.8-flash"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_GEMINI_MODEL}:generateContent"
)
_GEMINI_PROVIDERS = {"google", "gemini"}
_REQUEST_TIMEOUT_SECONDS = 10.0

_ACTIONS = {
    "low": "allow",
    "medium": "challenge_otp",
    "high": "block",
}


def score_risk(features: RiskFeatures) -> RiskAssessment:
    """Score a login from fixed weights, then ask Gemini for audit reasons.

    The model never changes ``risk_score``. If the provider is not Google, the
    API key is missing, or the call fails, the reasons fall back to the same
    features so the assessment can still be stored.
    """
    risk_score = _risk_score(features)
    risk_level = _risk_level(risk_score)
    reasons = _audit_reasons(features, risk_score, risk_level)
    return RiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
        recommended_action=_ACTIONS[risk_level],
    )


def _risk_score(features: RiskFeatures) -> float:
    score = 0.0
    if features.is_new_device:
        score += _NEW_DEVICE_WEIGHT
    if features.is_new_location:
        score += _NEW_LOCATION_WEIGHT
    if features.is_unusual_hour:
        score += _UNUSUAL_HOUR_WEIGHT
    if features.login_attempts_last_hour >= _HIGH_ATTEMPT_COUNT:
        score += _HIGH_ATTEMPT_WEIGHT
    if features.ip_reputation_flag:
        score += _BAD_IP_WEIGHT
    return min(score, 1.0)


def _risk_level(risk_score: float) -> str:
    if risk_score >= RISK_THRESHOLD_HIGH:
        return "high"
    if risk_score >= RISK_THRESHOLD_MEDIUM:
        return "medium"
    return "low"


def _audit_reasons(
    features: RiskFeatures, risk_score: float, risk_level: str
) -> list[str]:
    if LLM_PROVIDER.strip().casefold() not in _GEMINI_PROVIDERS or not LLM_API_KEY:
        return _fallback_reasons(features)
    try:
        text = _call_gemini(_prompt(features, risk_score, risk_level))
        reasons = _parse_reasons(text)
    except (
        httpx.HTTPError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ):
        return _fallback_reasons(features)
    return reasons or _fallback_reasons(features)


def _call_gemini(prompt: str) -> str:
    response = httpx.post(
        _GEMINI_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": LLM_API_KEY,
        },
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        },
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["candidates"][0]["content"]["parts"][0]["text"]


def _prompt(features: RiskFeatures, risk_score: float, risk_level: str) -> str:
    minutes = features.time_since_last_login_minutes
    gap = "unknown" if minutes is None else f"{minutes:g} minutes"
    return (
        "Explain this completed login risk assessment for an audit log. "
        "The score and level are already final. Do not recalculate them, "
        "and do not mention signals that are not listed.\n"
        f"Risk score: {risk_score:.2f}\n"
        f"Risk level: {risk_level}\n"
        f"New device: {features.is_new_device}\n"
        f"New location: {features.is_new_location}\n"
        f"Minutes since last login: {gap}\n"
        f"Login attempts in the last hour: {features.login_attempts_last_hour}\n"
        f"Unusual hour for this user: {features.is_unusual_hour}\n"
        f"IP reputation flagged: {features.ip_reputation_flag}\n"
        'Return only JSON: {"reasons": ["short plain-English sentence"]}. '
        "Use 1 to 4 sentences. Describe only the features that raise or lower risk."
    )


def _parse_reasons(text: str) -> list[str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        cleaned = cleaned.removesuffix("```").strip()
    parsed = json.loads(cleaned)
    items = parsed.get("reasons") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return []
    reasons: list[str] = []
    for item in items:
        sentence = str(item).strip()
        if sentence:
            reasons.append(sentence)
    return reasons[:4]


def _fallback_reasons(features: RiskFeatures) -> list[str]:
    reasons: list[str] = []
    if features.is_new_device:
        reasons.append("The login is from a device this user has not used before.")
    if features.is_new_location:
        reasons.append("The login is from a location this user has not used before.")
    if features.is_unusual_hour:
        reasons.append("The login hour is outside this user's usual hours.")
    if features.login_attempts_last_hour >= _HIGH_ATTEMPT_COUNT:
        reasons.append(
            "This user has made "
            f"{features.login_attempts_last_hour} login attempts in the last hour."
        )
    if features.ip_reputation_flag:
        reasons.append("The IP address is flagged for poor reputation.")
    if not reasons:
        reasons.append("No elevated behavioral signals were found for this login.")
    return reasons
