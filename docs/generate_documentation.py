"""Build the SecureAuth project documentation PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "SecureAuth-AI-Copilot-Documentation.pdf"

INK = colors.HexColor("#1b2430")
TEAL = colors.HexColor("#0f6e6e")
MUTED = colors.HexColor("#5d6b7a")
RULE = colors.HexColor("#d9d1c5")
ROW = colors.HexColor("#f6f3ee")


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        "CoverKicker", fontName="Times-Bold", fontSize=11, textColor=TEAL,
        tracking=1.2, spaceAfter=8,
    ))
    base.add(ParagraphStyle(
        "CoverTitle", fontName="Times-Bold", fontSize=28, leading=32,
        textColor=INK, spaceAfter=8,
    ))
    base.add(ParagraphStyle(
        "CoverSub", fontName="Times-Italic", fontSize=12, leading=16,
        textColor=MUTED, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        "H1", fontName="Times-Bold", fontSize=16, leading=20,
        textColor=TEAL, spaceBefore=14, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        "H2", fontName="Times-Bold", fontSize=13, leading=16,
        textColor=INK, spaceBefore=10, spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=10.5, leading=14,
        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        "BulletBody", fontName="Times-Roman", fontSize=10.5, leading=14,
        textColor=INK, leftIndent=12, spaceAfter=2,
    ))
    base.add(ParagraphStyle(
        "Cell", fontName="Times-Roman", fontSize=8.5, leading=11, textColor=INK,
    ))
    base.add(ParagraphStyle(
        "CellHead", fontName="Times-Bold", fontSize=8.5, leading=11, textColor=colors.white,
    ))
    base.add(ParagraphStyle(
        "Footer", fontName="Times-Roman", fontSize=8, textColor=MUTED, alignment=TA_LEFT,
    ))
    return base


def P(text, style):
    return Paragraph(text, style)


def table(headers, rows, col_widths, s):
    data = [[P(h, s["CellHead"]) for h in headers]]
    for row in rows:
        data.append([P(str(cell), s["Cell"]) for cell in row])
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(1.5)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "SecureAuth AI Copilot  |  Project documentation")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    s = styles()
    story = []
    story.append(Spacer(1, 28 * mm))
    story.append(P("PROJECT DOCUMENTATION", s["CoverKicker"]))
    story.append(P("SecureAuth AI Copilot", s["CoverTitle"]))
    story.append(P(
        "Behavioral login-risk scoring, step-up verification, and an audit trail. "
        "The score is computed by fixed rules. A language model only writes the explanation.",
        s["CoverSub"],
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(P("Document date: 6 October 2026", s["Body"]))
    story.append(P("Repository: Ayush-2308/SecureAuth-AI-Copilot", s["Body"]))
    story.append(P("Status: local FastAPI application with Supabase storage", s["Body"]))
    story.append(PageBreak())

    story.append(P("1. What this project is", s["H1"]))
    story.append(P(
        "SecureAuth AI Copilot checks one login attempt against that user's own past logins. "
        "It answers a single question: does this attempt look like the user's normal behavior, "
        "or should the application allow it, ask for a second proof, or stop it?",
        s["Body"],
    ))
    story.append(P(
        "The product is a small pipeline, not a chatbot. LangGraph runs six steps in order. "
        "Python rules compute a risk score from 0 to 1. Google Gemini may write one to four "
        "plain-English reasons for the audit log. Gemini never changes the score. "
        "A web page and two HTTP endpoints let a person submit a login and, when required, a one-time code.",
        s["Body"],
    ))
    story.append(P("The system produces one of four final actions:", s["Body"]))
    for line in [
        "allow - the login may continue.",
        "challenge_otp - ask for a 6-digit one-time code.",
        "challenge_biometric - ask the client to prompt fingerprint or face unlock again.",
        "block - deny the login. This happens when there have been more than 10 attempts in the last hour.",
    ]:
        story.append(P("- " + line, s["BulletBody"]))

    story.append(P("2. A concrete example", s["H1"]))
    story.append(P(
        "Rahul normally signs in from Mumbai on the phone named phone-rahul. "
        "A new attempt arrives from the same city, the same IP, but a device id the history has never seen: tablet-new. "
        "There have also been 5 attempts in the last hour.",
        s["Body"],
    ))
    story.append(table(
        ["Signal", "Result", "Weight added"],
        [
            ["New device", "Yes", "+0.30"],
            ["New location", "No, Mumbai is known", "+0.00"],
            ["Unusual hour", "Not enough of a personal hour pattern yet", "+0.00"],
            ["Attempts in the last hour", "5, which is at least 3", "+0.25"],
            ["Bad IP reputation", "Not flagged (placeholder)", "+0.00"],
            ["Score", "0.55, capped at 1.00", "medium"],
        ],
        [48 * mm, 78 * mm, 48 * mm],
        s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "0.55 is at or above the medium threshold of 0.30 and below the high threshold of 0.70, "
        "so the level is medium. The decision step maps medium to challenge_otp. "
        "The API confirms that a code was sent. It does not return the digits. "
        "If the submitted code's SHA-256 hash matches the stored hash before expiry, the screen says the login can continue.",
        s["Body"],
    ))

    story.append(P("3. Architecture", s["H1"]))
    story.append(P(
        "A browser page posts a login to FastAPI. FastAPI calls run_pipeline. "
        "LangGraph moves one PipelineState through the nodes below. "
        "The pattern agent reads recent rows from Supabase. "
        "The scoring agent adds weights locally and optionally calls Gemini for reasons. "
        "The decision agent chooses the action. "
        "Unless the action is block, the verification agent issues a challenge. "
        "The store node writes the login, the assessment, an OTP hash when one was issued, and a security-event line.",
        s["Body"],
    ))
    story.append(table(
        ["Layer", "Responsibility", "Code"],
        [
            ["Web UI", "Login form, decision panel, OTP box", "static/index.html"],
            ["HTTP API", "POST /login-event and POST /verify-otp", "main.py"],
            ["Orchestration", "StateGraph and run_pipeline", "secureauth/graph.py"],
            ["Behavior", "Compare this login with history", "agents/pattern_agent.py"],
            ["Score", "Weights, level, LLM reasons", "agents/risk_scoring_agent.py"],
            ["Decision", "Final action, including the hard block", "agents/decision_agent.py"],
            ["Verification", "OTP hash, biometric prompt, deny", "agents/verification_agent.py"],
            ["Database", "Supabase reads and writes", "db/supabase_client.py"],
            ["Schema", "Pydantic models", "schemas/models.py"],
            ["Settings", "Environment variables", "config.py"],
        ],
        [32 * mm, 78 * mm, 64 * mm],
        s,
    ))

    story.append(P("4. LangGraph pipeline", s["H1"]))
    story.append(P(
        "The graph state is the Pydantic model PipelineState. "
        "run_pipeline creates an event id and starts the state as pending. "
        "Each node returns only the fields it changes.",
        s["Body"],
    ))
    story.append(table(
        ["Order", "Node", "What it writes"],
        [
            ["1", "intake", "status = received"],
            ["2", "extract_features", "RiskFeatures from Supabase history"],
            ["3", "score_risk", "RiskAssessment, including a provisional action"],
            ["4", "decide", "Replaces recommended_action with the final action"],
            ["5", "verify", "verification_result. Skipped when the action is block"],
            ["6", "store", "login_history, risk_assessments, otp hash, security_events"],
        ],
        [18 * mm, 40 * mm, 116 * mm],
        s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "The conditional edge sits after decide. If recommended_action is block, the next node is store. "
        "Every other action goes to verify, then store. The returned status is stored.",
        s["Body"],
    ))

    story.append(P("5. Behavioral features", s["H1"]))
    story.append(P(
        "extract_features loads up to 20 of the user's most recent login_history rows when the caller does not pass history. "
        "Rows for a different user_id are ignored. Timestamps may be datetimes or ISO-8601 strings.",
        s["Body"],
    ))
    story.append(table(
        ["Feature", "Rule"],
        [
            ["is_new_device", "True when this device_id has not appeared in history."],
            ["is_new_location", "True when the current location is present and does not match a previous location, ignoring case. A missing location is not treated as new."],
            ["time_since_last_login_minutes", "Minutes since the latest earlier login. None when there is no earlier login."],
            ["login_attempts_last_hour", "Logins in the 60 minutes up to this attempt, including this attempt, without counting this attempt twice."],
            ["is_unusual_hour", "True only after at least 3 earlier logins, and only when this clock hour has never appeared in them."],
            ["ip_reputation_flag", "Always false for now. A real reputation lookup is still a TODO."],
        ],
        [52 * mm, 122 * mm],
        s,
    ))

    story.append(P("6. Risk metrics", s["H1"]))
    story.append(P(
        "The score is a sum of weights. It is capped at 1.0. "
        "These numbers are the project metrics. They are not learned by the model.",
        s["Body"],
    ))
    story.append(table(
        ["Metric", "Value", "When it applies"],
        [
            ["New device weight", "0.30", "is_new_device is true"],
            ["New location weight", "0.20", "is_new_location is true"],
            ["Unusual hour weight", "0.15", "is_unusual_hour is true"],
            ["High attempt weight", "0.25", "login_attempts_last_hour is 3 or more"],
            ["Bad IP weight", "0.40", "ip_reputation_flag is true"],
            ["Score cap", "1.00", "The sum cannot exceed this"],
            ["Medium threshold", "0.30", "score >= 0.30 and < 0.70 is medium. Configurable."],
            ["High threshold", "0.70", "score >= 0.70 is high. Configurable."],
            ["Low band", "below 0.30", "Everything under the medium threshold"],
            ["Hard attempt block", "more than 10", "Overrides the level and forces block"],
            ["Hour-pattern minimum", "3 earlier logins", "Before that, the hour is not called unusual"],
            ["History window", "20 rows", "Most recent logins for that user"],
            ["OTP lifetime", "5 minutes", "After that, verify_otp returns false"],
            ["OTP length", "6 digits", "Generated with secrets, not the random module"],
            ["Gemini timeout", "10 seconds", "If the call fails, rule-written reasons are used"],
        ],
        [48 * mm, 36 * mm, 90 * mm],
        s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "Maximum raw sum is 0.30 + 0.20 + 0.15 + 0.25 + 0.40 = 1.30, which is stored as 1.00. "
        "A brand-new user with a location is typically 0.50: new device 0.30 plus new location 0.20. "
        "That is medium, so the final action is challenge_otp.",
        s["Body"],
    ))

    story.append(P("7. How the final action is chosen", s["H1"]))
    story.append(P(
        "score_risk first attaches a provisional action: low becomes allow, medium becomes challenge_otp, "
        "and high becomes block. The decide node then replaces that action. "
        "The value stored in Supabase and returned by the API is the decision-agent result, not the provisional one.",
        s["Body"],
    ))
    story.append(table(
        ["Condition", "Final action"],
        [
            ["More than 10 attempts in the last hour", "block, even if the score is low"],
            ["Level low, and attempts are 10 or fewer", "allow"],
            ["Level medium, and attempts are 10 or fewer", "challenge_otp"],
            ["Level high, and attempts are 10 or fewer", "challenge_biometric"],
        ],
        [95 * mm, 79 * mm],
        s,
    ))

    story.append(P("8. Verification", s["H1"]))
    story.append(P(
        "This step mirrors the step-up checks used by production banking and fintech apps. "
        "allow returns success. challenge_biometric returns a payload that tells the client to prompt biometric authentication again. "
        "block is logged and returns denied, and the graph skips this node entirely. "
        "challenge_otp creates a 6-digit code, stores only SHA-256(code), and sets a 5-minute expiry. "
        "The plaintext code is not written to Supabase and is not included in the HTTP response. "
        "verify_otp hashes the submitted code, compares it in constant time, rejects an expired or unknown code, "
        "and deletes a matching code so it cannot be reused. The live check uses the in-memory challenge created by this server process.",
        s["Body"],
    ))

    story.append(P("9. Supabase tables", s["H1"]))
    story.append(P(
        "Create these tables by running secureauth/db/migrations.sql in the Supabase SQL editor. "
        "Each table also has a uuid primary key generated by the database.",
        s["Body"],
    ))
    story.append(table(
        ["Table", "Written by", "Important columns"],
        [
            ["login_history", "save_assessment", "user_id, timestamp, ip_address, device_id, location, login_method"],
            ["risk_assessments", "save_assessment", "event_id, user_id, risk_score, risk_level, recommended_action, reasons jsonb, created_at"],
            ["otp_challenges", "store_otp", "user_id, otp_hash, expires_at, verified"],
            ["security_events", "log_security_event", "event_id, detail, created_at"],
        ],
        [38 * mm, 38 * mm, 98 * mm],
        s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "get_user_login_history reads login_history for one user, newest first, default limit 20. "
        "Failed API calls also try to write a security_events row. The detail names the operation and the exception type. It does not include the one-time code.",
        s["Body"],
    ))

    story.append(P("10. API and user interface", s["H1"]))
    story.append(P("GET / serves static/index.html. The page is a login form and a decision panel.", s["Body"]))
    story.append(table(
        ["Method and path", "Body", "Success response"],
        [
            ["POST /login-event", "LoginEvent JSON", "assessment, recommended_action, challenge_sent, message. No OTP digits."],
            ["POST /verify-otp", "user_id and otp", "success true or false"],
        ],
        [40 * mm, 42 * mm, 92 * mm],
        s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "LoginEvent fields are user_id, timestamp, ip_address, device_id, device_type, optional location, and login_method. "
        "A first login from a new device and a new place can return risk_score 0.5, risk_level medium, "
        "recommended_action challenge_otp, and challenge_sent true. "
        "If the same device and place are used again and the other signals stay quiet, the score can be 0.00 and the action is allow, "
        "which the page shows as \"Login can continue.\" "
        "After a matching OTP, the decision panel is replaced with the same sentence.",
        s["Body"],
    ))

    story.append(P("11. Technology used", s["H1"]))
    story.append(table(
        ["Piece", "Role in this project"],
        [
            ["Python 3.11+", "Application language"],
            ["FastAPI", "HTTP API"],
            ["Uvicorn", "Local server"],
            ["Pydantic", "LoginEvent, RiskFeatures, RiskAssessment, PipelineState"],
            ["LangGraph", "StateGraph that orders the six nodes"],
            ["langchain-core", "Declared dependency of the agent stack"],
            ["Google Gemini", "gemini-3.8-flash, reasons only, provider google"],
            ["httpx", "Gemini REST call"],
            ["Supabase", "Postgres tables behind the data API"],
            ["python-dotenv", "Loads the project-root .env file"],
            ["hashlib SHA-256 and hmac", "OTP storage and constant-time compare"],
            ["secrets", "OTP generation"],
            ["Browser page", "HTML, CSS, and JavaScript in one file. No frontend framework."],
        ],
        [48 * mm, 126 * mm],
        s,
    ))

    story.append(P("12. Configuration", s["H1"]))
    story.append(P(
        "config.py loads .env from the repository root. Do not commit that file. "
        "secureauth/.env.example lists the names only.",
        s["Body"],
    ))
    story.append(table(
        ["Variable", "Purpose", "Default"],
        [
            ["SUPABASE_URL", "Project URL", "empty, required to run"],
            ["SUPABASE_KEY", "API key allowed to read and write the four tables", "empty, required to run"],
            ["LLM_API_KEY", "Gemini key for audit reasons", "empty; rules still score the login"],
            ["LLM_PROVIDER", "Must be google or gemini to call the model", "google in the example file"],
            ["RISK_THRESHOLD_MEDIUM", "Start of the medium band", "0.3"],
            ["RISK_THRESHOLD_HIGH", "Start of the high band", "0.7"],
        ],
        [52 * mm, 88 * mm, 34 * mm],
        s,
    ))

    story.append(P("13. How to run", s["H1"]))
    for line in [
        "From the repository root, install secureauth/requirements.txt.",
        "Copy secureauth/.env.example to .env and fill in the Supabase and Gemini values.",
        "Run secureauth/db/migrations.sql in the Supabase SQL editor.",
        "Start the app with: python -m uvicorn main:app --host 127.0.0.1 --port 8001",
        "Open http://127.0.0.1:8001/ . Port 8000 may already be used by another local app, which is why 8001 is the safe local port.",
        "Submit a login. If the decision is challenge_otp, enter the code for that same user id. Do not submit the login form again before verifying, or a new code replaces the old one.",
    ]:
        story.append(P("- " + line, s["BulletBody"]))

    story.append(P("14. Repository map", s["H1"]))
    story.append(table(
        ["Path", "Contents"],
        [
            ["main.py", "FastAPI application"],
            ["static/index.html", "Login and decision page"],
            ["README.md", "Short setup and curl examples"],
            ["secureauth/graph.py", "Compiled LangGraph pipeline"],
            ["secureauth/config.py", "Environment settings"],
            ["secureauth/schemas/models.py", "Shared data models"],
            ["secureauth/agents/", "Pattern, scoring, decision, and verification"],
            ["secureauth/db/supabase_client.py", "Database helpers"],
            ["secureauth/db/migrations.sql", "Table definitions"],
            ["docs/SecureAuth-AI-Copilot-Documentation.pdf", "This document"],
        ],
        [78 * mm, 96 * mm],
        s,
    ))

    story.append(P("15. Limits", s["H1"]))
    for line in [
        "IP reputation is not a live lookup. The flag stays false, so its 0.40 weight is unused until that TODO is replaced.",
        "Unusual hour needs three earlier logins. A first-time user is not marked unusual just because the clock says 2:15.",
        "Only the latest 20 logins are read. A longer attack spread outside that window is not fully counted.",
        "OTP verification on the running API checks the code held in that server process. Restarting the process drops codes that have not yet been verified.",
        "The HTTP API never returns the OTP. A demo operator cannot read the digits from the JSON response.",
        "Gemini explains the features. If the key is missing or the call fails, the same features are written as fixed sentences and the score is unchanged.",
    ]:
        story.append(P("- " + line, s["BulletBody"]))

    story.append(Spacer(1, 6 * mm))
    story.append(P(
        "End of document. The numbers in section 6 and the action table in section 7 match the code as of 6 October 2026.",
        s["Body"],
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="SecureAuth AI Copilot - Project Documentation",
        author="SecureAuth AI Copilot",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)
    print(OUT.stat().st_size)


if __name__ == "__main__":
    build()
