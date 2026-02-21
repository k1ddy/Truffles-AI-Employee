import pytest

from app.services.console_auth import has_console_permission, require_console_permission
from app.services.console_errors import ConsoleAPIError


@pytest.mark.parametrize(
    ("role", "section", "action", "allowed"),
    [
        ("owner", "inbox", "read", True),
        ("owner", "outreach", "write", True),
        ("support", "inbox", "write", False),
        ("support", "outreach", "write", False),
        ("platform_admin", "inbox", "write", True),
        ("platform_admin", "outreach", "read", True),
        ("support", "outreach", "read", True),
        ("manager", "knowledge", "read", True),
        ("manager", "knowledge", "write", False),
        ("manager", "outreach", "write", True),
        ("platform_admin", "knowledge", "write", True),
        ("admin", "team", "read", True),
        ("admin", "outreach", "write", True),
        ("manager", "team", "read", True),
        ("platform_admin", "team", "write", True),
        ("manager", "calendar", "read", True),
        ("specialist", "calendar", "read", False),
        ("specialist", "calendar", "write", False),
        ("specialist", "outreach", "write", False),
        ("specialist", "inbox", "read", False),
        ("viewer", "inbox", "read", True),
        ("viewer", "outreach", "write", False),
        ("viewer", "knowledge", "read", True),
        ("viewer", "calendar", "read", True),
        ("viewer", "audit", "read", True),
        ("viewer", "settings", "read", False),
        ("support", "calendar", "read", False),
        ("platform_admin", "calendar", "write", True),
        ("admin", "settings", "read", True),
        ("manager", "settings", "read", False),
        ("platform_admin", "settings", "write", True),
        ("support", "ops", "read", False),
        ("support", "ops", "write", False),
        ("platform_admin", "ops", "write", True),
        ("support", "audit", "read", False),
        ("manager", "audit", "read", False),
        ("platform_admin", "audit", "read", True),
        ("platform_admin", "integrations", "read", True),
        ("owner", "integrations", "read", False),
        ("support", "integrations", "read", False),
        ("owner", "business", "read", True),
        ("admin", "subscription", "read", True),
        ("manager", "business", "read", False),
        ("support", "subscription", "read", False),
        ("support", "provisioning", "read", False),
        ("support", "provisioning", "write", False),
        ("platform_admin", "provisioning", "write", True),
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
