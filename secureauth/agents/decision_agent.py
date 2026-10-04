from secureauth.schemas.models import RiskAssessment

# More than this many attempts in the last hour is a block, whatever the score.
BLOCK_ATTEMPT_THRESHOLD = 10

_ACTIONS = {
    "low": "allow",
    "medium": "challenge_otp",
    "high": "challenge_biometric",
}


def decide_action(
    assessment: RiskAssessment,
    login_attempts_last_hour: int | None = None,
) -> str:
    """Map a risk level to an action, then apply the attempt-count block.

    ``login_attempts_last_hour`` is not on ``RiskAssessment``. Pass the value
    from ``RiskFeatures`` so a burst of attempts can override the level.
    """
    if (
        login_attempts_last_hour is not None
        and login_attempts_last_hour > BLOCK_ATTEMPT_THRESHOLD
    ):
        return "block"
    return _ACTIONS[assessment.risk_level]
