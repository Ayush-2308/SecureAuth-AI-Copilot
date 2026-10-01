from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class LoginEvent(BaseModel):
    user_id: str
    timestamp: datetime
    ip_address: str
    device_id: str
    device_type: str
    location: Optional[str] = None
    login_method: str


class RiskFeatures(BaseModel):
    is_new_device: bool
    is_new_location: bool
    time_since_last_login_minutes: Optional[float] = None
    login_attempts_last_hour: int
    is_unusual_hour: bool
    ip_reputation_flag: bool


class RiskAssessment(BaseModel):
    risk_score: float
    risk_level: Literal["low", "medium", "high"]
    reasons: list[str]
    recommended_action: Literal[
        "allow", "challenge_otp", "challenge_biometric", "block"
    ]


class PipelineState(BaseModel):
    event_id: str
    login_event: LoginEvent
    features: Optional[RiskFeatures] = None
    assessment: Optional[RiskAssessment] = None
    verification_result: Optional[dict] = None
    status: str
