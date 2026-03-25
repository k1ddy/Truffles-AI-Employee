from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_config(repo: Path) -> dict:
    config = {
        "version": "test",
        "hotspots": [
            {
                "path": "truffles-api/app/services/info_signal_service.py",
                "active_waiver": None,
                "tracked_function_names": {
                    "name_patterns": [r"^detect_.*followup.*$", r"^looks_like_.*policy.*$"],
                    "exact_allowlist": ["detect_known_followup", "looks_like_known_policy_message"],
                },
            },
            {
                "path": "truffles-api/app/core/intent_routing.py",
                "active_waiver": None,
                "tracked_policy_snapshot_reasons": {
                    "exact_allowlist": ["known_reason"],
                },
            },
        ],
    }
    path = repo / "docs" / "SEMANTIC_BRIDGE_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_hotspots(repo: Path, *, info_text: str, routing_text: str) -> None:
    info_path = repo / "truffles-api" / "app" / "services" / "info_signal_service.py"
    info_path.parent.mkdir(parents=True, exist_ok=True)
    info_path.write_text(info_text, encoding="utf-8")

    routing_path = repo / "truffles-api" / "app" / "core" / "intent_routing.py"
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text(routing_text, encoding="utf-8")


BASE_INFO = '''
def detect_known_followup():
    return None


def looks_like_known_policy_message():
    return False
'''

BASE_ROUTING = '''
class PolicyCoreRouteSnapshot:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def build():
    return PolicyCoreRouteSnapshot(reason="known_reason")
'''


def test_semantic_bridge_growth_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("semantic_bridge_growth_guard", SCRIPTS / "semantic_bridge_growth_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(repo, info_text=BASE_INFO, routing_text=BASE_ROUTING)

    violations = module.evaluate(repo, config)
    assert violations == []



def test_semantic_bridge_growth_guard_blocks_new_tracked_function(tmp_path: Path) -> None:
    module = load_module("semantic_bridge_growth_guard", SCRIPTS / "semantic_bridge_growth_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(
        repo,
        info_text=BASE_INFO
        + '\n\ndef detect_new_followup():\n    return True\n',
        routing_text=BASE_ROUTING,
    )

    violations = module.evaluate(repo, config)
    assert violations
    assert "tracked function set grew without waiver" in violations[0]
    assert "detect_new_followup" in violations[0]



def test_semantic_bridge_growth_guard_blocks_new_policy_snapshot_reason(tmp_path: Path) -> None:
    module = load_module("semantic_bridge_growth_guard", SCRIPTS / "semantic_bridge_growth_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(
        repo,
        info_text=BASE_INFO,
        routing_text=BASE_ROUTING
        + '\n\ndef build_extra():\n    return PolicyCoreRouteSnapshot(reason="new_reason")\n',
    )

    violations = module.evaluate(repo, config)
    assert violations
    assert "PolicyCoreRouteSnapshot reason set grew without waiver" in violations[0]
    assert "new_reason" in violations[0]
