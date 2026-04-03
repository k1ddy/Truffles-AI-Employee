from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_semantic_owner_guard_matches_current_repo() -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")

    assert module.evaluate(ROOT) == []


def test_single_semantic_owner_guard_flags_raw_service_fallback(tmp_path: Path) -> None:
    module = load_module("single_semantic_owner_guard", SCRIPTS / "single_semantic_owner_guard.py")
    repo = tmp_path / "repo"
    (repo / "truffles-api" / "app" / "services").mkdir(parents=True)
    (repo / "truffles-api" / "app" / "routers" / "webhook").mkdir(parents=True)
    (repo / "truffles-api" / "app" / "core").mkdir(parents=True)

    for relative_path in module.FILE_RULES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

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

    for relative_path in module.FILE_RULES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    for relative_path in module.CONTAINED_PACK_API_ALLOWED_FILES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

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

    for relative_path in module.FILE_RULES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    for relative_path in module.CONTAINED_PACK_API_ALLOWED_FILES:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    (app_root / "routers" / "webhook" / "policy.py").write_text(
        "from app.services.pack_runtime_compat import get_pack_decision\n\n"
        "def leak(text):\n"
        "    return text\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("compatibility-only pack runtime helpers" in item for item in violations)
