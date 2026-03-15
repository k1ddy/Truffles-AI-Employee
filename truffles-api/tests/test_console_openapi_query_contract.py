from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


def _get_parameter(spec: dict, path: str, method: str, name: str) -> dict:
    operation = (((spec.get("paths") or {}).get(path) or {}).get(method)) or {}
    for parameter in operation.get("parameters") or []:
        if parameter.get("name") == name:
            return parameter
    raise AssertionError(f"missing parameter {name} on {method.upper()} {path}")


def test_optional_query_params_do_not_advertise_literal_null_values() -> None:
    spec = _load_console_contract()

    checks = [
        ("/console/v1/calendar/bookings", "get", "cursor"),
        ("/console/v1/cases/{case_id}/assignees", "get", "policy"),
        ("/console/v1/admin/domain-catalog", "get", "status"),
        ("/console/v1/onboarding/scorecard", "get", "branch_id"),
    ]

    for path, method, name in checks:
        schema = _get_parameter(spec, path, method, name).get("schema") or {}
        any_of = schema.get("anyOf") or []
        assert not any(
            isinstance(item, dict) and item.get("type") == "null"
            for item in any_of
        ), f"{method.upper()} {path} query param {name} must not expose literal null in OpenAPI"
