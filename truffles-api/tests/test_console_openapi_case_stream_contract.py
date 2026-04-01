from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


def _find_path(paths: dict, path: str) -> dict | None:
    legacy = path
    prefixed = f"/console/v1{path}"
    if legacy in paths:
        return paths.get(legacy)
    if prefixed in paths:
        return paths.get(prefixed)
    return None


def test_case_stream_path_is_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/cases/{case_id}/stream")
    assert path_item is not None, "missing path in console contract: /cases/{case_id}/stream"
    assert "get" in path_item, "missing operation GET /cases/{case_id}/stream"


def test_case_stream_response_uses_event_stream_content_type() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/cases/{case_id}/stream") or {}
    get_op = path_item.get("get") or {}
    responses = get_op.get("responses") or {}
    ok_response = responses.get("200") or {}
    content = ok_response.get("content") or {}
    assert "text/event-stream" in content, "GET /cases/{case_id}/stream must expose text/event-stream"

