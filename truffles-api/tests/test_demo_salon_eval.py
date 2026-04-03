from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import yaml

from app.routers.webhook import _legacy as webhook_router
from app.routers.webhook import context_manager as webhook_context
from app.routers.webhook import response as webhook_response
from app.routers.webhook import trace as webhook_trace
from app.services.state_machine import ConversationState

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"
EVAL_GOLDEN_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL_GOLDEN.yaml"


@pytest.fixture(scope="module")
def eval_data() -> dict:
    return yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8")) or {}


@pytest.fixture(scope="module")
def eval_golden_data() -> dict:
    return yaml.safe_load(EVAL_GOLDEN_PATH.read_text(encoding="utf-8")) or {}


def _normalize_turns(turns: object, case_id: str) -> list[dict]:
    if not turns:
        return []
    if not isinstance(turns, list):
        raise AssertionError(f"{case_id}: turns must be a list")
    normalized: list[dict] = []
    for idx, turn in enumerate(turns, start=1):
        if isinstance(turn, str):
            user_text = turn
            expected = None
        elif isinstance(turn, dict):
            user_text = turn.get("user") or turn.get("message") or turn.get("text")
            expected = turn.get("expected")
        else:
            raise AssertionError(f"{case_id}: turn {idx} must be a string or mapping")
        if not isinstance(user_text, str) or not user_text.strip():
            raise AssertionError(f"{case_id}: turn {idx} user text missing")
        normalized.append({"user": user_text.strip(), "expected": expected})
    return normalized


def _decision_trace(conversation: SimpleNamespace | None) -> list[dict]:
    if conversation is None:
        return []
    context = conversation.context or {}
    trace = context.get(webhook_trace.DECISION_TRACE_KEY) if isinstance(context, dict) else None
    if isinstance(trace, dict):
        return [trace]
    if isinstance(trace, list):
        return [item for item in trace if isinstance(item, dict)]
    return []


def _trace_has_entry(trace: list[dict], **expected: object) -> bool:
    for entry in trace:
        if all(entry.get(key) == value for key, value in expected.items()):
            return True
    return False


def test_demo_salon_eval_assets_are_nonempty(eval_data: dict, eval_golden_data: dict) -> None:
    cases = eval_data.get("eval_cases")
    golden_cases = eval_golden_data.get("eval_cases")
    assert isinstance(cases, list) and cases, "EVAL.yaml must contain eval_cases"
    assert isinstance(golden_cases, list) and golden_cases, "EVAL_GOLDEN.yaml must contain eval_cases"


def test_demo_salon_golden_cases_define_expected_meta(eval_golden_data: dict) -> None:
    cases = eval_golden_data.get("eval_cases") or []
    for case in cases:
        case_id = case.get("id", "<unknown>")
        expected_meta = case.get("expected_meta")
        assert isinstance(expected_meta, dict) and expected_meta, f"{case_id}: expected_meta missing"
        contract_keys = {key for key in expected_meta.keys() if key != "llm_used"}
        assert contract_keys, f"{case_id}: expected_meta lacks contract fields"


def test_demo_salon_booking_flow_cases_preserve_signal_contract(eval_data: dict) -> None:
    cases = eval_data.get("eval_cases") or []
    booking_cases = [
        case for case in cases if isinstance(case.get("expected"), dict) and case["expected"].get("action") == "booking_flow"
    ]
    assert booking_cases, "booking_flow eval cases missing"

    for case in booking_cases:
        case_id = case.get("id", "<unknown>")
        turns = _normalize_turns(case.get("turns"), case_id)
        messages = case.get("messages")
        if turns and messages:
            raise AssertionError(f"{case_id}: use turns or messages, not both")
        if turns:
            messages = [turn["user"] for turn in turns]
        elif not isinstance(messages, list) or not messages:
            user_text = case.get("user")
            messages = [user_text] if isinstance(user_text, str) and user_text.strip() else []
        assert messages, f"{case_id}: missing booking messages"
        assert webhook_router._has_booking_signal(
            messages,
            client_slug="demo_salon",
            message_text=messages[-1],
        ), f"{case_id}: booking signal not detected"
        booking_state = webhook_router._update_booking_from_messages(
            {},
            messages,
            client_slug="demo_salon",
        )
        for slot in case["expected"].get("booking_slots", []):
            if slot == "service":
                continue
            assert booking_state.get(slot), f"{case_id}: booking slot missing '{slot}'"


