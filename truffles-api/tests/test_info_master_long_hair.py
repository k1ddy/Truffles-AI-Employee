from app.routers.webhook.info import _build_info_intent_reply


def test_master_info_reply_handles_long_haircut_request_with_targeted_answer():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query=None,
        client_slug="demo_salon",
        message_text="У вас есть мастера, которые работают с долгими стрижками?",
    )

    assert isinstance(reply, str) and reply
    assert "длинные волосы" in reply.casefold()
    assert "балаяж" not in reply.casefold()
    assert isinstance(meta, dict)
    assert meta.get("intent_class") == "master"


def test_master_info_reply_handles_long_haircut_service_hint_when_message_is_generic():
    reply, meta = _build_info_intent_reply(
        "master",
        service_query="долгие стрижки",
        client_slug="demo_salon",
        message_text="Есть мастера?",
    )

    assert isinstance(reply, str) and reply
    assert "длинные волосы" in reply.casefold()
    assert "балаяж" not in reply.casefold()
    assert isinstance(meta, dict)
    assert meta.get("intent_class") == "master"
