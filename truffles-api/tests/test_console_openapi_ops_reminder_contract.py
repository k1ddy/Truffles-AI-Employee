from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


def test_ops_reminder_paths_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}

    expected_methods = {
        "/ops/reminders": {"get"},
        "/ops/reminders/retry": {"post"},
    }

    for path, required_ops in expected_methods.items():
        assert path in paths, f"missing path in console contract: {path}"
        available_ops = {key for key in (paths.get(path) or {}).keys() if isinstance(key, str)}
        for method in required_ops:
            assert method in available_ops, f"missing operation {method.upper()} {path}"


def test_ops_reminder_schemas_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    required_schemas = {
        "ReminderCounts",
        "ReminderErrorBucket",
        "ReminderItem",
        "ReminderListResponse",
        "ReminderRetryRequest",
        "ReminderRetryResponse",
    }

    for schema_name in required_schemas:
        assert schema_name in schemas, f"missing schema in console contract: {schema_name}"
