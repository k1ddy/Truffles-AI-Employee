import tomllib
from pathlib import Path


def _load_schemathesis_config() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "contracts" / "console_api" / "schemathesis.toml"
    return tomllib.loads(config_path.read_text(encoding="utf-8"))


def test_console_schemathesis_contract_uses_stable_demo_salon_seeds() -> None:
    config = _load_schemathesis_config()
    parameters = config.get("parameters") or {}

    assert parameters.get("client_id") == "c839d5dd-65be-4733-a5d2-72c9f70707f0"
    assert parameters.get("campaign_id") == "4c95e9e0-c42d-44e0-8f54-eebd27f4fb46"
    assert parameters.get("specialist_id") == "f3306db3-1028-4125-a50e-0c28535c2ef9"
    assert parameters.get("follow_up_owner_id") == "cccccccc-0000-0000-0000-000000000002"
    assert parameters.get("surface") == "cases"
    assert parameters.get("policy") == "least_open_cases"
    assert "branch_id" not in parameters


def test_console_schemathesis_contract_uses_branch_scope_overrides_for_branch_sensitive_ops() -> None:
    config = _load_schemathesis_config()
    operations = config.get("operations") or []

    branch_scope_ops = {
        op.get("include-path"): op.get("parameters")
        for op in operations
        if isinstance(op, dict)
        and op.get("include-path") in {
            "/console/v1/admin/domain-catalog",
            "/console/v1/admin/onboarding-blueprints",
            "/console/v1/admin/branch-changes",
            "/console/v1/admin/tool-registry",
            "/console/v1/admin/compliance-lifecycle/runs",
            "/console/v1/admin/compliance-lifecycle/runs/{run_id}",
            "/console/v1/admin/compliance-lifecycle/runs/{run_id}/artifact",
            "/console/v1/admin/compliance-policy-registry",
            "/console/v1/admin/policy-registry",
            "/console/v1/admin/sla-profile-registry",
            "/console/v1/admin/provider-lifecycle",
            "/console/v1/admin/memberships",
            "/console/v1/admin/routing-profiles",
            "/console/v1/admin/tenants/weekly-snapshots",
            "/console/v1/admin/tenants/portfolio",
            "/console/v1/admin/tenants/company-cockpit",
            "/console/v1/calendar/specialists",
            "/console/v1/cases",
            "/console/v1/cases/assignees",
        }
    }

    assert branch_scope_ops["/console/v1/admin/domain-catalog"] == {"status": "active"}
    assert branch_scope_ops["/console/v1/admin/onboarding-blueprints"] == {"domain_slug": "beauty"}
    assert branch_scope_ops["/console/v1/admin/branch-changes"]["branch_id"] == "b7f75692-951e-421a-aae6-f5db97394799"
    assert branch_scope_ops["/console/v1/admin/tool-registry"] == {
        "status": "active",
        "certification_status": "certified",
    }
    assert branch_scope_ops["/console/v1/admin/compliance-lifecycle/runs"] == {
        "scope": "branch",
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
        "data_class": "learned_responses",
        "operation": "retention_scan",
    }
    assert branch_scope_ops["/console/v1/admin/compliance-lifecycle/runs/{run_id}"] == {
        "scope": "branch",
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
        "data_class": "learned_responses",
        "operation": "retention_scan",
    }
    assert branch_scope_ops["/console/v1/admin/compliance-lifecycle/runs/{run_id}/artifact"] == {
        "scope": "branch",
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/admin/compliance-policy-registry"] == {
        "scope": "domain",
        "domain_key": "beauty",
        "data_class": "learned_responses",
    }
    assert branch_scope_ops["/console/v1/admin/policy-registry"] == {
        "scope": "branch",
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/admin/sla-profile-registry"] == {
        "scope": "domain",
        "domain_key": "beauty",
    }
    assert branch_scope_ops["/console/v1/admin/provider-lifecycle"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/admin/memberships"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/admin/routing-profiles"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/admin/tenants/weekly-snapshots"] == {
        "week_key": "2026-W11",
    }
    assert branch_scope_ops["/console/v1/admin/tenants/portfolio"] == {
        "q": "demo",
    }
    assert branch_scope_ops["/console/v1/admin/tenants/company-cockpit"] == {
        "client_q": "demo",
        "branch_q": "main",
    }
    assert branch_scope_ops["/console/v1/calendar/specialists"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }
    assert branch_scope_ops["/console/v1/cases"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
        "status": "open",
        "queue_view": "needs_reply",
        "assigned_to_me": "false",
        "unassigned": "false",
        "has_delivery_error": "false",
        "has_pending_outbox": "false",
        "has_human_lock": "false",
        "sort_by": "last_activity",
        "last_activity_since": "2026-03-16T00:00:00+00:00",
        "q": "demo",
        "phone": "+77001234567",
        "resolved_from": "2026-03-16",
        "resolved_to": "2026-03-17",
    }
    assert branch_scope_ops["/console/v1/cases/assignees"] == {
        "branch_id": "b7f75692-951e-421a-aae6-f5db97394799",
    }


def test_console_schemathesis_contract_disables_redirect_following_for_google_oauth() -> None:
    config = _load_schemathesis_config()
    operations = config.get("operations") or []

    redirect_ops = {
        op.get("include-path"): op.get("max-redirects")
        for op in operations
        if isinstance(op, dict) and op.get("include-path") in {
            "/console/v1/calendar/google/connect",
            "/console/v1/calendar/google/callback",
        }
    }

    assert redirect_ops == {
        "/console/v1/calendar/google/connect": 0,
        "/console/v1/calendar/google/callback": 0,
    }
