from app.routers.webhook import booking as booking_router
from app.routers.webhook import decision as decision_router


def test_next_booking_prompt_name_does_not_repeat_datetime_fragment():
    booking_state, prompt = booking_router._next_booking_prompt(
        {
            "active": True,
            "service": "Стрижка",
            "datetime": "17:45",
        },
        client_slug="demo_salon",
    )

    assert booking_state.get("last_question") == "name"
    assert isinstance(prompt, str)
    assert "17:45" not in prompt
    assert decision_router.MSG_BOOKING_ASK_NAME in prompt


def test_next_booking_prompt_name_does_not_leak_iso_datetime():
    booking_state, prompt = booking_router._next_booking_prompt(
        {
            "active": True,
            "service": "Стрижка",
            "datetime": "2023-10-06T00:00:00Z",
        },
        client_slug="demo_salon",
    )

    assert booking_state.get("last_question") == "name"
    assert isinstance(prompt, str)
    assert "2023-10-06T00:00:00Z" not in prompt
    assert decision_router.MSG_BOOKING_ASK_NAME in prompt
