from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.agent_membership import AgentMembership
from app.routers import console as console_router
from app.schemas.console import (
    ConsoleAgentCreateRequest,
    ConsoleBranchBootstrapAccountTemplate,
    ConsoleBranchCreateRequest,
    ConsoleBranchGoLiveDecisionRequest,
    ConsoleBranchGoLiveWaiverRequest,
    ConsoleBranchUpdateRequest,
    ConsoleOnboardingAutopilotRequest,
)
from app.schemas.onboarding_contract import (
    OnboardingProviderBindingPayload,
    OnboardingProviderBindingWhatsApp,
)
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", accessible_clients=None, client_id=None):
    selected_client_id = client_id or uuid4()
    clients = accessible_clients or [SimpleNamespace(id=selected_client_id, company_id=uuid4())]
    return SimpleNamespace(
        agent=SimpleNamespace(id=uuid4(), name="Tester", role=role),
        role=role,
        client=SimpleNamespace(id=selected_client_id, company_id=clients[0].company_id),
        accessible_clients=clients,
        branches=[],
        effective_branch_id=None,
    )


def test_ensure_unique_oidc_subject_rejects_duplicate():
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = SimpleNamespace(agent_id=uuid4())
    db.query.return_value = query

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_unique_oidc_subject(db, "duplicate-subject")

    assert exc_info.value.code == "OIDC_SUBJECT_IN_USE"


def test_ensure_unique_oidc_subject_returns_normalized_value():
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query

    value = console_router._ensure_unique_oidc_subject(db, "  clean-subject  ")

    assert value == "clean-subject"


