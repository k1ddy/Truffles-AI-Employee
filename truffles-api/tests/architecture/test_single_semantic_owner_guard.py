from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
SUPPORT_COPY_PATHS = (
    "prompts/llm_policy_core.md",
    "truffles-api/app/services/policy_prompt_snapshot_service.py",
    "truffles-api/app/services/policy_vocabulary_snapshot_service.py",
    "truffles-api/app/schemas/intent.py",
    "truffles-api/app/services/intent_service.py",
    "truffles-api/app/core/turn_planner.py",
    "truffles-api/app/core/consultant_runtime.py",
    "truffles-api/app/routers/webhook/decision.py",
    "ops/diagnose.py",
)
SUPPORT_PACKAGE_INITS = (
    "truffles-api/app/__init__.py",
    "truffles-api/app/services/__init__.py",
    "truffles-api/app/schemas/__init__.py",
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_guard_repo(repo: Path, module) -> None:
    for relative_path in module.FILE_RULES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    for relative_path in module.CANONICAL_WRITE_SCAN_PATHS:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")

    for relative_path in module.CONTAINED_PACK_API_ALLOWED_FILES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")

    for relative_path in SUPPORT_COPY_PATHS:
        source = ROOT / relative_path
        target = repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for relative_path in SUPPORT_PACKAGE_INITS:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "guard@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Guard Tester"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)


def test_single_semantic_owner_guard_matches_current_repo() -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")

    assert module.evaluate(ROOT) == []


def test_single_semantic_owner_guard_scopes_core_runtime_files_for_hardcode_scan() -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")

    assert module._is_hardcode_scope_file("truffles-api/app/core/turn_executor.py")
    assert module._is_hardcode_scope_file("truffles-api/app/core/consultant_runtime.py")
    assert not module._is_hardcode_scope_file("truffles-api/tests/test_demo_salon_eval.py")


