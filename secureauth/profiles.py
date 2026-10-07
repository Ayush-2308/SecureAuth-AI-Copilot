"""Demo account used when showing the login check to someone else."""

DEMO_ACCOUNT = {
    "user_id": "Ayush",
    "name": "Ayush",
    "phone": "+918273126155",
    "usual_device_id": "phone-ayush",
    "usual_location": "Delhi",
}


def matches_demo_user(user_id: str) -> bool:
    return user_id.strip().casefold() == DEMO_ACCOUNT["user_id"].casefold()


def phone_for(user_id: str) -> str | None:
    if matches_demo_user(user_id):
        return DEMO_ACCOUNT["phone"]
    return None


def needs_phone_otp(user_id: str, device_id: str, location: str | None) -> bool:
    """Ayush's own phone gets a code when this login is not his usual device or city."""
    if not matches_demo_user(user_id):
        return False
    usual_device = DEMO_ACCOUNT["usual_device_id"].casefold()
    if device_id.strip().casefold() != usual_device:
        return True
    if location and location.strip():
        usual_location = DEMO_ACCOUNT["usual_location"].casefold()
        if location.strip().casefold() != usual_location:
            return True
    return False