def test_demo_salon_eval_records_canonical_service_projection() -> None:
    conversation = SimpleNamespace(context={"context_manager": {"message_count": 4}})

    webhook_context._maybe_store_service_carryover(
        conversation=conversation,
        service_meta={
            "service_query": "маникюр",
            "service_query_source": "semantic_match",
            "service_query_score": 0.7,
        },
        intent="pricing",
        message_count=4,
        reason="demo_eval_test",
    )

    context = webhook_context._get_conversation_context(conversation)
    manager = webhook_context._get_context_manager(context)
    carryover = webhook_context._get_service_carryover(manager, message_count=4)
    trace = _decision_trace(conversation)

    assert carryover is not None
    assert carryover.get("service_query") == "маникюр"
    assert carryover.get("projection_source") == webhook_context.CANONICAL_DIALOG_STATE_KEY
    assert carryover.get("canonical_state_owner") == webhook_context.CANONICAL_DIALOG_STATE_OWNER
    assert _trace_has_entry(
        trace,
        stage="service_carryover",
        decision="set",
        reason="demo_eval_test",
    )


def test_llm_guard_records_trace_and_meta() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", remote_jid="77000000000@s.whatsapp.net")
    saved_message = SimpleNamespace(message_metadata={"decision_meta": {}})
    timing_context: dict = {}

    def _send_and_save(text: str | None, allow_quiet_hours: bool = True):
        return text, True

    with patch(
        "app.services.ai_service.rewrite_query_for_retrieval",
        return_value={"rewrite_used": False, "rewrite_text": "", "reason": "disabled"},
    ), patch(
        "app.routers.webhook.response.generate_bot_response",
        return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("плохой ответ", "high")),
    ), patch(
        "app.routers.webhook.response._detect_llm_guard_topics",
        return_value=["hard_law"],
    ), patch(
        "app.routers.webhook.response._reuse_active_handover",
        return_value=(None, False, False),
    ), patch(
        "app.routers.webhook.response.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace()),
    ), patch(
        "app.routers.webhook.response.send_telegram_notification",
        return_value=True,
    ), patch(
        "app.routers.webhook.response._reset_low_confidence_retry",
        return_value=None,
    ):
        webhook_response._handle_llm_primary(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="что-то странное",
            saved_message=saved_message,
            client_slug="demo_salon",
            policy_type="demo_salon",
            policy_pack={},
            routing={"allow_bot_reply": True, "allow_handover_create": True},
            append_user_message=False,
            timing_context=timing_context,
            client_config={},
            intent=None,
            multi_intent_other_followup=None,
            send_and_save=_send_and_save,
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    trace = _decision_trace(conversation)
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert _trace_has_entry(trace, stage="llm_guard", decision="blocked_topics")
    assert meta.get("action") == "escalate"
    assert meta.get("intent") == "llm_guard"
    assert meta.get("source") == "llm_guard"


def test_budget_gate_trace_records_on_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    conversation = SimpleNamespace(context={})
    saved_message = SimpleNamespace(message_metadata={"decision_meta": {}})
    timing_context: dict = {}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch(
        "app.services.ai_service.consume_llm_budget",
        return_value={
            "active": True,
            "allowed": False,
            "reason": "budget_exceeded",
            "limit": 1,
            "count": 2,
            "scope": "rag_rewrite",
        },
    ):
        webhook_response._ensure_rag_rewrite(
            conversation=conversation,
            saved_message=saved_message,
            message_text="нужна информация",
            client_slug="demo_salon",
            client_config={"llm_budget": {"daily_max_calls": 0}},
            timing_context=timing_context,
        )

    trace = _decision_trace(conversation)
    assert _trace_has_entry(trace, stage="budget_gate", decision="deny", llm_scope="rag_rewrite")
