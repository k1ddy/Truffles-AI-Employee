import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.routers.webhook import _legacy as legacy
from app.routers.webhook import decision as decision_router


def _detect_info_calls(source_path: Path) -> list[ast.Call]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "_detect_info_class_intents":
            calls.append(node)
        elif isinstance(func, ast.Attribute) and func.attr == "_detect_info_class_intents":
            calls.append(node)
    return calls


def _named_calls(source_path: Path, function_name: str) -> list[ast.Call]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == function_name:
            calls.append(node)
        elif isinstance(func, ast.Attribute) and func.attr == function_name:
            calls.append(node)
    return calls


def _call_has_keyword(call: ast.Call, keyword: str) -> bool:
    return any(isinstance(item, ast.keyword) and item.arg == keyword for item in call.keywords)


def test_expected_reply_contract_keeps_info_block_for_promotions(monkeypatch):
    conversation = SimpleNamespace(context={"expected_reply_type": legacy.EXPECTED_REPLY_SERVICE})

    monkeypatch.setattr(
        decision_router,
        "_match_expected_reply_candidates",
        lambda **_: (False, None, []),
    )
    monkeypatch.setattr(decision_router, "_looks_like_promotions_request", lambda *_, **__: True)
    monkeypatch.setattr(decision_router, "_is_booking_confirm_enabled", lambda: True)

    monkeypatch.setattr(legacy, "_get_expected_reply_type", lambda ctx: ctx.get("expected_reply_type"))
    monkeypatch.setattr(legacy, "_get_expected_reply_reason", lambda ctx: None)
    monkeypatch.setattr(legacy, "_get_intent_queue", lambda ctx: None)
    monkeypatch.setattr(legacy, "_get_session_memory", lambda ctx: None)
    monkeypatch.setattr(legacy, "_is_re_entry_required", lambda ctx: False)
    monkeypatch.setattr(legacy, "_select_expected_reply_message", lambda *_, **__: None)
    monkeypatch.setattr(legacy, "_get_booking_context", lambda ctx: {})
    monkeypatch.setattr(legacy, "_normalize_service_text", lambda text: (text or "").casefold())
    monkeypatch.setattr(legacy, "_looks_like_info_query", lambda *_, **__: True)
    monkeypatch.setattr(legacy, "_has_price_signal", lambda *_, **__: False)
    monkeypatch.setattr(legacy, "_has_duration_signal", lambda *_, **__: False)
    monkeypatch.setattr(legacy, "_extract_datetime", lambda *_, **__: None)
    monkeypatch.setattr(legacy, "_record_decision_trace", lambda *_, **__: None)
    monkeypatch.setattr(legacy, "_update_message_decision_metadata", lambda *_, **__: None)
    monkeypatch.setattr(legacy, "_set_router_observability", lambda *_, **__: {})
    monkeypatch.setattr(
        legacy,
        "interpret_expected_reply",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("interpreter should not run")),
    )
    monkeypatch.setattr(legacy, "_get_conversation_context", lambda conv: conv.context)
    monkeypatch.setattr(legacy, "_get_context_manager", lambda ctx: {})

    state = decision_router._apply_expected_reply_contract(
        conversation=conversation,
        saved_message=None,
        message_text="Есть ли скидки?",
        batch_messages=["Есть ли скидки?"],
        context=conversation.context,
        context_manager={},
        now=datetime.now(timezone.utc),
        current_goal="booking",
        class_carryover=None,
        message_count=1,
        policy_type=None,
        policy_pack=None,
        client_slug="demo_salon",
    )

    assert state.expected_reply_blocked_by_info is True
    assert state.expected_reply_shortcircuit is False


def test_decision_detect_info_calls_pass_client_slug():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    )
    calls = _detect_info_calls(source_path)

    assert calls
    assert all(_call_has_keyword(call, "client_slug") for call in calls)


def test_booking_detect_info_calls_pass_client_slug():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "booking.py"
    )
    calls = _detect_info_calls(source_path)

    assert calls
    assert all(_call_has_keyword(call, "client_slug") for call in calls)


def test_decision_recomputes_batch_non_booking_message_after_debounce():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    )
    calls = _named_calls(source_path, "_select_last_non_booking_message")

    assert len(calls) >= 2
    assert any(getattr(call, "lineno", 0) >= 6338 for call in calls)


def test_expected_reply_info_block_detects_booking_interrupt_info_turns():
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Есть ли у вас парковка?",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="У вас есть какие-то акции или скидки?",
        client_slug="demo_salon",
    )
    assert not decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Можно на 18:30?",
        client_slug="demo_salon",
    )


def test_decision_recomputes_expected_reply_block_after_debounce():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    )
    calls = _named_calls(source_path, "_should_block_expected_reply_by_info")

    assert calls
    assert any(getattr(call, "lineno", 0) >= 6338 for call in calls)
