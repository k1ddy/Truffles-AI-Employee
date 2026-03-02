from app.routers.webhook.info import _build_info_intent_reply


def test_master_info_reply_handles_long_haircut_request_with_targeted_answer():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="У вас есть мастера, которые работают с долгими стрижками?",
    )

    assert isinstance(reply, str) and reply
    assert isinstance(meta, dict)
    assert meta.get("intent_class") == "master"
    assert meta.get("action_class") == "FACT"
    fact_intents = set(meta.get("fact_intents") or [])
    info_sections = set(meta.get("info_sections") or [])
    assert "master" in fact_intents
    assert "master" in info_sections
    assert meta.get("master_query_contract") == "masters_catalog.v1"
    assert meta.get("master_reply_mode") == "service_match"
    assert isinstance(meta.get("master_profiles"), list)
    assert (meta.get("master_profiles_count") or 0) >= 1


def test_master_info_reply_handles_long_haircut_service_hint_when_message_is_generic():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query="долгие стрижки",
        client_slug="demo_salon",
        message_text="Есть мастера?",
    )

    assert isinstance(reply, str) and reply
    assert isinstance(meta, dict)
    assert meta.get("intent_class") == "master"
    assert meta.get("action_class") == "FACT"
    fact_intents = set(meta.get("fact_intents") or [])
    info_sections = set(meta.get("info_sections") or [])
    assert "master" in fact_intents
    assert "master" in info_sections
    assert meta.get("master_query_contract") == "masters_catalog.v1"
    assert meta.get("master_reply_mode") == "service_match"
    assert isinstance(meta.get("master_profiles"), list)
    assert (meta.get("master_profiles_count") or 0) >= 1
