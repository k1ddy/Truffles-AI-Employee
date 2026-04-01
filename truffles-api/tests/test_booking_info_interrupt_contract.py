import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.routers.webhook import _legacy as legacy
from app.routers.webhook import decision as decision_router
from app.routers.webhook import info as info_router
from app.services import pack_runtime_neutral_adapter as neutral_adapter


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


def test_info_detect_ignores_price_false_positive_inside_pochemu():
    text = "Почему я не могу записаться на выходные?"
    normalized = legacy.normalize_for_matching(text)

    assert legacy._has_price_signal(normalized, text, client_slug="demo_salon") is False

    intents, meta = info_router._detect_info_class_intents(
        text,
        intent_decomp_set=set(),
        client_slug="demo_salon",
        service_query="Дизайн ногтей",
    )

    assert "pricing" not in intents
    assert "hours" in intents
    assert meta.get("question_type") != "pricing"


def test_pack_runtime_neutral_price_signal_ignores_price_false_positive_inside_pochemu():
    false_positive_text = "Почему я не могу записаться на выходные?"
    normalized_false_positive = neutral_adapter._normalize_text(false_positive_text)

    assert (
        neutral_adapter._has_price_signal(
            normalized_false_positive,
            false_positive_text,
            client_slug="demo_salon",
        )
        is False
    )

    true_positive_text = "Почем маникюр?"
    normalized_true_positive = neutral_adapter._normalize_text(true_positive_text)

    assert (
        neutral_adapter._has_price_signal(
            normalized_true_positive,
            true_positive_text,
            client_slug="demo_salon",
        )
        is True
    )


def test_pack_runtime_neutral_price_signal_accepts_skolko_eto_stoit_phrase():
    text = "А сколько это стоит?"
    normalized = neutral_adapter._normalize_text(text)

    assert neutral_adapter._has_price_signal(
        normalized,
        text,
        client_slug="demo_salon",
    )


def test_pack_runtime_neutral_duration_signal_accepts_vremya_na_service_phrase():
    text = "Как вы оцениваете время на наращивание полигелем?"
    normalized = neutral_adapter._normalize_text(text)

    assert neutral_adapter._has_duration_signal(
        normalized,
        text,
        client_slug="demo_salon",
    )


def test_services_overview_signal_accepts_info_about_services_phrase():
    assert info_router._looks_like_services_overview_message(
        "Могу я получить информацию о ваших услугах?",
        client_slug="demo_salon",
    )


def test_promotions_signal_accepts_generic_statement():
    assert info_router._looks_like_promotions_policy_message(
        "Я слышал, что у вас есть акции на маникюр.",
        client_slug="demo_salon",
    )


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


def test_decision_no_longer_recomputes_batch_non_booking_message_after_debounce():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    )
    calls = _named_calls(source_path, "_select_last_non_booking_message")

    assert calls == []


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
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Какова продолжительность сеанса?",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="How long does the session take?",
        client_slug="demo_salon",
    )
    assert not decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Можно на 18:30?",
        client_slug="demo_salon",
    )
    assert not decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Я хочу записаться на 3 часа.",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        message_text="Сколько длится маникюр на 3 часа?",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
        message_text="Где ваш салон?",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
        message_text="Я отправлю фото своей прически.",
        client_slug="demo_salon",
    )
    assert decision_router._should_block_expected_reply_by_info(
        expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
        message_text="Проверьте, пожалуйста, мою запись на пятницу.",
        client_slug="demo_salon",
    )


def test_info_classifier_detects_location_question_where_salon_phrase():
    intents, meta = info_router._detect_info_class_intents(
        "Где ваш салон?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "location" in intents
    signals = meta.get("info_signals") if isinstance(meta, dict) else {}
    assert isinstance(signals, dict) and signals.get("location") is True


def test_decision_expected_reply_block_check_is_localized_to_single_contract_site():
    source_path = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    )
    calls = _named_calls(source_path, "_should_block_expected_reply_by_info")

    assert len(calls) == 1
