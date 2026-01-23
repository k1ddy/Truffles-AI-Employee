from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_resolve_telegram_action_target_requires_bot_token():
    settings = SimpleNamespace(telegram_bot_token=None, telegram_chat_id="-100123")

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_telegram_action_target(
            settings=settings,
            branch=None,
            scope="client",
            chat_id=None,
            branch_id=None,
        )

    assert exc_info.value.code == "TELEGRAM_CONFIG_MISSING"


def test_resolve_telegram_action_target_branch_requires_branch_id():
    settings = SimpleNamespace(telegram_bot_token="token", telegram_chat_id="-100123")

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_telegram_action_target(
            settings=settings,
            branch=None,
            scope="branch",
            chat_id=None,
            branch_id=None,
        )

    assert exc_info.value.code == "INVALID_PARAM"


def test_resolve_telegram_action_target_branch_missing_branch():
    settings = SimpleNamespace(telegram_bot_token="token", telegram_chat_id="-100123")
    branch_id = uuid4()

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_telegram_action_target(
            settings=settings,
            branch=None,
            scope="branch",
            chat_id=None,
            branch_id=branch_id,
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_resolve_telegram_action_target_branch_missing_chat_id():
    settings = SimpleNamespace(telegram_bot_token="token", telegram_chat_id="-100123")
    branch_id = uuid4()
    branch = SimpleNamespace(telegram_chat_id=None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_telegram_action_target(
            settings=settings,
            branch=branch,
            scope="branch",
            chat_id=None,
            branch_id=branch_id,
        )

    assert exc_info.value.code == "TELEGRAM_CONFIG_MISSING"
    assert exc_info.value.details["branch_id"] == str(branch_id)


def test_resolve_telegram_action_target_client_scope_uses_settings_chat_id():
    settings = SimpleNamespace(telegram_bot_token="token", telegram_chat_id="-100123")

    bot_token, chat_id, resolved_branch_id = console_router._resolve_telegram_action_target(
        settings=settings,
        branch=None,
        scope="client",
        chat_id=None,
        branch_id=None,
    )

    assert bot_token == "token"
    assert chat_id == "-100123"
    assert resolved_branch_id is None


def test_resolve_telegram_action_target_accepts_chat_override():
    settings = SimpleNamespace(telegram_bot_token="token", telegram_chat_id="-100123")
    branch_id = uuid4()

    bot_token, chat_id, resolved_branch_id = console_router._resolve_telegram_action_target(
        settings=settings,
        branch=None,
        scope="client",
        chat_id="-100999",
        branch_id=branch_id,
    )

    assert bot_token == "token"
    assert chat_id == "-100999"
    assert resolved_branch_id == branch_id


def test_generate_verification_code_format():
    code = console_router._generate_verification_code()
    assert len(code) == 6
    assert set(code) <= set("0123456789ABCDEF")
