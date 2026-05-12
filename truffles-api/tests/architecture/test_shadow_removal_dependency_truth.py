from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "scripts" / "shadow_removal_dependency_truth.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("shadow_removal_dependency_truth", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shadow_removal_dependency_truth_passes_current_repo_static() -> None:
    module = _load_module()

    report = module.build_report(ROOT)

    assert report["valid"] is True
    assert report["blocking_references"] == []
    assert report["decision"] == "static_guard_ready"


def test_shadow_removal_dependency_truth_blocks_runtime_code_reference(tmp_path: Path) -> None:
    module = _load_module()
    runtime_file = tmp_path / "truffles-api" / "app" / "services" / "bad_shadow_client.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text(
        'SHADOW_URL = "http://truffles-provider-gateway/provider/inbound"\n',
        encoding="utf-8",
    )

    report = module.build_report(tmp_path)

    assert report["valid"] is False
    assert report["blocking_references"] == [
        {
            "service": "provider_gateway",
            "container_name": "truffles-provider-gateway",
            "path": "truffles-api/app/services/bad_shadow_client.py",
            "classification": "blocking_runtime_code",
            "token_type": "container_name",
            "token": "truffles-provider-gateway",
        }
    ]


def test_shadow_removal_dependency_truth_allows_docs_tests_and_self(tmp_path: Path) -> None:
    module = _load_module()
    docs_file = tmp_path / "docs" / "NOTE.md"
    test_file = tmp_path / "truffles-api" / "tests" / "test_shadow_doc.py"
    app_file = tmp_path / "truffles-api" / "app" / "provider_gateway_app.py"
    restart_file = tmp_path / "scripts" / "restart_provider_gateway.sh"
    for path in (docs_file, test_file, app_file, restart_file):
        path.parent.mkdir(parents=True, exist_ok=True)
    docs_file.write_text("truffles-provider-gateway\n", encoding="utf-8")
    test_file.write_text("import app.provider_gateway_app\n", encoding="utf-8")
    app_file.write_text("truffles-provider-gateway\n", encoding="utf-8")
    restart_file.write_text("uvicorn app.provider_gateway_app:app\n", encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["valid"] is True
    assert report["blocking_references"] == []
    assert report["static_reference_counts"]["allowed_doc_or_inventory"] == 1
    assert report["static_reference_counts"]["allowed_test"] == 1
    assert report["static_reference_counts"]["allowed_shadow_self"] == 3


def test_shadow_removal_dependency_truth_blocks_deploy_config_reference(tmp_path: Path) -> None:
    module = _load_module()
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(
        "services:\n  shadow:\n    container_name: truffles-outbox-service\n",
        encoding="utf-8",
    )

    report = module.build_report(tmp_path)

    assert report["valid"] is False
    assert report["blocking_references"][0]["classification"] == "blocking_deploy_config"
