from datetime import datetime
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from secureauth.agents.decision_agent import decide_action
from secureauth.agents.pattern_agent import extract_features as build_features
from secureauth.agents.risk_scoring_agent import score_risk as assess_risk
from secureauth.agents.verification_agent import trigger_verification
from secureauth.db.supabase_client import (
    log_security_event,
    save_assessment,
    store_otp,
)
from secureauth.schemas.models import LoginEvent, PipelineState


def intake(state: PipelineState) -> dict:
    return {"status": "received"}


def extract_features(state: PipelineState) -> dict:
    features = build_features(state.login_event)
    return {"features": features, "status": "features_extracted"}


def score_risk(state: PipelineState) -> dict:
    if state.features is None:
        raise ValueError("score_risk requires features from the previous step")
    assessment = assess_risk(state.features)
    return {"assessment": assessment, "status": "scored"}


def decide(state: PipelineState) -> dict:
    if state.assessment is None or state.features is None:
        raise ValueError("decide requires features and an assessment")
    action = decide_action(
        state.assessment,
        login_attempts_last_hour=state.features.login_attempts_last_hour,
    )
    assessment = state.assessment.model_copy(update={"recommended_action": action})
    return {"assessment": assessment, "status": "decided"}


def verify(state: PipelineState) -> dict:
    if state.assessment is None:
        raise ValueError("verify requires a decided assessment")
    result = trigger_verification(
        state.assessment.recommended_action,
        state.login_event.user_id,
    )
    return {"verification_result": result, "status": "verified"}


def store(state: PipelineState) -> dict:
    final = state.model_copy(update={"status": "stored"})
    save_assessment(final)
    _store_issued_otp(final)
    log_security_event(final.event_id, _security_detail(final))
    return {"status": "stored"}


def _store_issued_otp(state: PipelineState) -> None:
    result = state.verification_result or {}
    if result.get("action") != "challenge_otp":
        return
    otp_hash = result.get("otp_hash")
    expires_at = result.get("expires_at")
    if not isinstance(otp_hash, str) or not otp_hash or expires_at is None:
        return
    if isinstance(expires_at, str):
        text = expires_at.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        expires_at = datetime.fromisoformat(text)
    if not isinstance(expires_at, datetime):
        return
    store_otp(state.login_event.user_id, otp_hash, expires_at)


def _security_detail(state: PipelineState) -> str:
    assessment = state.assessment
    user_id = state.login_event.user_id
    if assessment is None:
        return f"Login for {user_id} finished with status {state.status}."
    return (
        f"Login for {user_id} scored {assessment.risk_score:.2f} "
        f"({assessment.risk_level}); action {assessment.recommended_action}."
    )


def _route_after_decide(state: PipelineState) -> str:
    action = state.assessment.recommended_action if state.assessment else ""
    if action == "block":
        return "store"
    return "verify"


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("intake", intake)
    graph.add_node("extract_features", extract_features)
    graph.add_node("score_risk", score_risk)
    graph.add_node("decide", decide)
    graph.add_node("verify", verify)
    graph.add_node("store", store)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "extract_features")
    graph.add_edge("extract_features", "score_risk")
    graph.add_edge("score_risk", "decide")
    graph.add_conditional_edges(
        "decide",
        _route_after_decide,
        {"verify": "verify", "store": "store"},
    )
    graph.add_edge("verify", "store")
    graph.add_edge("store", END)
    return graph.compile()


pipeline = build_graph()


def run_pipeline(event: LoginEvent) -> PipelineState:
    """Run a login event through intake, scoring, decision, verification, and store."""
    initial = PipelineState(
        event_id=str(uuid4()),
        login_event=event,
        status="pending",
    )
    result = pipeline.invoke(initial)
    if isinstance(result, PipelineState):
        return result
    return PipelineState.model_validate(result)
