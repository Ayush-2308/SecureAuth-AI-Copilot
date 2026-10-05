# SecureAuth AI Copilot

SecureAuth scores a login from the user's own history, then decides whether to allow it, step up authentication, or block it.

The pipeline extracts behavioral features, computes a rule-based risk score, and asks an LLM only for a short human-readable explanation. LangGraph then runs the steps in order: intake, feature extraction, risk scoring, decision, verification, and store. A blocked login skips verification and goes straight to storage.

The verification step mirrors real biometric and one-time-passcode flows from production fintech apps. An OTP challenge issues a code that is stored only as a SHA-256 hash. A biometric challenge tells the client to prompt the user again. The login API confirms that a challenge was sent and never returns the code.

## Setup

Use Python 3.11 or newer from the project root.

```bash
python -m pip install -r secureauth/requirements.txt
copy secureauth\.env.example .env
```

Fill in `.env`:

- `SUPABASE_URL` and `SUPABASE_KEY` for history and audit storage
- `LLM_API_KEY` and `LLM_PROVIDER=google` for the written risk reasons
- `RISK_THRESHOLD_MEDIUM` (default `0.3`) and `RISK_THRESHOLD_HIGH` (default `0.7`)

In the Supabase SQL editor, run `secureauth/db/migrations.sql`. That creates `login_history`, `risk_assessments`, `otp_challenges`, and `security_events`.

## Run locally

```bash
uvicorn main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

## Example requests

Submit a login:

```bash
curl.exe -X POST http://127.0.0.1:8000/login-event -H "Content-Type: application/json" -d "{\"user_id\":\"user-1\",\"timestamp\":\"2026-10-05T11:00:00Z\",\"ip_address\":\"203.0.113.10\",\"device_id\":\"device-1\",\"device_type\":\"mobile\",\"location\":\"Mumbai\",\"login_method\":\"password\"}"
```

A first login from a new device and location can look like this:

```json
{
  "assessment": {
    "risk_score": 0.5,
    "risk_level": "medium",
    "reasons": [
      "The login is from a device this user has not used before.",
      "The login is from a location this user has not used before."
    ],
    "recommended_action": "challenge_otp"
  },
  "recommended_action": "challenge_otp",
  "challenge_sent": true,
  "message": "A one-time passcode challenge was sent."
}
```

Submit the code the user received. The response is only success or failure:

```bash
curl.exe -X POST http://127.0.0.1:8000/verify-otp -H "Content-Type: application/json" -d "{\"user_id\":\"user-1\",\"otp\":\"123456\"}"
```

```json
{
  "success": false
}
```
