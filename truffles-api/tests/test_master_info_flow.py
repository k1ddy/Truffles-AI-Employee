from app.routers.webhook.info import _build_info_intent_reply, _detect_info_class_intents
from app.services.demo_salon_knowledge import get_demo_salon_decision


def test_detect_info_class_intents_master_signal():
    intents, meta = _detect_info_class_intents(
        "Можно к конкретному мастеру?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True


def test_detect_info_class_intents_parking_signal():
    intents, meta = _detect_info_class_intents(
        "У вас есть парковка рядом?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "parking" in intents
    assert meta.get("info_signals", {}).get("parking") is True


def test_detect_info_class_intents_location_phrase_signal():
    intents, meta = _detect_info_class_intents(
        "В каком районе вы находитесь?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "location" in intents
    assert meta.get("info_signals", {}).get("location") is True


def test_build_info_intent_reply_master_uses_truth_team():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="Можно к мастеру?",
    )

    assert isinstance(reply, str) and "мастер" in reply.casefold()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "master" in fact_intents
    assert "master" in info_sections


def test_build_info_intent_reply_location_uses_truth_address():
    reply, meta = _build_info_intent_reply(
        "location",
        service_query=None,
        client_slug="demo_salon",
        message_text="В каком районе вы находитесь?",
    )

    assert isinstance(reply, str) and "адрес" in reply.casefold()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "location" in fact_intents
    assert "address" in info_sections or "location" in info_sections


def test_get_demo_salon_decision_master_intent():
    decision = get_demo_salon_decision(
        "Можно записаться к мастеру на окрашивание?",
        client_slug="demo_salon",
    )

    assert decision is not None
    assert decision.action == "reply"
    assert decision.intent == "master"
    assert "мастер" in (decision.response or "").casefold()
