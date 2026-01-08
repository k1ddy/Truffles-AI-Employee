from app.routers import webhook


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
