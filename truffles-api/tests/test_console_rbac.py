import pytest

from app.services.console_auth import has_console_permission, require_console_permission
from app.services.console_errors import ConsoleAPIError


@pytest.mark.parametrize(
    ("role", "section", "action", "allowed"),
    [
        ("owner", "inbox", "read", True),
        ("support", "inbox", "write", False),
        ("manager", "knowledge", "read", True),
        ("manager", "knowledge", "write", False),
        ("admin", "team", "read", True),
        ("manager", "team", "read", False),
        ("manager", "calendar", "read", True),
        ("support", "calendar", "read", False),
        ("admin", "settings", "read", True),
        ("manager", "settings", "read", False),
        ("support", "ops", "read", True),
        ("support", "ops", "write", False),
        ("support", "audit", "read", True),
        ("manager", "audit", "read", False),
        ("support", "provisioning", "read", True),
        ("support", "provisioning", "write", False),
    ],
)
def test_console_rbac_matrix(role: str, section: str, action: str, allowed: bool) -> None:
    assert has_console_permission(role, section, action) is allowed


def test_require_console_permission_raises_on_denied() -> None:
    context = type("Ctx", (), {"role": "support"})()
    with pytest.raises(ConsoleAPIError) as exc_info:
        require_console_permission(context, "inbox", "write")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"
