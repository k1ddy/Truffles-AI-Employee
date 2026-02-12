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


def test_detect_info_class_intents_pricing_signal_for_colloquial_phrase():
    intents, meta = _detect_info_class_intents(
        "А если я захочу укладку, сколько это будет?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "pricing" in intents
    assert meta.get("info_signals", {}).get("pricing") is True


def test_detect_info_class_intents_duration_signal_for_colloquial_phrase():
    intents, meta = _detect_info_class_intents(
        "А по времени сколько это будет?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "duration" in intents
    assert meta.get("info_signals", {}).get("duration") is True


def test_detect_info_class_intents_contact_signal():
    intents, meta = _detect_info_class_intents(
        "Какой у вас номер телефона?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "contact" in intents
    assert meta.get("info_signals", {}).get("contact") is True


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


def test_build_info_intent_reply_contact_uses_instagram_when_phone_missing():
    reply, meta = _build_info_intent_reply(
        "contact",
        service_query=None,
        client_slug="demo_salon",
        message_text="Какой у вас номер телефона?",
    )

    assert isinstance(reply, str) and "instagram" in reply.casefold()
    assert "не указан" in reply.casefold()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "contact" in fact_intents
    assert "contact" in info_sections


def test_get_demo_salon_decision_master_intent():
    decision = get_demo_salon_decision(
        "Можно записаться к мастеру на окрашивание?",
        client_slug="demo_salon",
    )

    assert decision is not None
    assert decision.action == "reply"
    assert decision.intent == "master"
    assert "мастер" in (decision.response or "").casefold()


def test_get_demo_salon_decision_contact_intent():
    decision = get_demo_salon_decision(
        "Какой у вас номер телефона?",
        client_slug="demo_salon",
    )

    assert decision is not None
    assert decision.action == "reply"
    assert decision.intent == "contact"
    assert "instagram" in (decision.response or "").casefold()