def test_single_semantic_owner_guard_flags_raw_service_fallback(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    (repo / "truffles-api" / "app" / "services").mkdir(parents=True)
    (repo / "truffles-api" / "app" / "routers" / "webhook").mkdir(parents=True)
    (repo / "truffles-api" / "app" / "core").mkdir(parents=True)

    _seed_guard_repo(repo, module)

    (repo / "truffles-api" / "app" / "services" / "intent_service.py").write_text(
        "from app.services.pack_runtime_service import get_pack_service_hint\n"
        "def x(message, normalized_client_slug):\n"
        "    return get_pack_service_hint(message, client_slug=normalized_client_slug)\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "services" / "pack_runtime_service.py").write_text(
        "def y(message_text, client_slug):\n"
        "    semantic_query = get_pack_service_hint(message_text, client_slug=client_slug)\n"
        "    if not resolved_service and message_text:\n"
        "        pass\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "routers" / "webhook" / "info.py").write_text(
        "def z():\n"
        "    get_pack_price_reply('x')\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "routers" / "webhook" / "booking.py").write_text(
        "def z():\n"
        "    return None\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "routers" / "webhook" / "policy.py").write_text(
        "def z(message, client_slug):\n"
        "    price_reply = get_pack_price_reply(message, client_slug=client_slug)\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py").write_text(
        "def _is_timeout_pending_time_slot_question():\n"
        "    return resolve_master_intent('x')\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "app" / "core" / "turn_executor.py").write_text(
        "synthetic_policy_decision = True\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert violations
    assert any("intent_service.py" in item for item in violations)
    assert any("pack_runtime_service.py" in item for item in violations)
    assert any("info.py" in item for item in violations)
    assert any("booking.py" in item for item in violations)
    assert any("policy.py" in item for item in violations)
    assert any("decision.py" in item for item in violations)
    assert any("synthetic_policy_decision" in item for item in violations)


def test_single_semantic_owner_guard_flags_contained_pack_api_escape(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    app_root = repo / "truffles-api" / "app"
    (app_root / "services").mkdir(parents=True)
    (app_root / "routers" / "webhook").mkdir(parents=True)

    _seed_guard_repo(repo, module)

    (app_root / "routers" / "webhook" / "policy.py").write_text(
        "from app.services.pack_runtime_service import get_pack_decision\n\n"
        "def leak(text):\n"
        "    return get_pack_decision(text)\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("contained pack API token" in item for item in violations)


def test_single_semantic_owner_guard_flags_compat_import_escape(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    app_root = repo / "truffles-api" / "app"
    (app_root / "services").mkdir(parents=True)
    (app_root / "routers" / "webhook").mkdir(parents=True)

    _seed_guard_repo(repo, module)

    (app_root / "routers" / "webhook" / "policy.py").write_text(
        "from app.services.pack_runtime_compat import get_pack_decision\n\n"
        "def leak(text):\n"
        "    return text\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("compatibility-only pack runtime helpers" in item for item in violations)


def test_single_semantic_owner_guard_flags_unknown_canonical_subscript_writer(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)

    target = repo / "truffles-api" / "app" / "routers" / "webhook" / "info_compat.py"
    target.write_text(
        "def leak(meta):\n"
        "    meta['action'] = 'collect'\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("unexpected canonical write signature" in item and "field=action" in item for item in violations)


def test_single_semantic_owner_guard_flags_unknown_canonical_update_writer(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)

    target = repo / "truffles-api" / "app" / "routers" / "webhook" / "response_compat.py"
    target.write_text(
        "def leak(meta):\n"
        "    meta.update({'expected_reply_type': 'time'})\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any(
        "unexpected canonical write signature" in item and "kind=call.update" in item for item in violations
    )


def test_single_semantic_owner_guard_flags_unknown_canonical_model_copy_writer(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)

    target = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision_compat.py"
    target.write_text(
        "def leak(payload):\n"
        "    return payload.model_copy(update={'semantic_contract': {'goal': 'booking'}})\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any(
        "unexpected canonical write signature" in item and "kind=call.model_copy_update" in item
        for item in violations
    )


def test_single_semantic_owner_guard_flags_phrase_branching_in_core_diff(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)
    _init_git_repo(repo)

    target = repo / "truffles-api" / "app" / "core" / "turn_executor.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "def leak(message_text):\n"
        "    if \"маникюр\" in message_text:\n"
        "        return 'collect'\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, base_ref="HEAD")
    assert any("forbidden semantic hardcode diff line" in item and "turn_executor.py" in item for item in violations)


def test_single_semantic_owner_guard_allows_marked_technical_diff(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)
    _init_git_repo(repo)

    target = repo / "truffles-api" / "app" / "core" / "turn_executor.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "def leak(message_text):\n"
        "    if \"маникюр\" in message_text:  # hardcode-gate: allow\n"
        "        return 'collect'\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, base_ref="HEAD")
    assert not any("forbidden semantic hardcode diff line" in item for item in violations)


def test_single_semantic_owner_guard_runs_semantic_contract_sync_subguard(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)

    prompt_path = repo / "prompts" / "llm_policy_core.md"
    prompt_path.write_text(
        prompt_path.read_text(encoding="utf-8").replace(
            "{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}",
            "",
            1,
        ),
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any(
        "semantic_contract_sync_guard.py" in item and "generated contract marker exactly once" in item
        for item in violations
    )


def test_single_semantic_owner_guard_runs_boundary_rewrite_subguard(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    _seed_guard_repo(repo, module)

    runtime_path = repo / "truffles-api" / "app" / "core" / "consultant_runtime.py"
    runtime_path.write_text(
        runtime_path.read_text(encoding="utf-8").replace(
            'decision_meta["boundary_normalization_used"] = bool(',
            'decision_meta["boundary_normalization_used_missing"] = bool(',
            1,
        ),
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any(
        "boundary_rewrite_guard.py" in item and "missing required boundary rewrite snippet" in item
        for item in violations
    )
