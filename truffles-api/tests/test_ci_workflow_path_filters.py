from pathlib import Path

import yaml


def _load_filters() -> dict[str, list[str]]:
    repo_root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load(
        (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["changes"]["steps"]
    filter_step = next(
        step for step in steps if str(step.get("uses", "")).startswith("dorny/paths-filter@")
    )
    return yaml.safe_load(filter_step["with"]["filters"])


def test_activation_deploy_paths_force_deploy_required() -> None:
    filters = _load_filters()

    assert "scripts/restart_knowledge_activation_service.sh" in filters["deploy_required"]
    assert "scripts/knowledge_activation_postdeploy.sh" in filters["deploy_required"]
    assert "ops/knowledge_activation_closeout.py" in filters["deploy_required"]


def test_activation_deploy_paths_force_livecheck_required() -> None:
    filters = _load_filters()

    assert "scripts/restart_knowledge_activation_service.sh" in filters["livecheck_required"]
    assert "scripts/knowledge_activation_postdeploy.sh" in filters["livecheck_required"]
    assert "ops/**" in filters["livecheck_required"]
