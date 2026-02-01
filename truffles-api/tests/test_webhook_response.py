from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.routers import webhook
from app.routers.webhook import _legacy as legacy
from app.routers.webhook.response import _finalize_bot_response


def test_maybe_append_booking_cta_adds_prompt_when_needed():
    response = webhook._maybe_append_booking_cta(
        "Мы можем помочь с услугой",
        conversation_state=webhook.ConversationState.BOT_ACTIVE.value,
        allow_booking_flow=True,
        has_followup=False,
    )

    assert response.endswith(webhook.MSG_BOOKING_CTA)


def test_maybe_append_booking_cta_skips_when_already_mentions_booking():
    response = webhook._maybe_append_booking_cta(
        "Хотите записаться на процедуру?",
        conversation_state=webhook.ConversationState.BOT_ACTIVE.value,
        allow_booking_flow=True,
        has_followup=False,
    )

    assert response == "Хотите записаться на процедуру?"


def test_apply_quiet_hours_notice_adds_notice():
    response = webhook._apply_quiet_hours_notice(
        "Мы ответим утром.",
        "Салон сейчас закрыт.",
    )

    assert response == "Салон сейчас закрыт.\n\nМы ответим утром."


def test_apply_quiet_hours_notice_skips_when_notice_present():
    response = webhook._apply_quiet_hours_notice(
        "Салон сейчас закрыт. Мы ответим утром.",
        "Салон сейчас закрыт.",
    )

    assert response == "Салон сейчас закрыт. Мы ответим утром."


def test_finalize_bot_response_quiet_hours_ttl():
    conversation = SimpleNamespace(
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    now = datetime(2026, 1, 27, 21, 0, tzinfo=timezone.utc)
    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now,
    )
    assert response.startswith("Салон закрыт.")

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now + timedelta(minutes=5),
    )
    assert response == "Ответ"

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now + timedelta(minutes=11),
    )
    assert response.startswith("Салон закрыт.")


def test_finalize_bot_response_evening_greeting_once():
    conversation = SimpleNamespace(
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    now = datetime(2026, 1, 27, 19, 0, tzinfo=timezone.utc)
    greeting = "Добрый вечер. Это виртуальный ассистент салона."
    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice=None,
        evening_greeting=greeting,
        now=now,
    )
    assert response.startswith(greeting)

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice=None,
        evening_greeting=greeting,
        now=now + timedelta(hours=1),
    )
    assert response == "Ответ"


def test_time_only_guard_detection():
    assert legacy._looks_like_time_only_request("в 7") is True
    assert legacy._looks_like_time_only_request("на 7:30") is True
    assert legacy._looks_like_time_only_request("э на чассов в 7") is True
    assert legacy._looks_like_time_only_request("маникюр в 7") is False
    assert legacy._looks_like_time_only_request("на час") is False
