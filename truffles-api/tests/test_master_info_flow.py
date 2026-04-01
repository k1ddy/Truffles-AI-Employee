import pytest

from app.routers.webhook.info import (
    _anchor_group_hit,
    _build_info_intent_reply,
    _detect_info_class_intents,
    _tokenize_for_matching,
)
from app.services import demo_salon_knowledge
from app.services.demo_salon_knowledge import get_demo_salon_decision


def test_detect_info_class_intents_master_signal():
    intents, meta = _detect_info_class_intents(
        "Можно к конкретному мастеру?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True


def test_detect_info_class_intents_master_signal_who_will_do_procedure():
    intents, meta = _detect_info_class_intents(
        "Кто будет делать процедуру маникюра?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True


def test_detect_info_class_intents_master_signal_for_experience_question():
    intents, meta = _detect_info_class_intents(
        "Кто лучше по маникюру и у кого больше опыта?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True
    master_resolution = meta.get("master_resolution", {})
    assert master_resolution.get("needs_service_clarify") is False
    assert master_resolution.get("service_query") == "Маникюр"


def test_detect_info_class_intents_master_signal_for_masters_do_x_question():
    intents, meta = _detect_info_class_intents(
        "Какие мастера делают маникюр?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True
    master_resolution = meta.get("master_resolution", {})
    assert master_resolution.get("needs_service_clarify") is False
    assert master_resolution.get("service_query") == "Маникюр"


def test_detect_info_class_intents_services_overview_does_not_trigger_master():
    intents, meta = _detect_info_class_intents(
        "Какие услуги вы оказываете?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" not in intents
    assert meta.get("info_signals", {}).get("master") is False


def test_anchor_group_hit_short_prefix_requires_exact_token_boundary():
    tokens = _tokenize_for_matching("у вас есть мастера которые работают с долгими стрижками")
    assert _anchor_group_hit(tokens, ("работ", "до")) is False

    explicit_tokens = _tokenize_for_matching("какие мастера работают до скольки")
    assert _anchor_group_hit(explicit_tokens, ("работ", "до")) is True


def test_detect_info_class_intents_master_phrase_no_false_hours_anchor():
    intents, meta = _detect_info_class_intents(
        "У вас есть мастера, которые работают с долгими стрижками?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" in intents
    assert meta.get("info_signals", {}).get("master") is True
    assert meta.get("info_signals", {}).get("hours") is False
    anchor_intents = set(meta.get("anchor_intents") or [])
    assert "hours" not in anchor_intents


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


def test_detect_info_class_intents_location_signal_from_address_hint():
    intents, meta = _detect_info_class_intents(
        "Портал на Абая сегодня открыт?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "location" in intents
    assert meta.get("info_signals", {}).get("location") is True
    assert meta.get("info_signals", {}).get("location_address_hint") is True


def test_detect_info_class_intents_duration_signal():
    intents, meta = _detect_info_class_intents(
        "Какое время займет маникюр?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "duration" in intents
    assert meta.get("info_signals", {}).get("duration") is True


def test_detect_info_class_intents_pricing_signal():
    intents, meta = _detect_info_class_intents(
        "Сколько стоит маникюр?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "pricing" in intents
    assert meta.get("info_signals", {}).get("pricing") is True


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


def test_detect_info_class_intents_hours_signal_for_work_schedule_phrase():
    intents, meta = _detect_info_class_intents(
        "Какое у вас рабочее время?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "hours" in intents
    assert meta.get("info_signals", {}).get("hours") is True


def test_detect_info_class_intents_hours_signal_for_how_long_you_work_phrase():
    intents, meta = _detect_info_class_intents(
        "Как долго вы работаете?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "hours" in intents
    assert "duration" not in intents
    assert meta.get("info_signals", {}).get("hours") is True
    assert meta.get("info_signals", {}).get("duration") is False


@pytest.mark.parametrize(
    "message_text",
    [
        "Я предпочитаю утренние часы.",
        "Мне подходят только утренние часы.",
    ],
)
def test_detect_info_class_intents_daypart_preference_statement_does_not_trigger_hours_or_duration(
    message_text,
):
    intents, meta = _detect_info_class_intents(
        message_text,
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "hours" not in intents
    assert "duration" not in intents
    assert meta.get("info_signals", {}).get("hours") is False
    assert meta.get("info_signals", {}).get("duration") is False
    assert meta.get("daypart_preference_statement") is True
    assert set(meta.get("suppressed_info_intents") or []) == {"hours", "duration"}


def test_detect_info_class_intents_hours_question_with_daypart_remains_hours():
    intents, meta = _detect_info_class_intents(
        "Во сколько вы открываетесь утром?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "hours" in intents
    assert "duration" not in intents
    assert meta.get("info_signals", {}).get("hours") is True
    assert meta.get("info_signals", {}).get("duration") is False
    assert meta.get("daypart_preference_statement") is not True


def test_detect_info_class_intents_special_offers_phrase_does_not_trigger_master():
    intents, meta = _detect_info_class_intents(
        "У вас есть специальные предложения?",
        intent_decomp_set=set(),
        client_slug="demo_salon",
    )

    assert "master" not in intents
    assert meta.get("info_signals", {}).get("master") is False


def test_compose_multi_truth_reply_how_long_you_work_drops_duration_component():
    reply, meta = demo_salon_knowledge.compose_multi_truth_reply(
        "Как долго вы работаете?",
        "demo_salon",
        {"intents": ["hours", "duration"], "service_query": "Стрижка"},
        return_meta=True,
    )

    assert isinstance(reply, str) and reply
    info_sections = (meta or {}).get("info_sections") or []
    fact_intents = (meta or {}).get("fact_intents") or []
    assert "hours" in info_sections
    assert "hours" in fact_intents
    assert "duration" not in info_sections
    assert "service_duration" not in info_sections
    assert "duration" not in fact_intents


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


def test_build_info_intent_reply_master_phrase_uses_team_listing():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="У вас есть мастер по маникюру?",
    )

    text = (reply or "").casefold()
    assert "по мастерам" in text or "мастер" in text
    assert "₸" not in text
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "master" in fact_intents
    assert "master" in info_sections


def test_build_info_intent_reply_master_long_hair_question_focuses_hair_team():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="У вас есть мастера, которые работают с долгими стрижками?",
    )

    text = (reply or "").casefold()
    assert "волос" in text
    assert "ногти" not in text
    assert "брови" not in text
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "master" in fact_intents
    assert "master" in info_sections
    assert isinstance((meta or {}).get("resolver_id"), str)
    assert isinstance((meta or {}).get("resolver_version"), str)


def test_build_info_intent_reply_master_without_service_returns_clarify_collect():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="Кто лучший мастер?",
    )

    assert isinstance(reply, str) and "по какой услуге" in reply.casefold()
    assert isinstance(meta, dict)
    assert meta.get("action_class") == "COLLECT"
    assert meta.get("clarify_reason") == "missing_service_query"
    assert meta.get("service_query") is None


def test_build_info_intent_reply_emits_resolver_contract_meta():
    reply, meta = _build_info_intent_reply(
        "pricing",
        service_query=None,
        client_slug="demo_salon",
        message_text="Сколько стоит маникюр?",
    )

    assert isinstance(reply, str) and reply.strip()
    assert isinstance(meta, dict)
    assert meta.get("resolver_id")
    assert meta.get("resolver_version")
    assert meta.get("intent_class")
    assert meta.get("action_class") in {"FACT", "COLLECT"}
    assert isinstance(meta.get("resolver_candidates"), list)


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


def test_build_info_intent_reply_location_scoped_request_excludes_hours():
    reply, meta = _build_info_intent_reply(
        "location",
        service_query=None,
        client_slug="demo_salon",
        message_text="Где находится салон?",
        requested_info_intents=["location"],
    )

    assert isinstance(reply, str) and "адрес" in reply.casefold()
    assert "работаем" not in reply.casefold()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert fact_intents == ["location"]
    assert info_sections == ["address"]


def test_build_info_intent_reply_parking_scoped_request_excludes_location_bundle():
    reply, meta = _build_info_intent_reply(
        "parking",
        service_query=None,
        client_slug="demo_salon",
        message_text="Есть ли у вас парковка?",
        requested_info_intents=["parking"],
    )

    assert isinstance(reply, str) and "парков" in reply.casefold()
    assert "адрес" not in reply.casefold()
    assert "работаем" not in reply.casefold()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert fact_intents == ["parking"]
    assert info_sections == ["parking"]


def test_build_info_intent_reply_promotions_uses_truth_promotions():
    reply, meta = _build_info_intent_reply(
        "promotions",
        service_query=None,
        client_slug="demo_salon",
        message_text="Есть ли у вас специальные предложения?",
    )

    assert isinstance(reply, str) and reply.strip()
    fact_intents = (meta or {}).get("fact_intents") or []
    info_sections = (meta or {}).get("info_sections") or []
    assert "promotions" in fact_intents
    assert "promotions" in info_sections


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
