from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module():
    repo_root = Path(__file__).resolve().parents[2]
    for path_value in (repo_root, repo_root / "ops"):
        as_text = str(path_value)
        if as_text not in sys.path:
            sys.path.insert(0, as_text)
    module_path = repo_root / "ops" / "console_tenants_perf_long_run.py"
    spec = importlib.util.spec_from_file_location("console_tenants_perf_long_run", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_scope_from_portfolio_payload_returns_first_valid_company_client_pair() -> None:
    module = _load_module()
    payload = {
        "clients": {
            "items": [
                {"id": " ", "company_id": " "},
                {"id": "client-2", "company_id": "company-2"},
                {"id": "client-3", "company_id": "company-3"},
            ]
        }
    }

    company_id, client_id = module._extract_scope_from_portfolio_payload(payload)

    assert company_id == "company-2"
    assert client_id == "client-2"


def test_extract_scope_from_portfolio_payload_returns_none_when_no_valid_scope() -> None:
    module = _load_module()
    payload = {"clients": {"items": [{"id": "client-1", "company_id": " "}]}}

    company_id, client_id = module._extract_scope_from_portfolio_payload(payload)

    assert company_id is None
    assert client_id is None


def test_extract_scope_from_portfolio_payload_handles_non_dict_payload() -> None:
    module = _load_module()

    company_id, client_id = module._extract_scope_from_portfolio_payload(["invalid"])

    assert company_id is None
    assert client_id is None