def test_resolve_membership_target_rejects_mixed_scope_fields():
    db = Mock()
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_membership_target(
            db,
            scope="branch",
            company_id=None,
            client_id=uuid4(),
            branch_id=uuid4(),
        )
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_create_agent_blocks_cross_tenant_access(monkeypatch):
    target_client_id = uuid4()
    allowed_client_id = uuid4()
    db = Mock()
    client = SimpleNamespace(id=target_client_id, company_id=uuid4())
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[SimpleNamespace(id=allowed_client_id, company_id=uuid4())],
            client_id=allowed_client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_agent(
            request=Mock(),
            body=ConsoleAgentCreateRequest(client_id=target_client_id, role="owner", name="Owner"),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_create_agent_rejects_mixed_oidc_and_sso_payload(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=client_id, company_id=company_id)

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_agent(
            request=Mock(),
            body=ConsoleAgentCreateRequest(
                client_id=client_id,
                role="manager",
                branch_id=uuid4(),
                oidc_subject="oidc-sub",
                sso_username="login",
                sso_password="password123",
            ),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_create_agent_provisions_sso_user_and_binds_subject(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=client_id, company_id=company_id)
    created = {}

    def _fake_create_agent_with_membership(
        _db,
        *,
        client,
        role,
        branch,
        name,
        is_active,
        oidc_subject,
        linked_from,
        now,
    ):
        created["client_id"] = client.id
        created["role"] = role
        created["oidc_subject"] = oidc_subject
        created["linked_from"] = linked_from
        return SimpleNamespace(
            id=uuid4(),
            name=name,
            role=role,
            client_id=client.id,
            branch_id=branch.id if branch else None,
            is_active=is_active,
        )

    sso_calls = {}

    def _fake_provision_sso(*, username, password, temporary_password):
        sso_calls["username"] = username
        sso_calls["password"] = password
        sso_calls["temporary_password"] = temporary_password
        return "keycloak-sub-123"

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_create_agent_with_membership", _fake_create_agent_with_membership)
    monkeypatch.setattr(console_router, "_provision_sso_user_and_get_subject", _fake_provision_sso)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.create_agent(
        request=Mock(),
        body=ConsoleAgentCreateRequest(
            client_id=client_id,
            role="owner",
            name="Owner User",
            sso_username="owner.user",
            sso_password="Password123",
            sso_temp_password=False,
        ),
        db=db,
    )

    assert response.agent.client_id == client_id
    assert response.agent.role == "owner"
    assert created["oidc_subject"] == "keycloak-sub-123"
    assert created["linked_from"] == "admin_api"
    assert sso_calls["username"] == "owner.user"
    assert sso_calls["password"] == "Password123"
    assert sso_calls["temporary_password"] is False


@pytest.mark.parametrize("deprecated_role", ["support", "specialist"])
@pytest.mark.asyncio
async def test_create_agent_rejects_deprecated_roles(monkeypatch, deprecated_role: str):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=client_id, company_id=company_id)

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_agent(
            request=Mock(),
            body=ConsoleAgentCreateRequest(
                client_id=client_id,
                role=deprecated_role,
                name="Deprecated Role",
            ),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "deprecated for assignment" in exc_info.value.message


def test_resolve_keycloak_admin_config_accepts_non_console_username_password_aliases(monkeypatch):
    env_keys = (
        "CONSOLE_OIDC_ISSUER",
        "KEYCLOAK_ISSUER",
        "CONSOLE_KEYCLOAK_TOKEN_URL",
        "CONSOLE_KEYCLOAK_ADMIN_BASE_URL",
        "KEYCLOAK_ADMIN_BASE_URL",
        "CONSOLE_KEYCLOAK_REALM",
        "KEYCLOAK_REALM",
        "CONSOLE_KEYCLOAK_USERNAME",
        "KEYCLOAK_ADMIN_USERNAME",
        "KEYCLOAK_USERNAME",
        "CONSOLE_KEYCLOAK_PASSWORD",
        "KEYCLOAK_ADMIN_PASSWORD",
        "KEYCLOAK_PASSWORD",
        "CONSOLE_KEYCLOAK_CLIENT_ID",
        "CONSOLE_KEYCLOAK_CLIENT_SECRET",
    )
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("KEYCLOAK_ISSUER", "https://auth.example.com/realms/truffles")
    monkeypatch.setenv("KEYCLOAK_USERNAME", "svc-ops")
    monkeypatch.setenv("KEYCLOAK_PASSWORD", "secret-pass")

    resolved = console_router._resolve_keycloak_admin_config()

    assert resolved["token_url"] == "https://auth.example.com/realms/truffles/protocol/openid-connect/token"
    assert resolved["admin_base_url"] == "https://auth.example.com"
    assert resolved["realm"] == "truffles"
    assert resolved["admin_username"] == "svc-ops"
    assert resolved["admin_password"] == "secret-pass"
    assert resolved["client_id"] == "admin-cli"
    assert resolved["client_secret"] is None


def test_resolve_keycloak_admin_config_missing_credentials_includes_alias_hints(monkeypatch):
    env_keys = (
        "CONSOLE_OIDC_ISSUER",
        "KEYCLOAK_ISSUER",
        "CONSOLE_KEYCLOAK_TOKEN_URL",
        "CONSOLE_KEYCLOAK_ADMIN_BASE_URL",
        "KEYCLOAK_ADMIN_BASE_URL",
        "CONSOLE_KEYCLOAK_REALM",
        "KEYCLOAK_REALM",
        "CONSOLE_KEYCLOAK_USERNAME",
        "KEYCLOAK_ADMIN_USERNAME",
        "KEYCLOAK_USERNAME",
        "CONSOLE_KEYCLOAK_PASSWORD",
        "KEYCLOAK_ADMIN_PASSWORD",
        "KEYCLOAK_PASSWORD",
    )
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("KEYCLOAK_ISSUER", "https://auth.example.com/realms/truffles")

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_keycloak_admin_config()

    assert exc_info.value.code == "INTEGRATION_UNAVAILABLE"
    details = exc_info.value.details or {}
    missing = details.get("missing") or []
    aliases = details.get("aliases") or {}
    assert "CONSOLE_KEYCLOAK_USERNAME" in missing
    assert "CONSOLE_KEYCLOAK_PASSWORD" in missing
    assert aliases.get("CONSOLE_KEYCLOAK_USERNAME") == ["KEYCLOAK_ADMIN_USERNAME", "KEYCLOAK_USERNAME"]
    assert aliases.get("CONSOLE_KEYCLOAK_PASSWORD") == ["KEYCLOAK_ADMIN_PASSWORD", "KEYCLOAK_PASSWORD"]


@pytest.mark.asyncio
async def test_create_branch_bootstrap_accounts_return_created_agents(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    client = SimpleNamespace(id=client_id, company_id=company_id)
    db.query.return_value.filter.return_value.first.return_value = client

    helper_calls = []

    def _fake_create_agent_with_membership(
        _db,
        *,
        client,
        role,
        branch,
        name,
        is_active,
        oidc_subject,
        linked_from,
        now,
    ):
        helper_calls.append(
            {
                "role": role,
                "branch_id": branch.id if branch else None,
                "name": name,
                "is_active": is_active,
                "linked_from": linked_from,
            }
        )
        return SimpleNamespace(
            id=uuid4(),
            name=name,
            role=role,
            client_id=client.id,
            branch_id=branch.id if branch else None,
            is_active=is_active,
        )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_create_agent_with_membership", _fake_create_agent_with_membership)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *args, **kwargs: None)

    response = await console_router.create_branch(
        request=Mock(),
        body=ConsoleBranchCreateRequest(
            client_id=client_id,
            slug="branch-1",
            name="Branch 1",
            is_active=False,
            bootstrap_accounts=[
                ConsoleBranchBootstrapAccountTemplate(role="owner", name="Owner User"),
                ConsoleBranchBootstrapAccountTemplate(role="manager", name="Manager User"),
            ],
        ),
        db=db,
    )

    assert len(response.created_agents) == 2
    assert helper_calls[0]["role"] == "owner"
    assert helper_calls[0]["branch_id"] is None
    assert helper_calls[1]["role"] == "manager"
    assert helper_calls[1]["branch_id"] == response.branch.id
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_branch_rejects_deprecated_bootstrap_role(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=client_id, company_id=company_id)

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_branch(
            request=Mock(),
            body=ConsoleBranchCreateRequest(
                client_id=client_id,
                slug="branch-deprecated-role",
                name="Branch Deprecated Role",
                is_active=False,
                bootstrap_accounts=[
                    ConsoleBranchBootstrapAccountTemplate(role="support", name="Support User"),
                ],
            ),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "deprecated for assignment" in exc_info.value.message


@pytest.mark.asyncio
async def test_create_branch_rejects_invalid_timezone(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=client_id, company_id=company_id)

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_branch(
            request=Mock(),
            body=ConsoleBranchCreateRequest(
                client_id=client_id,
                slug="branch-1",
                name="Branch 1",
                phone="+77001112233",
                timezone="Mars/Phobos",
            ),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_update_branch_rejects_invalid_telegram_chat_id(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        slug="branch-a",
        name="Branch A",
        instance_id="inst-1",
        phone="+77001112233",
        telegram_chat_id=None,
        knowledge_tag=None,
        timezone="Asia/Almaty",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="booking",
        onboarding_updated_at=None,
        go_live_state="approved",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_branch(
            branch_id=branch.id,
            request=Mock(),
            body=ConsoleBranchUpdateRequest(telegram_chat_id="not-a-chat-id"),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_update_branch_normalizes_knowledge_tag_to_lowercase(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        slug="branch-a",
        name="Branch A",
        instance_id="inst-1",
        phone="+77001112233",
        telegram_chat_id=None,
        knowledge_tag=None,
        timezone="Asia/Almaty",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="booking",
        onboarding_updated_at=None,
        go_live_state="approved",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.update_branch(
        branch_id=branch.id,
        request=Mock(),
        body=ConsoleBranchUpdateRequest(knowledge_tag="Demo_Tag"),
        db=db,
    )

    assert response.knowledge_tag == "demo_tag"
    assert branch.knowledge_tag == "demo_tag"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_rejects_blank_phone(monkeypatch):
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(role="platform_admin"),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_onboarding_autopilot(
            request=Mock(),
            body=ConsoleOnboardingAutopilotRequest(
                phone="  ",
                instance_id="inst-1",
            ),
            db=Mock(),
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_blocks_cross_tenant_company(monkeypatch):
    allowed_client_id = uuid4()
    allowed_company_id = uuid4()
    foreign_company_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=foreign_company_id)

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[SimpleNamespace(id=allowed_client_id, company_id=allowed_company_id)],
            client_id=allowed_client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_onboarding_autopilot(
            request=Mock(),
            body=ConsoleOnboardingAutopilotRequest(
                phone="+77001112233",
                instance_id="inst-1",
                company_id=foreign_company_id,
            ),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_blocks_cross_tenant_client(monkeypatch):
    allowed_client_id = uuid4()
    allowed_company_id = uuid4()
    foreign_client_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = [
        SimpleNamespace(id=allowed_company_id),
        SimpleNamespace(id=foreign_client_id),
    ]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[SimpleNamespace(id=allowed_client_id, company_id=allowed_company_id)],
            client_id=allowed_client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_onboarding_autopilot(
            request=Mock(),
            body=ConsoleOnboardingAutopilotRequest(
                phone="+77001112233",
                instance_id="inst-1",
                company_id=allowed_company_id,
                client_id=foreign_client_id,
            ),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_activate_requires_scorecard_pass(monkeypatch):
    now = datetime.now(timezone.utc)
    company_id = uuid4()
    client_id = uuid4()
    branch_id = uuid4()
    company = SimpleNamespace(id=company_id, name="Company A", billing_info={})
    client = SimpleNamespace(
        id=client_id,
        name="client-a",
        status="active",
        config={},
        company_id=company_id,
        created_at=now,
        updated_at=now,
    )
    branch = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        slug="branch-a",
        name="Branch A",
        timezone="Asia/Almaty",
        phone="+77001112233",
        instance_id="inst-1",
        telegram_chat_id=None,
        knowledge_tag="knowledge-a",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="branch_draft",
        onboarding_updated_at=now,
        go_live_state="approved",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        webhook_secret=None,
        created_at=now,
        updated_at=now,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = [
        company,
        client,
        None,
        None,
        branch,
    ]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_capability", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_onboarding_contract", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_next_available_branch_slug", lambda *args, **kwargs: "branch-a")
    monkeypatch.setattr(
        console_router,
        "_ensure_client_webhook_secret_from_instance",
        lambda *args, **kwargs: ("whs_test", "https://example.com/webhook", False),
    )
    monkeypatch.setattr(console_router, "build_intake_payload", lambda *args, **kwargs: {"client_pack": {}})
    monkeypatch.setattr(console_router, "upsert_draft", lambda *args, **kwargs: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(console_router, "evaluate_intake_payload", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(
        console_router,
        "build_intake_pack_quality_summary",
        lambda *args, **kwargs: SimpleNamespace(
            compile=SimpleNamespace(
                status="pass",
                infra_valid=True,
                schema_version="compiled_pack.v1",
                hash="hash-1",
                pack_index_hash="pack-hash-1",
                signal_graph_present=True,
                policy_bundle_present=True,
                errors=[],
            ),
            quality_matrix=SimpleNamespace(
                status="pass",
                infra_valid=True,
                semantic_valid=True,
                required_fields_count=1,
                missing_fields_count=0,
                critical_missing_fields_count=0,
                integrity_missing_count=0,
                missing_fields=[],
                critical_missing_fields=[],
                integrity_missing=[],
                dimensions=[
                    SimpleNamespace(
                        id="pack_compile",
                        status="pass",
                        required=True,
                        details=[],
                    )
                ],
                regressions=[],
                comparison_blocked=False,
                comparison_block_reason=None,
            ),
        ),
    )
    monkeypatch.setattr(console_router, "build_onboarding_inputs", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(console_router, "build_onboarding_status", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *args, **kwargs: SimpleNamespace(
            ready=False,
            missing=["payment_confirmed"],
            checks=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.GO_NO_GO,
                    required=True,
                    passed=False,
                    missing=["payment_confirmed"],
                )
            ],
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_onboarding_autopilot(
            request=Mock(),
            body=ConsoleOnboardingAutopilotRequest(
                company_id=company_id,
                client_id=client_id,
                branch_id=branch_id,
                phone="+77001112233",
                instance_id="inst-1",
                activate_branch=True,
            ),
            db=db,
        )

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"
    assert exc_info.value.details["operation"] == "onboarding_autopilot_activate"
    assert exc_info.value.details["scorecard_status"] == "fail"
    assert exc_info.value.details["missing"] == ["payment_confirmed"]
    db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_preserves_existing_provider_binding(monkeypatch):
    now = datetime.now(timezone.utc)
    company_id = uuid4()
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    company = SimpleNamespace(id=company_id, name="Company A", billing_info={})
    client = SimpleNamespace(
        id=client_id,
        name="client-a",
        status="active",
        config={},
        company_id=company_id,
        created_at=now,
        updated_at=now,
    )
    branch = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        slug="branch-a",
        name="Branch A",
        timezone="Asia/Almaty",
        phone="+77001112233",
        instance_id="inst-existing",
        telegram_chat_id=None,
        knowledge_tag="knowledge-a",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="branch_draft",
        onboarding_updated_at=now,
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        webhook_secret=None,
        created_at=now,
        updated_at=now,
    )
    contract_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payment_status="pending",
        payment_confirmed_at=None,
        payment_confirmed_by=None,
        payload_json={
            "domain_slug": None,
            "purchased": {
                "channels": {"whatsapp": True},
                "providers": {},
                "features": {},
            },
            "provider_binding": {
                "whatsapp": {
                    "provider": "chatflow",
                    "instance_id": "inst-existing",
                    "webhook_status": "configured",
                    "paid_until": "2030-01-01",
                    "notes": "existing binding",
                }
            },
        },
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    capability_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payload_json={
            "channels": {"whatsapp": True},
            "providers": {},
            "features": {},
        },
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = [
        company,
        client,
        None,
        None,
        branch,
    ]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_capability", lambda *args, **kwargs: capability_record)
    monkeypatch.setattr(console_router, "_get_latest_onboarding_contract", lambda *args, **kwargs: contract_record)
    monkeypatch.setattr(console_router, "_next_available_branch_slug", lambda *args, **kwargs: "branch-a")
    monkeypatch.setattr(
        console_router,
        "_ensure_client_webhook_secret_from_instance",
        lambda *args, **kwargs: ("whs_test", "https://example.com/webhook", False),
    )
    monkeypatch.setattr(console_router, "build_intake_payload", lambda *args, **kwargs: {"client_pack": {}})
    monkeypatch.setattr(console_router, "upsert_draft", lambda *args, **kwargs: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(console_router, "evaluate_intake_payload", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(console_router, "build_onboarding_inputs", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        console_router,
        "build_onboarding_status",
        lambda *args, **kwargs: SimpleNamespace(
            current_step=console_router.OnboardingStep.BRANCH_DRAFT,
            steps=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.BRANCH_DRAFT,
                    status="complete",
                    required=True,
                    missing=[],
                )
            ],
        ),
    )
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *args, **kwargs: SimpleNamespace(ready=True, missing=[], checks=[]),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.run_onboarding_autopilot(
        request=Mock(),
        body=ConsoleOnboardingAutopilotRequest(
            company_id=company_id,
            client_id=client_id,
            branch_id=branch_id,
            phone="+77001112233",
            instance_id="inst-new",
            activate_branch=False,
        ),
        db=db,
    )

    binding = response.onboarding_contract.payload.provider_binding.whatsapp
    assert binding is not None
    assert binding.provider == "chatflow"
    assert binding.instance_id == "inst-existing"
    assert binding.webhook_status == "configured"
    assert binding.paid_until == "2030-01-01"
    assert binding.notes == "existing binding"
    assert response.intake.compile is not None
    assert response.intake.quality_matrix is not None
    assert response.intake.quality_matrix.status in {"pass", "fail"}


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_autofills_provider_binding_instance_id(monkeypatch):
    now = datetime.now(timezone.utc)
    company_id = uuid4()
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    company = SimpleNamespace(id=company_id, name="Company A", billing_info={})
    client = SimpleNamespace(
        id=client_id,
        name="client-a",
        status="active",
        config={},
        company_id=company_id,
        created_at=now,
        updated_at=now,
    )
    branch = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        slug="branch-a",
        name="Branch A",
        timezone="Asia/Almaty",
        phone="+77001112233",
        instance_id="inst-existing",
        telegram_chat_id=None,
        knowledge_tag="knowledge-a",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="branch_draft",
        onboarding_updated_at=now,
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        webhook_secret=None,
        created_at=now,
        updated_at=now,
    )
    contract_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payment_status="pending",
        payment_confirmed_at=None,
        payment_confirmed_by=None,
        payload_json={
            "domain_slug": None,
            "purchased": {
                "channels": {"whatsapp": True},
                "providers": {},
                "features": {},
            },
            "provider_binding": {"whatsapp": {}},
        },
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    capability_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payload_json={
            "channels": {"whatsapp": True},
            "providers": {},
            "features": {},
        },
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = [
        company,
        client,
        None,
        None,
        branch,
    ]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_capability", lambda *args, **kwargs: capability_record)
    monkeypatch.setattr(console_router, "_get_latest_onboarding_contract", lambda *args, **kwargs: contract_record)
    monkeypatch.setattr(console_router, "_next_available_branch_slug", lambda *args, **kwargs: "branch-a")
    monkeypatch.setattr(
        console_router,
        "_ensure_client_webhook_secret_from_instance",
        lambda *args, **kwargs: ("whs_test", "https://example.com/webhook", False),
    )
    monkeypatch.setattr(console_router, "build_intake_payload", lambda *args, **kwargs: {"client_pack": {}})
    monkeypatch.setattr(console_router, "upsert_draft", lambda *args, **kwargs: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(console_router, "evaluate_intake_payload", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(console_router, "build_onboarding_inputs", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        console_router,
        "build_onboarding_status",
        lambda *args, **kwargs: SimpleNamespace(
            current_step=console_router.OnboardingStep.BRANCH_DRAFT,
            steps=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.BRANCH_DRAFT,
                    status="complete",
                    required=True,
                    missing=[],
                )
            ],
        ),
    )
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *args, **kwargs: SimpleNamespace(ready=True, missing=[], checks=[]),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.run_onboarding_autopilot(
        request=Mock(),
        body=ConsoleOnboardingAutopilotRequest(
            company_id=company_id,
            client_id=client_id,
            branch_id=branch_id,
            phone="+77001112233",
            instance_id="inst-autopilot",
            provider_binding=OnboardingProviderBindingPayload(
                whatsapp=OnboardingProviderBindingWhatsApp(
                    provider="chatflow",
                    webhook_status="configured",
                    paid_until="2030-02-10",
                    owner="platform-admin",
                    rebind_required=False,
                    alert_state="warn",
                    notes="new binding from autopilot",
                )
            ),
            activate_branch=False,
        ),
        db=db,
    )

    binding = response.onboarding_contract.payload.provider_binding.whatsapp
    assert binding is not None
    assert binding.provider == "chatflow"
    assert binding.instance_id == "inst-autopilot"
    assert binding.webhook_status == "configured"
    assert binding.paid_until == "2030-02-10"
    assert binding.owner == "platform-admin"
    assert binding.next_renewal_at == "2030-02-10"
    assert binding.rebind_required is False
    assert binding.alert_state == "warn"
    assert binding.notes == "new binding from autopilot"


def test_membership_role_guard_rejects_platform_admin():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_role_is_assignable("platform_admin")
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.parametrize("deprecated_role", ["support", "specialist"])
def test_membership_role_guard_rejects_deprecated_roles(deprecated_role: str):
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_role_is_assignable(deprecated_role)
    assert exc_info.value.code == "INVALID_PARAM"
    assert "deprecated for assignment" in exc_info.value.message


def test_membership_agent_guard_rejects_platform_admin_agent():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_agent_is_mutable(
            SimpleNamespace(role="platform_admin"),
        )
    assert exc_info.value.code == "INVALID_STATE"


def test_create_agent_with_membership_skips_membership_for_platform_admin(monkeypatch):
    db = Mock()
    added = []
    db.add.side_effect = added.append
    client = SimpleNamespace(id=uuid4(), company_id=uuid4())

    monkeypatch.setattr(console_router, "_ensure_unique_oidc_subject", lambda *_args, **_kwargs: None)

    agent = console_router._create_agent_with_membership(
        db,
        client=client,
        role="platform_admin",
        branch=None,
        name="Platform Admin",
        is_active=True,
        oidc_subject=None,
        linked_from="test",
    )

    assert agent.role == "platform_admin"
    assert not any(isinstance(item, AgentMembership) for item in added)


def test_membership_guard_blocks_self_privileged_downgrade():
    actor_id = uuid4()
    membership = SimpleNamespace(
        id=uuid4(),
        agent_id=actor_id,
        is_active=True,
        role="owner",
    )
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))
    agent = SimpleNamespace(client_id=uuid4())

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_change_keeps_privileged_access(
            Mock(),
            context=context,
            membership=membership,
            agent=agent,
            next_role="manager",
            next_is_active=False,
        )

    assert exc_info.value.code == "INVALID_STATE"


def test_membership_guard_blocks_last_privileged_membership(monkeypatch):
    actor_id = uuid4()
    membership = SimpleNamespace(
        id=uuid4(),
        agent_id=uuid4(),
        is_active=True,
        role="admin",
    )
    client_id = uuid4()
    client = SimpleNamespace(id=client_id)
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))
    agent = SimpleNamespace(client_id=client_id)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "_has_other_privileged_access_for_client",
        lambda *_args, **_kwargs: False,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_change_keeps_privileged_access(
            db,
            context=context,
            membership=membership,
            agent=agent,
            next_role="manager",
            next_is_active=False,
        )

    assert exc_info.value.code == "INVALID_STATE"


def test_agent_lifecycle_guard_blocks_platform_admin():
    context = SimpleNamespace(agent=SimpleNamespace(id=uuid4()))
    agent = SimpleNamespace(id=uuid4(), role="platform_admin", client_id=uuid4())

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_agent_lifecycle_is_mutable(
            Mock(),
            context=context,
            agent=agent,
            enabling=False,
        )

    assert exc_info.value.code == "INVALID_STATE"


def test_agent_lifecycle_guard_blocks_self_disable():
    actor_id = uuid4()
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))
    agent = SimpleNamespace(id=actor_id, role="owner", client_id=uuid4())

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_agent_lifecycle_is_mutable(
            Mock(),
            context=context,
            agent=agent,
            enabling=False,
        )

    assert exc_info.value.code == "INVALID_STATE"


def test_agent_lifecycle_guard_blocks_last_privileged_agent(monkeypatch):
    actor_id = uuid4()
    target_agent_id = uuid4()
    client_id = uuid4()
    client = SimpleNamespace(id=client_id)
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))
    agent = SimpleNamespace(id=target_agent_id, role="admin", client_id=client_id)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "_has_other_privileged_access_for_client",
        lambda *_args, **_kwargs: False,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_agent_lifecycle_is_mutable(
            db,
            context=context,
            agent=agent,
            enabling=False,
        )

    assert exc_info.value.code == "INVALID_STATE"


def test_require_branch_go_live_gate_blocks_pending_state():
    branch = SimpleNamespace(
        go_live_state="pending",
        go_live_reason="missing approvals",
        go_live_waiver_until=None,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_branch_go_live_gate(branch, operation="branch_activate")

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"


@pytest.mark.asyncio
async def test_update_branch_blocks_activation_without_go_live_approval(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        slug="branch-a",
        name="Branch A",
        instance_id="inst-1",
        phone="+77001112233",
        telegram_chat_id=None,
        knowledge_tag=None,
        timezone="Asia/Almaty",
        working_hours={},
        booking_settings={},
        is_active=False,
        onboarding_state="booking",
        onboarding_updated_at=None,
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_branch(
            branch_id=branch.id,
            request=Mock(),
            body=ConsoleBranchUpdateRequest(is_active=True),
            db=db,
        )

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"


@pytest.mark.asyncio
async def test_get_onboarding_scorecard_returns_fail_payload(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    context = _mock_context(role="owner")
    context.branches = [branch]

    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *_args, **_kwargs: SimpleNamespace(
            ready=False,
            missing=["payment_confirmed"],
            sla_control_loop=SimpleNamespace(
                status="warn",
                reminder_1_minutes=10,
                reminder_2_minutes=45,
                escalation_timeout_minutes=120,
                pending_total=1,
                warning_total=1,
                breached_total=0,
                provider_status="configured",
                provider_paid_until="2026-03-10",
                provider_days_to_renewal=21,
                provider_alert_state="ok",
                active_incidents=["handover_sla_warning"],
                recommended_actions=["review_pending_handovers"],
            ),
            operational_pipeline=SimpleNamespace(
                status="fail",
                blocked=True,
                current_stage_id="contract_alignment",
                blockers=["payment_confirmed"],
                next_actions=["complete_contract_and_payment"],
                stages=[
                    SimpleNamespace(
                        id="contract_alignment",
                        label="Contract alignment",
                        owner_lane="owner_admin",
                        required=True,
                        status="fail",
                        blockers=["payment_confirmed"],
                        next_action="complete_contract_and_payment",
                    ),
                    SimpleNamespace(
                        id="go_live_control",
                        label="Go-live control",
                        owner_lane="owner_admin",
                        required=True,
                        status="fail",
                        blockers=["payment_confirmed"],
                        next_action="resolve_go_live_blockers",
                    ),
                ],
            ),
            document_ingestion=SimpleNamespace(
                status="fail",
                valid=False,
                source="draft",
                missing_fields=["client_pack.policy.hard_law"],
                critical_missing_fields=["client_pack.policy.hard_law"],
            ),
            checks=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.GO_NO_GO,
                    required=True,
                    passed=False,
                    missing=["payment_confirmed"],
                )
            ],
            readiness_kernel=SimpleNamespace(
                status="fail",
                blocker_codes=["go_no_go:payment_confirmed", "delivery:backlog_critical"],
                next_action_codes=["resolve_go_no_go_missing"],
                auto_questions=[
                    SimpleNamespace(
                        code="go_no_go:payment_confirmed",
                        question="Подтвердите оплату по договору.",
                        blocking_go_live=True,
                    )
                ],
                dimensions=[
                    SimpleNamespace(
                        id="go_no_go_contract",
                        status="fail",
                        blocker_codes=["go_no_go:payment_confirmed"],
                        next_action_codes=["resolve_go_no_go_missing"],
                    )
                ],
                shadow_hard_gate_blockers=["go_no_go:payment_confirmed", "delivery:backlog_critical"],
            ),
        ),
    )

    response = await console_router.get_onboarding_scorecard(
        request=Mock(),
        branch_id=branch.id,
        db=Mock(),
    )

    assert response.branch_id == branch.id
    assert response.status == "fail"
    assert response.ready is False
    assert response.missing == ["payment_confirmed"]
    assert response.checks[0].id == "go_no_go"
    assert response.checks[0].passed is False
    assert response.document_ingestion is not None
    assert response.document_ingestion.status == "fail"
    assert response.document_ingestion.valid is False
    assert response.document_ingestion.source == "draft"
    assert response.sla_control_loop is not None
    assert response.sla_control_loop.status == "warn"
    assert response.sla_control_loop.warning_total == 1
    assert response.sla_control_loop.active_incidents == ["handover_sla_warning"]
    assert response.operational_pipeline is not None
    assert response.operational_pipeline.status == "fail"
    assert response.operational_pipeline.blocked is True
    assert response.operational_pipeline.current_stage_id == "contract_alignment"
    assert response.operational_pipeline.blockers == ["payment_confirmed"]
    assert response.operational_pipeline.stages[0].id == "contract_alignment"
    assert response.readiness_kernel is not None
    assert response.readiness_kernel.status == "fail"
    assert "go_no_go:payment_confirmed" in response.readiness_kernel.blocker_codes
    assert response.readiness_kernel.shadow_hard_gate.status == "fail"
    assert "delivery:backlog_critical" in response.readiness_kernel.shadow_hard_gate.blocker_codes


def test_require_branch_scorecard_ready_allows_shadow_blockers_when_hard_gate_disabled(monkeypatch):
    scorecard = SimpleNamespace(
        ready=True,
        missing=[],
        checks=[
            SimpleNamespace(
                id=console_router.OnboardingStep.GO_NO_GO,
                required=True,
                passed=True,
                missing=[],
            )
        ],
        readiness_kernel=SimpleNamespace(
            status="fail",
            blocker_codes=["delivery:backlog_critical"],
            next_action_codes=["run_outbox_process_and_review_failed"],
            shadow_hard_gate_blockers=["delivery:backlog_critical"],
        ),
    )
    monkeypatch.setattr(console_router, "build_onboarding_scorecard", lambda *_args, **_kwargs: scorecard)
    monkeypatch.setattr(console_router, "_ONBOARDING_READINESS_HARD_GATE_ENABLED", False)
    monkeypatch.setattr(
        console_router,
        "_ONBOARDING_READINESS_HARD_GATE_CODES",
        {"delivery:backlog_critical"},
    )

    console_router._require_branch_scorecard_ready(
        db=Mock(),
        branch=SimpleNamespace(client_id=uuid4(), id=uuid4()),
        operation="branch_activate",
    )


def test_require_branch_scorecard_ready_blocks_when_hard_gate_enabled(monkeypatch):
    scorecard = SimpleNamespace(
        ready=True,
        missing=[],
        checks=[
            SimpleNamespace(
                id=console_router.OnboardingStep.GO_NO_GO,
                required=True,
                passed=True,
                missing=[],
            )
        ],
        readiness_kernel=SimpleNamespace(
            status="fail",
            blocker_codes=["delivery:backlog_critical"],
            next_action_codes=["run_outbox_process_and_review_failed"],
            shadow_hard_gate_blockers=["delivery:backlog_critical"],
        ),
    )
    monkeypatch.setattr(console_router, "build_onboarding_scorecard", lambda *_args, **_kwargs: scorecard)
    monkeypatch.setattr(console_router, "_ONBOARDING_READINESS_HARD_GATE_ENABLED", True)
    monkeypatch.setattr(
        console_router,
        "_ONBOARDING_READINESS_HARD_GATE_CODES",
        {"delivery:backlog_critical"},
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_branch_scorecard_ready(
            db=Mock(),
            branch=SimpleNamespace(client_id=uuid4(), id=uuid4()),
            operation="branch_activate",
        )

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"
    assert exc_info.value.details["missing"] == ["delivery:backlog_critical"]
    assert exc_info.value.details["scorecard_status"] == "pass"
    assert exc_info.value.details["readiness_kernel"]["shadow_hard_gate"]["enforced"] is True


@pytest.mark.asyncio
async def test_approve_branch_go_live_sets_state_and_clears_waiver(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=datetime.now(timezone.utc) + timedelta(hours=2),
        go_live_waiver_reason="old waiver",
        go_live_waiver_by=uuid4(),
        updated_at=None,
        slug="branch-a",
        name="Branch A",
        is_active=False,
        instance_id="inst-1",
        telegram_chat_id=None,
        phone="+77001112233",
        knowledge_tag=None,
        timezone="Asia/Almaty",
        working_hours={},
        booking_settings={},
        onboarding_state="booking",
        onboarding_updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    actor_id = uuid4()
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: SimpleNamespace(
            agent=SimpleNamespace(id=actor_id, name="Actor", role="platform_admin"),
            role="platform_admin",
            client=SimpleNamespace(id=branch.client_id, company_id=uuid4()),
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            branches=[],
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *_args, **_kwargs: SimpleNamespace(
            ready=True,
            missing=[],
            checks=[SimpleNamespace(id=console_router.OnboardingStep.GO_NO_GO, required=True, passed=True)],
        ),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.approve_branch_go_live(
        branch_id=branch.id,
        request=Mock(),
        body=ConsoleBranchGoLiveDecisionRequest(reason="checklist passed"),
        db=db,
    )

    assert response.go_live_state == "approved"
    assert response.go_live_allowed is True
    assert branch.go_live_state == "approved"
    assert branch.go_live_waiver_until is None
    assert branch.go_live_waiver_reason is None
    assert branch.go_live_waiver_by is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_approve_branch_go_live_requires_prerequisites(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *_args, **_kwargs: SimpleNamespace(
            ready=False,
            missing=["payment_confirmed"],
            checks=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.GO_NO_GO,
                    required=True,
                    passed=False,
                )
            ],
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.approve_branch_go_live(
            branch_id=branch.id,
            request=Mock(),
            body=ConsoleBranchGoLiveDecisionRequest(reason="force"),
            db=db,
        )

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"
    assert exc_info.value.details["missing"] == ["payment_confirmed"]
    assert exc_info.value.details["scorecard_status"] == "fail"
    assert "go_no_go" in exc_info.value.details["failed_checks"]


@pytest.mark.asyncio
async def test_waive_branch_go_live_validates_ttl(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.waive_branch_go_live(
            branch_id=branch.id,
            request=Mock(),
            body=ConsoleBranchGoLiveWaiverRequest(reason="temporary", ttl_hours=0),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_waive_branch_go_live_requires_prerequisites(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        go_live_state="pending",
        go_live_reason=None,
        go_live_reviewed_at=None,
        go_live_reviewed_by=None,
        go_live_waiver_until=None,
        go_live_waiver_reason=None,
        go_live_waiver_by=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = branch

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=branch.client_id, company_id=uuid4())],
            client_id=branch.client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_scorecard",
        lambda *_args, **_kwargs: SimpleNamespace(
            ready=False,
            missing=["provider_binding.whatsapp.webhook_status"],
            checks=[
                SimpleNamespace(
                    id=console_router.OnboardingStep.GO_NO_GO,
                    required=True,
                    passed=False,
                )
            ],
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.waive_branch_go_live(
            branch_id=branch.id,
            request=Mock(),
            body=ConsoleBranchGoLiveWaiverRequest(reason="temporary", ttl_hours=24),
            db=db,
        )

    assert exc_info.value.code == "GO_LIVE_GATE_REQUIRED"
    assert exc_info.value.details["operation"] == "branch_go_live_waive"
    assert exc_info.value.details["missing"] == ["provider_binding.whatsapp.webhook_status"]
    assert "go_no_go" in exc_info.value.details["failed_checks"]
