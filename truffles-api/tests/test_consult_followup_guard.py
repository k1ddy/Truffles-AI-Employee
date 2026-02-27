from app.routers.webhook import _legacy as legacy
from app.routers.webhook import response as webhook_response


def test_consult_return_not_attached_for_booking_reason(monkeypatch):
    called = {"value": False}

    def _fail_apply(**_kwargs):
        called["value"] = True
        raise AssertionError("consult return should not be applied for booking reason")

    monkeypatch.setattr("app.routers.webhook.context_manager._apply_consult_return", _fail_apply)
    bot_response = webhook_response._maybe_apply_consult_return(
        conversation=None,
        saved_message=None,
        bot_response="На какую услугу хотите записаться?",
        consult_return_pending=True,
        consult_return_prompt="Если вернуться к вопросу...",
        consult_context={"question": "Что нравится в референсе"},
        reason="llm_policy_core_booking",
    )

    assert bot_response == "На какую услугу хотите записаться?"
    assert called["value"] is False


def test_consult_return_not_attached_for_booking_reason_family(monkeypatch):
    called = {"value": False}

    def _fail_apply(**_kwargs):
        called["value"] = True
        raise AssertionError("consult return should not be applied for booking reason family")

    monkeypatch.setattr("app.routers.webhook.context_manager._apply_consult_return", _fail_apply)
    bot_response = webhook_response._maybe_apply_consult_return(
        conversation=None,
        saved_message=None,
        bot_response="Проверю и вернусь с деталями.",
        consult_return_pending=True,
        consult_return_prompt="Если вернуться к вопросу...",
        consult_context={"question": "Что нравится в референсе"},
        reason="policy_override_booking_flow",
    )

    assert bot_response == "Проверю и вернусь с деталями."
    assert called["value"] is False


def test_consult_followup_suppressed_without_booking_signal(monkeypatch):
    monkeypatch.setattr(legacy, "_is_booking_request", lambda _text, client_slug=None: False)

    assert (
        webhook_response._should_append_booking_followup_for_consult(
            booking_goal_locked=True,
            consult_action="consult_reply",
            message_text="Какую стрижку вы рекомендуете?",
            expected_reply_type="name",
            client_slug="demo_salon",
        )
        is False
    )


def test_consult_followup_kept_with_booking_signal(monkeypatch):
    monkeypatch.setattr(legacy, "_is_booking_request", lambda _text, client_slug=None: True)

    assert (
        webhook_response._should_append_booking_followup_for_consult(
            booking_goal_locked=True,
            consult_action="consult_reply",
            message_text="Подтвердите запись, пожалуйста.",
            expected_reply_type="name",
            client_slug="demo_salon",
        )
        is True
    )


def test_consult_followup_kept_for_service_expected_reply(monkeypatch):
    monkeypatch.setattr(legacy, "_is_booking_request", lambda _text, client_slug=None: False)

    assert (
        webhook_response._should_append_booking_followup_for_consult(
            booking_goal_locked=True,
            consult_action="consult_reply",
            message_text="Что посоветуете?",
            expected_reply_type="service_choice",
            client_slug="demo_salon",
        )
        is True
    )
