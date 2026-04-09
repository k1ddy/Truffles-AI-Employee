from __future__ import annotations

import ast
import importlib.util
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = _module_tree(path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"class {class_name} not found in {path}")


def _function_def(class_node: ast.ClassDef, function_name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    raise AssertionError(f"function {function_name} not found in class {class_node.name}")


def _class_field_names(path: Path, class_name: str) -> list[str]:
    class_node = _class_def(path, class_name)
    fields: list[str] = []
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fields.append(node.target.id)
    return fields


def _decision_attr_reads(function_node: ast.FunctionDef) -> set[str]:
    attrs: set[str] = set()
    for node in ast.walk(function_node):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "decision"
        ):
            attrs.add(node.attr)
    return attrs


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo, "HEAD"


def write_config(repo: Path) -> dict:
    config = {
        "sunset_files": [
            {
                "path": "truffles-api/app/routers/webhook/decision.py",
                "active_waiver": None,
            }
        ]
    }
    path = repo / "docs" / "LEGACY_SUNSET.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def commit_base(repo: Path, file_text: str, relative_path: str = "truffles-api/app/routers/webhook/decision.py") -> str:
    target_path = repo / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(file_text, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_legacy_freeze_guard_blocks_executable_additions(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["path"] = "truffles-api/app/routers/webhook/session_memory.py"
    base = commit_base(
        repo,
        "def keep():\n    return 1\n",
        relative_path="truffles-api/app/routers/webhook/session_memory.py",
    )
    target_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "session_memory.py"
    target_path.write_text("def keep():\n    return 1\n\nvalue = 2\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "session_memory.py" in violations[0]


def test_legacy_freeze_guard_allows_comment_only_additions(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["path"] = "truffles-api/app/routers/webhook/session_memory.py"
    base = commit_base(
        repo,
        "def keep():\n    return 1\n",
        relative_path="truffles-api/app/routers/webhook/session_memory.py",
    )
    target_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "session_memory.py"
    target_path.write_text("def keep():\n    return 1\n\n# comment only\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_legacy_freeze_guard_allows_only_scoped_waiver_lines(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["path"] = "truffles-api/app/routers/webhook/session_memory.py"
    config["sunset_files"][0]["active_waiver"] = {
        "allowed_executable_lines": [
            "value = 2",
        ]
    }
    base = commit_base(
        repo,
        "def keep():\n    return 1\n",
        relative_path="truffles-api/app/routers/webhook/session_memory.py",
    )
    target_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "session_memory.py"
    target_path.write_text("def keep():\n    return 1\n\nvalue = 2\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_legacy_freeze_guard_blocks_non_waived_lines_even_with_scoped_waiver(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["path"] = "truffles-api/app/routers/webhook/session_memory.py"
    config["sunset_files"][0]["active_waiver"] = {
        "allowed_executable_lines": [
            "value = 2",
        ]
    }
    base = commit_base(
        repo,
        "def keep():\n    return 1\n",
        relative_path="truffles-api/app/routers/webhook/session_memory.py",
    )
    target_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "session_memory.py"
    target_path.write_text(
        "def keep():\n    return 1\n\nvalue = 2\n\nanother_value = 3\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "another_value = 3" in violations[0]


def test_legacy_freeze_guard_skips_router_files_moved_under_single_owner_guard(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["path"] = "truffles-api/app/routers/webhook/decision.py"
    base = commit_base(repo, "def keep():\n    return 1\n")
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.write_text("def keep():\n    return 1\n\nvalue = 2\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_webhook_legacy_adapter_uses_explicit_export_allowlist() -> None:
    legacy_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "_legacy.py"
    text = legacy_path.read_text(encoding="utf-8")

    assert "_DECISION_EXPORTS = (" in text
    assert "_decision.__dict__.items()" not in text
    assert "globals().update(_SHARED_EXPORTS)" in text


def test_legacy_root_webhook_removed_from_app_runtime() -> None:
    removed_path = ROOT / "truffles-api" / "app" / "webhook.py"
    shadow_path = ROOT / "truffles-api" / "tests" / "support_legacy_webhook_shadow.py"

    assert not removed_path.exists()
    assert shadow_path.exists()


def test_booking_prompt_owner_removed_from_app_core() -> None:
    removed_path = ROOT / "truffles-api" / "app" / "core" / "booking_prompt_owner.py"
    shadow_path = ROOT / "truffles-api" / "tests" / "support_booking_prompt_owner_shadow.py"

    assert not removed_path.exists()
    assert shadow_path.exists()


def test_reasoning_core_has_no_app_runtime_importers() -> None:
    app_root = ROOT / "truffles-api" / "app"
    removed_path = app_root / "services" / "reasoning_core.py"
    importers: list[str] = []

    assert not removed_path.exists()

    for path in app_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.services.reasoning_core":
                        importers.append(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app.services.reasoning_core":
                    importers.append(str(path.relative_to(ROOT)))
                elif module == "app.services":
                    if any(alias.name == "reasoning_core" for alias in node.names):
                        importers.append(str(path.relative_to(ROOT)))

    assert importers == []


def test_reasoning_core_shadow_support_has_no_direct_decision_router_import() -> None:
    reasoning_core_path = ROOT / "truffles-api" / "tests" / "support_reasoning_core_shadow.py"
    tree = ast.parse(reasoning_core_path.read_text(encoding="utf-8"), filename=str(reasoning_core_path))

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.routers.webhook.decision":
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "app.routers.webhook" and any(alias.name == "decision" for alias in node.names):
                violations.append(f"{module}:decision")
            elif module == "app.routers.webhook.decision":
                violations.append(module)

    assert violations == []


def test_app_runtime_has_no_non_service_get_pack_decision_callsites() -> None:
    app_root = ROOT / "truffles-api" / "app"
    allowed_paths = {
        "truffles-api/app/services/demo_salon_knowledge.py",
        "truffles-api/app/services/pack_runtime_default.py",
        "truffles-api/app/services/pack_runtime_neutral_adapter.py",
        "truffles-api/app/services/pack_runtime_service.py",
    }
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        relative_path = str(path.relative_to(ROOT))
        if relative_path in allowed_paths:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "get_pack_decision":
                violations.append(f"{relative_path}:{node.lineno}")
            elif isinstance(func, ast.Attribute) and func.attr == "get_pack_decision":
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []


def test_app_runtime_has_no_non_service_get_pack_service_decision_callsites() -> None:
    app_root = ROOT / "truffles-api" / "app"
    allowed_paths = {
        "truffles-api/app/services/demo_salon_knowledge.py",
        "truffles-api/app/services/pack_runtime_default.py",
        "truffles-api/app/services/pack_runtime_neutral_adapter.py",
        "truffles-api/app/services/pack_runtime_service.py",
    }
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        relative_path = str(path.relative_to(ROOT))
        if relative_path in allowed_paths:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "get_pack_service_decision":
                violations.append(f"{relative_path}:{node.lineno}")
            elif isinstance(func, ast.Attribute) and func.attr == "get_pack_service_decision":
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []


def test_app_runtime_has_no_synthetic_policy_decision_marker() -> None:
    app_root = ROOT / "truffles-api" / "app"
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "synthetic_policy_decision" in line:
                violations.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert violations == []


def test_app_runtime_has_no_removed_non_owner_surface_snippets() -> None:
    app_root = ROOT / "truffles-api" / "app"
    forbidden_snippets = (
        "build_controlled_degrade(",
        "build_preflight_reject(",
        "_semantic_contract_from_frame(",
        "resolve_timeout_owner_boundary(",
        "owner_replacement_cutover",
    )
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(snippet in line for snippet in forbidden_snippets):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert violations == []


def test_legacy_response_policy_have_no_raw_service_resolution_paths() -> None:
    response_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "response.py"
    ).read_text(encoding="utf-8")
    decision_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    ).read_text(encoding="utf-8")
    guards_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "guards.py"
    ).read_text(encoding="utf-8")
    dedup_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "dedup.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    policy_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    ).read_text(encoding="utf-8")
    booking_signal_runtime_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking_signal_runtime.py"
    ).read_text(encoding="utf-8")

    assert "semantic_service_match(" not in response_text
    assert "rewrite_for_service_match(" not in response_text
    assert "get_pack_service_decision(" not in response_text
    assert "_is_booking_request(" not in response_text
    assert "_is_booking_request(" not in decision_text
    assert "get_pack_service_hint(" not in decision_text
    assert "_evaluate_booking_signal(" not in guards_text
    assert "_evaluate_booking_signal(" not in dedup_text
    assert '\"service_matcher\":' not in policy_text
    assert ".get(\"service_matcher\")" not in booking_text
    assert "_extract_service_hint(" not in booking_text
    assert ".get(\"service_matcher\")" not in info_text
    assert "get_pack_service_hint(" not in info_text
    assert "_match_service(" not in info_text
    assert "_validate_service_slot(" not in info_text
    assert "def _extract_service_hint(" not in booking_signal_runtime_text
    assert "phrase_match_intent(" not in response_text


def test_decision_runtime_has_no_raw_info_interrupt_or_verification_fallbacks() -> None:
    decision_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    policy_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    ).read_text(encoding="utf-8")
    interrupt_text = (
        ROOT
        / "truffles-api"
        / "app"
        / "routers"
        / "webhook"
        / "expected_reply_interrupt_runtime.py"
    ).read_text(encoding="utf-8")

    assert "_detect_info_class_intents(" not in decision_text
    assert "fallback_info_intents" not in decision_text
    assert "_looks_like_info_query(" not in decision_text
    assert "_looks_like_services_overview_message(" not in decision_text
    assert "_looks_like_time_only_request(" not in decision_text
    assert "_looks_like_carryover_followup(" not in decision_text
    assert "_looks_like_hours_followup(" not in decision_text
    assert "info_followup_runtime" not in decision_text
    assert "def _preflight_booking_block(" not in decision_text
    assert "def _looks_like_booking_verification_request(" not in decision_text
    assert "def _has_explicit_location_or_hours_request(" not in decision_text
    assert "_detect_info_class_intents(" not in booking_text
    assert "_looks_like_info_query(" not in booking_text
    assert "def _looks_like_booking_reschedule_request(" not in booking_text
    assert "_looks_like_promotions_request(" not in booking_text
    assert "_detect_info_class_intents(" not in policy_text
    assert "def _looks_like_policy_topic(" not in policy_text
    assert "def _looks_like_promotions_request(" not in policy_text
    assert "_detect_info_class_intents(" not in interrupt_text
    assert "_looks_like_info_query(" not in interrupt_text
    assert "def _looks_like_booking_verification_request(" not in interrupt_text
    assert "def _has_explicit_location_or_hours_request(" not in interrupt_text
    assert "_has_price_signal(" not in interrupt_text
    assert "_has_duration_signal(" not in interrupt_text
    assert "_validate_service_slot(" not in interrupt_text
    assert "phrase_match_intent(" not in info_text
    assert "semantic_question_type(" not in info_text
    assert "from ._legacy import" not in info_text
    assert "_looks_like_carryover_followup(" not in info_text
    assert "_looks_like_hours_followup(" not in info_text
    assert "info_followup_runtime" not in info_text
    assert "_has_price_signal(normalized_message, message_text)" not in info_text
    assert "_has_duration_signal(normalized_message, message_text)" not in info_text
    assert "_has_parking_signal(" not in info_text
    assert "_has_guest_waiting_signal(" not in info_text
    assert "location_signal = _signal_any_match(" not in info_text
    assert '"reason": "short_noisy_followup"' not in info_text


def test_decision_runtime_has_no_dead_pre_owner_helper_defs() -> None:
    decision_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    ).read_text(encoding="utf-8")

    assert "def _detect_fast_intent(" not in decision_text
    assert "def _detect_intent_signals(" not in decision_text
    assert "def _resolve_action(" not in decision_text
    assert "def _llm_first_firebreak_semantic_reasons(" not in decision_text
    assert "def _run_class_router_stage(" not in decision_text
    assert "def _extract_pack_index_meta(" not in decision_text
    assert "def _extract_compiled_pack_meta(" not in decision_text
    assert "def _should_use_expected_reply_collect_fast_path(" not in decision_text
    assert "def _build_expected_reply_collect_fast_policy_result(" not in decision_text
    assert "def _is_timeout_pending_time_slot_question(" not in decision_text
    assert "def _is_timeout_master_info_interrupt_candidate(" not in decision_text
    assert "def _is_timeout_active_time_specialist_interrupt_candidate(" not in decision_text
    assert "resolve_master_intent(" not in decision_text
    assert "def _looks_like_promo_code_request(" not in decision_text
    assert "def _format_discounts_reply_for_message(" not in decision_text
    assert "def _build_router_state(" not in decision_text
    assert "def _controller_meta_updates_from_router_state(" not in decision_text
    assert "route_dialogue_controller(" not in decision_text
    assert "get_demo_salon_decision =" not in decision_text
    assert "get_demo_salon_service_decision =" not in decision_text
    assert "get_demo_salon_price_item =" not in decision_text

    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    assert "def _handle_offline_info_class(" not in info_text
    assert "def _handle_info_flow(" not in info_text

    response_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "response.py"
    ).read_text(encoding="utf-8")
    assert "def _handle_ai_response_action(" not in response_text
    assert 'router_intents = class_router_result.get("intents")' not in response_text
    assert 'if out_of_domain_signal and not expected_reply_shortcircuit:' not in response_text
    assert 'in_signals = class_router_result.get("in_signals") or []' not in response_text
    assert 'anchors_in_hits = int(class_router_result.get("anchors_in_hits") or 0)' not in response_text
    assert '"decision": "domain_anchor"' not in response_text
    assert '"decision": "service_semantic_guard"' not in response_text
    assert '"decision": "no_response_guard"' not in response_text
    assert '"decision": "router_low_confidence"' not in response_text


def test_live_booking_consumers_have_no_raw_booking_request_callsites() -> None:
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    booking_signal_runtime_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking_signal_runtime.py"
    ).read_text(encoding="utf-8")
    interrupt_text = (
        ROOT
        / "truffles-api"
        / "app"
        / "routers"
        / "webhook"
        / "expected_reply_interrupt_runtime.py"
    ).read_text(encoding="utf-8")

    assert "_is_booking_request(" not in booking_text
    assert "_is_booking_request(" not in interrupt_text
    assert "def _is_booking_request(" not in booking_signal_runtime_text
    assert "def _evaluate_booking_signal(" not in booking_signal_runtime_text
    assert "def _has_booking_signal(" not in booking_signal_runtime_text
    assert "_detect_info_class_intents(" not in booking_signal_runtime_text
    assert "semantic_service_match(" not in booking_signal_runtime_text
    assert "get_pack_service_hint(" not in booking_signal_runtime_text
    assert "classify_domain_with_scores(" not in booking_signal_runtime_text
    assert "get_pack_service_hint(" not in booking_text


def test_policy_router_has_no_direct_decision_router_import() -> None:
    policy_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    tree = ast.parse(policy_path.read_text(encoding="utf-8"), filename=str(policy_path))

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.routers.webhook.decision":
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "app.routers.webhook" and any(alias.name == "decision" for alias in node.names):
                violations.append(f"{module}:decision")
            elif module == "app.routers.webhook.decision":
                violations.append(module)

    assert violations == []


def test_intent_service_has_no_pack_service_fallback_in_policy_core_context_hint() -> None:
    intent_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "def _policy_core_context_service_hint(" in intent_text
    assert "from app.services.pack_runtime_service import get_pack_service_hint" not in intent_text
    assert "return get_pack_service_hint(message, client_slug=normalized_client_slug)" not in intent_text


def test_pack_runtime_and_info_paths_require_explicit_service_grounding() -> None:
    pack_runtime_text = (
        ROOT / "truffles-api" / "app" / "services" / "pack_runtime_service.py"
    ).read_text(encoding="utf-8")
    demo_knowledge_text = (
        ROOT / "truffles-api" / "app" / "services" / "demo_salon_knowledge.py"
    ).read_text(encoding="utf-8")
    demo_compat_text = (
        ROOT / "truffles-api" / "app" / "services" / "demo_salon_knowledge_compat.py"
    ).read_text(encoding="utf-8")
    pack_runtime_compat_text = (
        ROOT / "truffles-api" / "app" / "services" / "pack_runtime_compat.py"
    ).read_text(encoding="utf-8")
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    policy_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    ).read_text(encoding="utf-8")
    tool_registry_text = (
        ROOT / "truffles-api" / "app" / "services" / "tool_registry_service.py"
    ).read_text(encoding="utf-8")

    assert "semantic_query = get_pack_service_hint(message_text, client_slug=client_slug)" not in pack_runtime_text
    assert "if not resolved_service and message_text:" not in pack_runtime_text
    assert "_pack_query_service_context(\n            message_text," not in pack_runtime_text
    assert "def get_pack_decision(" not in pack_runtime_text
    assert "def get_pack_service_decision(" not in pack_runtime_text
    assert "def get_pack_service_hint(" not in pack_runtime_text
    assert "def get_pack_price_item(" not in pack_runtime_text
    assert "def get_pack_price_reply(" not in pack_runtime_text
    assert "def resolve_master_intent(" not in pack_runtime_text
    assert "def semantic_service_match(" not in pack_runtime_text
    assert "def _compat_service_semantics(" not in pack_runtime_text
    assert "def _compat_service_hint(" not in pack_runtime_text
    assert "def _compat_price_item_lookup(" not in pack_runtime_text
    assert "def _compat_price_reply_builder(" not in pack_runtime_text
    assert "def _compat_truth_gate_builder(" not in pack_runtime_text
    assert "def _compat_service_decision_builder(" not in pack_runtime_text
    assert "def _compat_master_resolver(" not in pack_runtime_text
    assert "def _resolve_compat_master_service_query(" not in pack_runtime_text
    assert '"compat_hint"' not in pack_runtime_text
    assert "get_pack_decision" in pack_runtime_compat_text
    assert "resolve_master_intent" in pack_runtime_compat_text
    assert "def _compat_demo_service_decision(" not in demo_knowledge_text
    assert "def _compat_demo_decision(" not in demo_knowledge_text
    assert "def _compat_demo_price_reply(" not in demo_knowledge_text
    assert "def _compat_demo_price_item(" not in demo_knowledge_text
    assert "def _compat_demo_service_hint(" not in demo_knowledge_text
    assert "_build_demo_truth_decision as get_demo_salon_decision" in demo_compat_text
    assert "_resolve_demo_price_item as get_demo_salon_price_item" in demo_compat_text
    assert "_build_demo_price_reply as get_demo_salon_price_reply" in demo_compat_text
    assert "_build_demo_service_decision as get_demo_salon_service_decision" in demo_compat_text
    assert "_resolve_demo_service_hint as get_demo_salon_service_hint" in demo_compat_text
    assert "get_pack_price_reply(" not in info_text
    assert "get_pack_price_item(" not in info_text
    assert "message=message_text if not resolved_service_query else None" not in info_text
    assert 'base_info_override = bool(info_signals.get("parking") or info_signals.get("guest"))' not in info_text
    assert 'include_base_bundle = bool({"location"} & info_class_intents_for_reply)' not in info_text
    assert 'for key in ("parking", "guest", "location")' not in info_text
    assert "build_master_reply_from_pack(\n            client_slug=client_slug,\n            message_text=None," in info_text
    assert "def _detect_info_class_intents(" not in info_text
    assert "def _looks_like_info_query(" not in info_text
    assert "get_pack_price_item(" not in booking_text
    assert "resolve_explicit_master_intent(\n            client_slug=client_slug," in booking_text
    assert "price_reply = get_pack_price_reply(message, client_slug=client_slug)" not in policy_text
    assert '"price_item": get_pack_price_item' not in policy_text
    assert ".get_pack_price_item(" not in tool_registry_text
    assert ".get_pack_price_reply(" not in tool_registry_text


def test_policy_runtime_snapshot_owner() -> None:
    policy_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    ).read_text(encoding="utf-8")
    snapshot_text = (
        ROOT / "truffles-api" / "app" / "services" / "policy_snapshot_service.py"
    ).read_text(encoding="utf-8")

    for removed_def in (
        "def _resolve_runtime_policy_overrides(",
        "def _resolve_registry_policy_overrides(",
        "def _apply_runtime_policy_overrides(",
        "def _apply_registry_policy_overrides(",
    ):
        assert removed_def not in policy_text

    assert "def build_policy_pack_snapshot(" in snapshot_text
    assert "def build_routing_policy_snapshot(" in snapshot_text


def test_reasoning_core_routing_reads_compiled_policy_snapshot() -> None:
    reasoning_core_text = (
        ROOT / "truffles-api" / "tests" / "support_reasoning_core_shadow.py"
    ).read_text(encoding="utf-8")

    assert "from app.routers.webhook.policy import _get_routing_policy" not in reasoning_core_text
    assert "from app.services.policy_snapshot_service import build_routing_policy_snapshot" in reasoning_core_text


def test_tool_registry_snapshot_owner() -> None:
    snapshot_text = (
        ROOT / "truffles-api" / "app" / "services" / "tool_registry_snapshot_service.py"
    ).read_text(encoding="utf-8")
    tool_registry_text = (
        ROOT / "truffles-api" / "app" / "services" / "tool_registry_service.py"
    ).read_text(encoding="utf-8")
    tool_certification_text = (
        ROOT / "truffles-api" / "app" / "services" / "tool_certification_service.py"
    ).read_text(encoding="utf-8")

    assert "class ToolRegistrySnapshotV1" in snapshot_text
    assert "def build_tool_registry_snapshot(" in snapshot_text
    assert "def resolve_tool_registry_entry(" in snapshot_text
    assert "def resolve_policy_info_tool_action(" in snapshot_text
    assert "from app.services.tool_registry_snapshot_service import" in tool_registry_text
    assert "from app.services.tool_registry_snapshot_service import" in tool_certification_text


def test_policy_tool_projector_binding_rules_use_snapshot_owner() -> None:
    projector_text = (
        ROOT / "truffles-api" / "app" / "core" / "policy_tool_projector.py"
    ).read_text(encoding="utf-8")

    for removed_symbol in (
        "_SERVICE_QUERY_TOOL_ACTIONS =",
        "_SPECIALIST_TOOL_ACTIONS =",
        "_BOOKING_REF_TOOL_ACTIONS =",
        "_BOOKING_CUSTOMER_TOOL_ACTIONS =",
        "_POLICY_INFO_TOOL_ACTION_MAP =",
    ):
        assert removed_symbol not in projector_text

    assert "resolve_tool_registry_entry" in projector_text
    assert "resolve_policy_info_tool_action" in projector_text


def test_policy_core_context_snapshot_owner() -> None:
    snapshot_text = (
        ROOT / "truffles-api" / "app" / "services" / "policy_context_snapshot_service.py"
    ).read_text(encoding="utf-8")
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "class PolicyCoreContextSnapshotV1" in snapshot_text
    assert "def build_policy_core_context_snapshot(" in snapshot_text
    assert "_DEFAULT_INFO_REFS_V1" in snapshot_text
    assert "_GENERIC_TOOL_ACTIONS_V1" in snapshot_text
    assert "from app.services.policy_context_snapshot_service import build_policy_core_context_snapshot" in intent_service_text


def test_policy_core_allowed_context_uses_compiled_context_snapshot() -> None:
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    for removed_symbol in (
        "def _build_policy_core_allowed_context(",
        "def _build_policy_core_policy_cards(",
        "def _build_policy_core_capability_cards(",
        "def _load_policy_core_consult_catalog(",
        "_POLICY_CORE_DEFAULT_INFO_REFS =",
        "_POLICY_CORE_GENERIC_TOOL_ACTIONS =",
    ):
        assert removed_symbol not in intent_service_text


def test_policy_vocabulary_snapshot_owner() -> None:
    snapshot_text = (
        ROOT / "truffles-api" / "app" / "services" / "policy_vocabulary_snapshot_service.py"
    ).read_text(encoding="utf-8")
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "class PolicyCoreVocabularySnapshotV1" in snapshot_text
    assert "def build_policy_core_vocabulary_snapshot(" in snapshot_text
    assert "def build_policy_core_response_format(" in snapshot_text
    assert "def policy_core_semantic_contract_allowlists(" in snapshot_text
    assert "from app.services.policy_vocabulary_snapshot_service import build_policy_core_response_format" in intent_service_text
    assert "from app.services.policy_vocabulary_snapshot_service import (" in intent_service_text


def test_policy_core_response_format_uses_snapshot_owner() -> None:
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "def _build_policy_core_response_format(" not in intent_service_text
    assert "policy_core_semantic_contract_allowlists().items()" in intent_service_text


def test_policy_prompt_snapshot_owner() -> None:
    snapshot_text = (
        ROOT / "truffles-api" / "app" / "services" / "policy_prompt_snapshot_service.py"
    ).read_text(encoding="utf-8")
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "class PolicyCorePromptSnapshotV1" in snapshot_text
    assert "def load_policy_core_prompt_snapshot(" in snapshot_text
    assert "_POLICY_CORE_PROMPT_PATH" in snapshot_text
    assert "_POLICY_CORE_PROMPT_FALLBACK" in snapshot_text
    assert "from app.services.policy_prompt_snapshot_service import load_policy_core_prompt_snapshot" in intent_service_text


def test_policy_core_prompt_load_uses_snapshot_owner() -> None:
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "POLICY_CORE_PROMPT_FALLBACK =" not in intent_service_text
    assert "_POLICY_CORE_PROMPT_CACHE" not in intent_service_text
    assert "POLICY_CORE_PROMPT_PATH =" not in intent_service_text


def test_controller_plan_prompt_snapshot_owner() -> None:
    snapshot_text = (
        ROOT
        / "truffles-api"
        / "app"
        / "services"
        / "controller_plan_prompt_snapshot_service.py"
    ).read_text(encoding="utf-8")
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "class ControllerPromptSnapshotV1" in snapshot_text
    assert "class PlanPromptSnapshotV1" in snapshot_text
    assert "def load_controller_prompt_snapshot(" in snapshot_text
    assert "def load_plan_prompt_snapshot(" in snapshot_text
    assert "from app.services.controller_plan_prompt_snapshot_service import (" in intent_service_text
    assert "from app.services.controller_plan_prompt_snapshot_service import load_plan_prompt_snapshot" in intent_service_text


def test_controller_plan_prompt_loaders_use_snapshot_owner() -> None:
    intent_service_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")

    assert "CONTROLLER_PROMPT_FALLBACK =" not in intent_service_text
    assert "PLAN_PROMPT_FALLBACK =" not in intent_service_text
    assert "CONTROLLER_PROMPT_PATH =" not in intent_service_text
    assert "PLAN_PROMPT_PATH =" not in intent_service_text
    assert "_CONTROLLER_PROMPT_CACHE" not in intent_service_text
    assert "_PLAN_PROMPT_CACHE" not in intent_service_text

def test_capability_registry_snapshot_owner() -> None:
    snapshot_text = (
        ROOT
        / "truffles-api"
        / "app"
        / "services"
        / "capability_registry_snapshot_service.py"
    ).read_text(encoding="utf-8")
    manifest_text = (
        ROOT / "truffles-api" / "app" / "services" / "capability_manifest_service.py"
    ).read_text(encoding="utf-8")

    assert "class CapabilityRegistrySnapshotV1" in snapshot_text
    assert "class ToolProtocolPolicySnapshotV1" in snapshot_text
    assert "class FactScopePolicySnapshotV1" in snapshot_text
    assert "class HandoffPolicySnapshotV1" in snapshot_text
    assert "def build_capability_registry_snapshot(" in snapshot_text
    assert "from app.services.capability_registry_snapshot_service import (" in manifest_text



def test_capability_manifest_service_uses_snapshot_owner() -> None:
    manifest_text = (
        ROOT / "truffles-api" / "app" / "services" / "capability_manifest_service.py"
    ).read_text(encoding="utf-8")

    assert "get_runtime_capabilities" not in manifest_text
    assert "TOOL_POLICY_ENFORCEMENT" not in manifest_text
    assert "TOOL_PROTOCOL_DENY_BY_DEFAULT" not in manifest_text
    assert "resolve_tool_protocol_snapshot(" in manifest_text
    assert "resolve_fact_scope_snapshot(" in manifest_text
    assert "resolve_handoff_policy_snapshot(" in manifest_text


def test_workstream7_phase1_snapshot_owners_exist() -> None:
    services_dir = ROOT / "truffles-api" / "app" / "services"
    required_symbols = {
        "policy_snapshot_service.py": ("RoutingPolicySnapshotV1", "PolicyPackSnapshotV1"),
        "tool_registry_snapshot_service.py": ("ToolRegistrySnapshotV1",),
        "policy_context_snapshot_service.py": ("PolicyCoreContextSnapshotV1",),
        "capability_registry_snapshot_service.py": ("CapabilityRegistrySnapshotV1",),
    }

    for relative_name, symbols in required_symbols.items():
        text = (services_dir / relative_name).read_text(encoding="utf-8")
        for symbol in symbols:
            assert f"class {symbol}" in text
        assert "schema_version" in text



def test_workstream7_runtime_hotspots_use_governed_snapshot_owners() -> None:
    policy_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "policy.py"
    ).read_text(encoding="utf-8")
    projector_text = (
        ROOT / "truffles-api" / "app" / "core" / "policy_tool_projector.py"
    ).read_text(encoding="utf-8")
    intent_text = (
        ROOT / "truffles-api" / "app" / "services" / "intent_service.py"
    ).read_text(encoding="utf-8")
    manifest_text = (
        ROOT / "truffles-api" / "app" / "services" / "capability_manifest_service.py"
    ).read_text(encoding="utf-8")

    assert "from app.services.policy_snapshot_service import (" in policy_text
    assert "from app.services.tool_registry_snapshot_service import (" in projector_text
    assert "from app.services.policy_context_snapshot_service import build_policy_core_context_snapshot" in intent_text
    assert "from app.services.policy_vocabulary_snapshot_service import build_policy_core_response_format" in intent_text
    assert "from app.services.policy_vocabulary_snapshot_service import (" in intent_text
    assert "from app.services.policy_prompt_snapshot_service import load_policy_core_prompt_snapshot" in intent_text
    assert "from app.services.controller_plan_prompt_snapshot_service import (" in intent_text
    assert "from app.services.controller_plan_prompt_snapshot_service import load_plan_prompt_snapshot" in intent_text
    assert "from app.services.capability_registry_snapshot_service import (" in manifest_text

    for removed_symbol in (
        "def _build_policy_core_allowed_context(",
        "def _build_policy_core_response_format(",
        "POLICY_CORE_PROMPT_FALLBACK =",
        "CONTROLLER_PROMPT_FALLBACK =",
        "PLAN_PROMPT_FALLBACK =",
    ):
        assert removed_symbol not in intent_text

    assert "_SERVICE_QUERY_TOOL_ACTIONS =" not in projector_text
    assert "_POLICY_INFO_TOOL_ACTION_MAP =" not in projector_text
    assert "get_runtime_capabilities" not in manifest_text



def test_response_retry_sidecar_cluster_uses_narrow_runtime_primitives() -> None:
    response_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "response.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    context_manager_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "context_manager.py"
    ).read_text(encoding="utf-8")

    for removed_symbol in (
        "decision_router.QUIET_HOURS_NOTICE_KEY",
        "decision_router.QUIET_HOURS_NOTICE_TTL_MINUTES",
        "decision_router.EVENING_GREETING_KEY",
        "decision_router.EVENING_GREETING_TTL_HOURS",
        "decision_router._append_followup(",
        "decision_router._combine_sidecar(",
        "decision_router.MSG_STYLE_REFERENCE_NEED_MEDIA",
        "decision_router.MSG_PENDING_LOW_CONFIDENCE",
        "decision_router.should_offer_low_confidence_retry(",
        "decision_router.LOW_CONFIDENCE_MAX_RETRIES",
        "decision_router.MSG_LOW_CONFIDENCE_RETRY",
        "decision_router.MSG_HANDOVER_CONFIRM",
    ):
        assert removed_symbol not in response_text

    assert "decision_router._append_followup(" not in context_manager_text
    assert "decision_router._combine_sidecar(" not in booking_text
    assert "decision_router.MSG_STYLE_REFERENCE_NEED_MEDIA" not in booking_text
    assert "decision_router.MSG_ESCALATED" not in booking_text


def test_controller_class_router_cluster_uses_narrow_runtime_owner() -> None:
    decision_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    ).read_text(encoding="utf-8")
    response_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "response.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    class_router_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "class_router_runtime.py"
    ).read_text(encoding="utf-8")

    for removed_symbol in (
        "decision_router._build_controller_meta_output(",
        "decision_router.CONTROLLER_CONFIDENCE_THRESHOLD",
        "decision_router._ensure_controller_output_meta(",
        "decision_router._resolve_controller_signal_class(",
        "decision_router._resolve_class_router_result(",
        "decision_router.DomainIntent.",
        "decision_router.CONSULT_INTERRUPT_INTENTS",
        "decision_router._controller_meta_updates_from_class_router(",
        "decision_router._router_observability_updates_from_class_router(",
    ):
        assert removed_symbol not in response_text
        assert removed_symbol not in booking_text
        assert removed_symbol not in info_text

    for direct_helper in (
        "_build_controller_meta_output(",
        "_ensure_controller_output_meta(",
        "_resolve_class_router_result(",
        "_resolve_controller_signal_class(",
    ):
        assert direct_helper not in response_text
        assert direct_helper not in booking_text
        assert direct_helper not in decision_text
    for direct_helper in (
        "_build_controller_meta_output(",
        "_ensure_controller_output_meta(",
        "_resolve_class_router_result(",
        "_resolve_controller_signal_class(",
    ):
        assert direct_helper not in info_text

    assert 'router_output_class == "out_of_domain"' not in response_text
    assert "controller_service_query" not in response_text
    assert 'slots.get("service_query")' not in response_text
    assert "response_compat" not in response_text
    assert "response_compat" not in booking_text
    assert "response_compat" not in info_text
    assert "response_compat" not in decision_text
    assert "router_service_query" not in info_text
    assert 'slots.get("service_query")' not in info_text
    assert 'info_semantic_lock = guest_policy_lock or info_bundle_lock or controller_low_confidence' not in info_text
    assert 'skip_reason = "controller_low_confidence"' not in info_text
    assert 'result["classes"] = [controller_class]' not in class_router_text
    assert 'result["intents"] = sorted(info_controller_intents)' not in class_router_text
    assert 'controller_used_reason = "deterministic"' not in class_router_text
    assert 'controller_output = {**controller_output, "class": controller_class, "goal": controller_goal}' not in class_router_text


def test_response_decision_helper_residue_uses_narrow_runtime_owners() -> None:
    response_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "response.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")
    context_manager_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "context_manager.py"
    ).read_text(encoding="utf-8")
    guards_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "guards.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in response_text
    for removed_symbol in (
        "decision_router._merge_rag_scores(",
        "decision_router._derive_rag_status(",
        "decision_router._record_knowledge_backlog(",
        "decision_router._is_booking_request(",
        "decision_router._extract_service_hint(",
        "decision_router._looks_like_time_only_request(",
        "decision_router.CONSULT_CONTEXT_TTL_MESSAGES",
        "decision_router.CLARIFY_MAX_ATTEMPTS",
    ):
        assert removed_symbol not in response_text

    for removed_symbol in (
        "decision_router._extract_service_hint(",
        "decision_router._is_booking_request(",
        "decision_router._extract_datetime(",
    ):
        assert removed_symbol not in booking_text

    for removed_symbol in (
        "decision_router._extract_service_hint(",
        "decision_router._extract_datetime(",
        "decision_router._has_explicit_service_signal(",
    ):
        assert removed_symbol not in info_text

    for removed_symbol in (
        "decision_router.CONSULT_CONTEXT_TTL_MESSAGES",
        "decision_router._resolve_backlog_language(",
    ):
        assert removed_symbol not in context_manager_text

    for removed_symbol in (
        "decision_router.CLARIFY_MAX_ATTEMPTS",
        "decision_router._evaluate_booking_signal(",
    ):
        assert removed_symbol not in guards_text


def test_context_and_guard_runtime_clusters_use_narrow_owners() -> None:
    context_manager_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "context_manager.py"
    ).read_text(encoding="utf-8")
    guards_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "guards.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")
    pending_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "pending.py"
    ).read_text(encoding="utf-8")
    package_init_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in context_manager_text
    assert "_decision_runtime(" not in guards_text

    for removed_symbol in (
        "decision_router.SERVICE_CARRYOVER_KEY",
        "decision_router.CONSULT_CONTEXT_KEY",
        "decision_router.EXPECTED_REPLY_TYPE_KEY",
        "decision_router.EXPECTED_REPLY_REASON_KEY",
        "decision_router.CONTEXT_MANAGER_KEY",
        "decision_router.RE_ENTRY_REQUIRED_KEY",
        "decision_router.CLASS_CARRYOVER_KEY",
        "decision_router.CLASS_CARRYOVER_TTL_MESSAGES",
        "decision_router.CLASS_CARRYOVER_CLASSES",
        "decision_router.SERVICE_CARRYOVER_SKIP_INTENTS",
        "decision_router._ensure_question_mark(",
        "decision_router._is_refusal_flag_active(",
        "decision_router.HANDOVER_CONFIRM_WINDOW_MINUTES",
        "decision_router.REENGAGE_CONFIRM_KEY",
        "decision_router.REENGAGE_CONFIRM_WINDOW_MINUTES",
        "decision_router.ASR_CONFIRM_KEY",
        "decision_router.ASR_CONFIRM_WINDOW_MINUTES",
        "decision_router.ASR_INFLIGHT_KEY",
        "decision_router.STYLE_REFERENCE_PENDING_KEY",
        "decision_router.MEMORY_PROFILE_TTL_DAYS",
        "decision_router.MEMORY_PROFILE_KEY",
        "decision_router.MEMORY_PENDING_KEY",
    ):
        assert removed_symbol not in context_manager_text

    for removed_symbol in (
        "decision_router.MULTI_INTENT_LABELS",
        "decision_router.SESSION_TIMEOUT_HOURS",
        "decision_router._coerce_batch_messages(",
        "decision_router.get_mute_settings(",
        "decision_router.MSG_REENGAGE_DECLINED",
        "decision_router.MSG_REENGAGE_CONFIRM",
        "decision_router.MSG_MUTED_TEMP",
        "decision_router.MSG_MUTED_LONG",
        "decision_router.MSG_FACT_GUARD_CLARIFY",
    ):
        assert removed_symbol not in guards_text

    for removed_symbol in (
        "decision_router.SERVICE_HINT_KEY",
        "decision_router.SERVICE_HINT_AT_KEY",
        "decision_router.SERVICE_HINT_WINDOW_MINUTES",
        "decision_router._is_refusal_flag_active(",
        "decision_router.MSG_FACT_GUARD_CLARIFY",
    ):
        assert removed_symbol not in booking_text

    assert "decision_router.MSG_MUTED_TEMP" not in pending_text
    assert "from app.routers.webhook.decision import (\n    EXPECTED_REPLY_REASON_KEY," not in package_init_text


def test_pending_runtime_cluster_uses_narrow_owner() -> None:
    pending_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "pending.py"
    ).read_text(encoding="utf-8")
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in pending_text
    for removed_symbol in (
        "decision_router.MSG_HANDOVER_DECLINED",
        "decision_router.MSG_PENDING_ACK",
        "decision_router.is_handover_status_question(",
        "decision_router.MSG_PENDING_STATUS",
        "decision_router.MSG_PENDING_WAIT",
        "decision_router.MSG_PENDING_SLA_PING",
        "decision_router.PENDING_SLA_PING_MINUTES",
        "decision_router.PENDING_SLA_PING_SENT_KEY",
    ):
        assert removed_symbol not in pending_text

    assert "decision_router.MSG_PENDING_ESCALATION" not in booking_text


def test_info_followup_runtime_cluster_uses_narrow_owner() -> None:
    info_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "info.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in info_text
    for removed_symbol in (
        "decision_router.MSG_ESCALATED",
        "decision_router.MSG_EXPECTED_SERVICE_OFF_TOPIC",
        "decision_router._combine_sidecar(",
        "decision_router._looks_like_hours_followup(",
        "decision_router._looks_like_carryover_followup(",
    ):
        assert removed_symbol not in info_text


def test_booking_runtime_cluster_uses_narrow_owners() -> None:
    booking_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "booking.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in booking_text
    for removed_symbol in (
        "decision_router.MSG_BOOKING_ASK_ALL",
        "decision_router.MSG_BOOKING_CANCELLED",
        "decision_router.MSG_BOOKING_REENGAGE",
        "decision_router.MSG_BOOKING_SLOT_LOCK_STUB",
        "decision_router.NAME_PATTERN",
        "decision_router.NAME_NOISE_TOKENS",
        "decision_router._matches_guest_policy_lexicon(",
        "decision_router._is_booking_cancel(",
        "decision_router._booking_clarify_guard_reason(",
    ):
        assert removed_symbol not in booking_text


def test_operational_helper_runtime_cluster_uses_narrow_owners() -> None:
    dedup_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "dedup.py"
    ).read_text(encoding="utf-8")
    outbox_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "outbox.py"
    ).read_text(encoding="utf-8")
    shield_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "shield.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in dedup_text
    assert "_decision_runtime(" not in outbox_text
    assert "_decision_runtime(" not in shield_text

    for removed_symbol in (
        "decision_router._is_env_enabled(",
        "decision_router._find_message_by_message_id(",
        "decision_router._find_message_by_conversation_created_at(",
        "decision_router._ensure_rag_meta_defaults(",
        "decision_router.MSG_ESCALATED",
    ):
        assert removed_symbol not in dedup_text
        assert removed_symbol not in outbox_text
        assert removed_symbol not in shield_text


def test_media_runtime_cluster_uses_narrow_owner() -> None:
    media_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "media.py"
    ).read_text(encoding="utf-8")

    assert "_decision_runtime(" not in media_text
    for removed_symbol in (
        "decision_router.MEDIA_TYPE_ALIASES",
        "decision_router.MEDIA_MAX_DEFAULT_MB",
        "decision_router.MEDIA_RATE_LIMIT_DEFAULTS",
        "decision_router.MEDIA_STORAGE_DEFAULT_DIR",
        "decision_router.MEDIA_STORAGE_MAX_BYTES",
        "decision_router.AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB",
        "decision_router.ASR_LOW_CONFIDENCE_MIN_CHARS",
        "decision_router.ASR_LOW_CONFIDENCE_MIN_WORDS",
        "decision_router.ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS",
        "decision_router.ASR_LOW_CONFIDENCE_NON_LETTER_RATIO",
        "decision_router.STYLE_REFERENCE_HINT_TOKENS",
        "decision_router.STYLE_REFERENCE_PATTERNS",
        "decision_router.MSG_MEDIA_RATE_LIMIT",
        "decision_router.MSG_MEDIA_UNSUPPORTED",
        "decision_router.MSG_MEDIA_TOO_LARGE",
    ):
        assert removed_symbol not in media_text


def test_webhook_package_init_has_no_eager_decision_import() -> None:
    init_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    tree = ast.parse(init_text, filename=str(init_path))

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "app.routers.webhook.decision"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module != "app.routers.webhook.decision"
            assert not (module == "app.routers.webhook" and any(alias.name == "decision" for alias in node.names))

    assert "def __getattr__(name: str):" in init_text


def test_webhook_package_init_has_no_outbox_export() -> None:
    init_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")

    assert "from app.routers.webhook.outbox import _process_outbox_rows" not in init_text
    assert '"_process_outbox_rows"' not in init_text


def test_app_runtime_has_no_eager_decision_importers() -> None:
    app_root = ROOT / "truffles-api" / "app"
    allowed_importers = {"truffles-api/app/routers/webhook/_legacy.py"}
    importers: set[str] = set()

    for path in app_root.rglob("*.py"):
        if path == app_root / "routers" / "webhook" / "decision.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.routers.webhook.decision":
                        importers.add(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app.routers.webhook.decision":
                    importers.add(str(path.relative_to(ROOT)))
                elif module == "app.routers.webhook" and any(
                    alias.name == "decision" for alias in node.names
                ):
                    importers.add(str(path.relative_to(ROOT)))
                elif node.level == 1 and module == "" and any(
                    alias.name == "decision" for alias in node.names
                ):
                    importers.add(str(path.relative_to(ROOT)))

    assert importers == allowed_importers


def test_app_runtime_has_no_decision_helper_reads() -> None:
    app_root = ROOT / "truffles-api" / "app"
    helper_read_violations: list[str] = []

    for path in app_root.rglob("*.py"):
        if path == app_root / "routers" / "webhook" / "decision.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "decision_router." in text or "_decision_runtime(" in text:
            helper_read_violations.append(str(path.relative_to(ROOT)))

    assert helper_read_violations == []


def test_app_runtime_has_no_webhook_package_outbox_importers() -> None:
    app_root = ROOT / "truffles-api" / "app"
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if module == "app.routers.webhook" and any(
                alias.name == "_process_outbox_rows" for alias in node.names
            ):
                violations.append(str(path.relative_to(ROOT)))
            elif node.level == 1 and module == "" and any(
                alias.name == "_process_outbox_rows" for alias in node.names
            ):
                violations.append(str(path.relative_to(ROOT)))

    assert violations == []


def test_app_runtime_has_no_webhook_outbox_importers() -> None:
    app_root = ROOT / "truffles-api" / "app"
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        if path == app_root / "routers" / "webhook" / "outbox.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.routers.webhook.outbox":
                        violations.append(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app.routers.webhook.outbox":
                    violations.append(str(path.relative_to(ROOT)))

    assert violations == []


def test_decision_router_has_no_outbox_process_wrapper() -> None:
    decision_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_text = decision_path.read_text(encoding="utf-8")

    assert "async def _process_outbox_rows(" not in decision_text


def test_outbox_request_wrappers_are_thin() -> None:
    outbox_service_text = (ROOT / "truffles-api" / "app" / "routers" / "outbox_service.py").read_text(
        encoding="utf-8"
    )
    admin_text = (ROOT / "truffles-api" / "app" / "routers" / "admin.py").read_text(encoding="utf-8")

    for text in (outbox_service_text, admin_text):
        assert "run_default_outbox_process(" in text
        assert "release_stale_processing(" not in text
        assert "claim_pending_outbox_batches(" not in text
        assert "schedule_inbound_syncs(" not in text
        assert "_process_outbox_rows(" not in text

    assert "process_reminder_jobs(" not in outbox_service_text


def test_outbox_execution_low_level_imports_stay_in_shared_runtime_owner() -> None:
    app_root = ROOT / "truffles-api" / "app"
    owner_path = app_root / "services" / "outbox_runtime_service.py"
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        if path == owner_path:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            for alias in node.names:
                pair = (module, alias.name)
                if pair in {
                    ("app.services.outbox_service", "claim_pending_outbox_batches"),
                    ("app.services.outbox_service", "release_stale_processing"),
                    ("app.services.calendar_sync_service", "schedule_inbound_syncs"),
                }:
                    violations.append(f"{path.relative_to(ROOT)}:{module}:{alias.name}")

    assert violations == []


def test_outbox_worker_and_console_use_shared_runtime_settings() -> None:
    console_text = (ROOT / "truffles-api" / "app" / "routers" / "console.py").read_text(encoding="utf-8")
    worker_text = (ROOT / "truffles-api" / "app" / "workers" / "outbox.py").read_text(encoding="utf-8")

    assert "load_outbox_process_settings" in console_text
    assert "run_scoped_outbox_process(" in console_text
    assert "load_outbox_process_settings" in worker_text
    assert "run_outbox_worker_cycle(" in worker_text

    for removed_env_key in (
        "OUTBOX_PROCESS_LIMIT",
        "OUTBOX_COALESCE_SECONDS",
        "OUTBOX_MAX_WAIT_SECONDS",
        "OUTBOX_MAX_ATTEMPTS",
        "OUTBOX_RETRY_BACKOFF_SECONDS",
        "OUTBOX_STALE_PROCESSING_SECONDS",
    ):
        assert removed_env_key not in console_text
        assert removed_env_key not in worker_text


def test_outbox_worker_loop_uses_shared_runtime_cycle() -> None:
    worker_text = (ROOT / "truffles-api" / "app" / "workers" / "outbox.py").read_text(encoding="utf-8")

    assert "run_outbox_worker_cycle(" in worker_text
    assert "release_stale_processing(" not in worker_text
    assert "schedule_inbound_syncs(" not in worker_text
    assert "claim_pending_outbox_batches(" not in worker_text
    assert "process_claimed_outbox_rows(" not in worker_text


def test_console_router_has_no_local_outbox_claim_helper() -> None:
    console_text = (ROOT / "truffles-api" / "app" / "routers" / "console.py").read_text(encoding="utf-8")

    assert "def _claim_scoped_outbox_rows(" not in console_text
    assert "claim_scoped_outbox_rows(" not in console_text
    assert "run_scoped_outbox_process(" in console_text


def test_secondary_helper_mesh_has_no_legacy_adapter_imports() -> None:
    helper_paths = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "branch_selection.py",
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "shield.py",
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "session_memory.py",
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "trace.py",
    )

    for path in helper_paths:
        text = path.read_text(encoding="utf-8")
        assert "from . import _legacy as legacy" not in text


def test_session_memory_helper_is_not_an_allowed_continuity_writer() -> None:
    config = yaml.safe_load((ROOT / "docs" / "LEGACY_SUNSET.yaml").read_text(encoding="utf-8"))
    allowed_writer_paths = set((config or {}).get("continuity_guard", {}).get("allowed_writer_paths") or [])

    assert "truffles-api/app/routers/webhook/session_memory.py" not in allowed_writer_paths


def test_pending_and_state_service_are_not_allowed_continuity_writers() -> None:
    config = yaml.safe_load((ROOT / "docs" / "LEGACY_SUNSET.yaml").read_text(encoding="utf-8"))
    allowed_writer_paths = set((config or {}).get("continuity_guard", {}).get("allowed_writer_paths") or [])

    assert "truffles-api/app/routers/webhook/pending.py" not in allowed_writer_paths
    assert "truffles-api/app/services/state_service.py" not in allowed_writer_paths


def test_context_manager_is_not_an_allowed_continuity_writer() -> None:
    config = yaml.safe_load((ROOT / "docs" / "LEGACY_SUNSET.yaml").read_text(encoding="utf-8"))
    allowed_writer_paths = set((config or {}).get("continuity_guard", {}).get("allowed_writer_paths") or [])

    assert "truffles-api/app/routers/webhook/context_manager.py" not in allowed_writer_paths


def test_only_dialog_state_service_is_allowed_continuity_writer() -> None:
    config = yaml.safe_load((ROOT / "docs" / "LEGACY_SUNSET.yaml").read_text(encoding="utf-8"))
    allowed_writer_paths = list((config or {}).get("continuity_guard", {}).get("allowed_writer_paths") or [])

    assert allowed_writer_paths == ["truffles-api/app/core/dialog_state_service.py"]


def test_media_outbox_helper_family_has_no_legacy_adapter_imports() -> None:
    helper_paths = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "media.py",
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "outbox.py",
    )

    for path in helper_paths:
        text = path.read_text(encoding="utf-8")
        assert "from . import _legacy as legacy" not in text


def test_final_legacy_residue_first_wave_uses_direct_owners() -> None:
    init_text = (ROOT / "truffles-api" / "app" / "routers" / "webhook" / "__init__.py").read_text(
        encoding="utf-8"
    )
    tool_registry_text = (
        ROOT / "truffles-api" / "app" / "services" / "tool_registry_service.py"
    ).read_text(encoding="utf-8")
    decision_text = (
        ROOT / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    ).read_text(encoding="utf-8")

    assert "from app.routers.webhook._legacy import" not in init_text
    assert "from app.routers.webhook import _legacy as legacy" not in tool_registry_text
    for removed_symbol in (
        "legacy.is_greeting_message(",
        "legacy.classify_intent(",
        "legacy._normalize_service_text(",
        "legacy._resolve_controller_signal_class(",
        "legacy.DomainIntent.UNKNOWN",
        "legacy._set_router_observability(",
    ):
        assert removed_symbol not in decision_text


def test_policy_decision_creation_stays_in_governed_core_boundary() -> None:
    app_root = ROOT / "truffles-api" / "app"
    turn_planner_path = app_root / "core" / "turn_planner.py"
    boundary_validator_path = app_root / "core" / "boundary_validator.py"

    direct_constructor_violations: list[str] = []
    model_validate_violations: list[str] = []

    for path in app_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "PolicyDecision":
                if path != turn_planner_path:
                    direct_constructor_violations.append(str(path.relative_to(ROOT)))
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == "model_validate"
                and isinstance(func.value, ast.Name)
                and func.value.id == "PolicyDecision"
            ):
                if path not in {turn_planner_path, boundary_validator_path}:
                    model_validate_violations.append(str(path.relative_to(ROOT)))

    assert direct_constructor_violations == []
    assert model_validate_violations == []


def test_app_runtime_has_no_legacy_adapter_importers() -> None:
    app_root = ROOT / "truffles-api" / "app"
    importers: list[str] = []

    for path in app_root.rglob("*.py"):
        if path == app_root / "routers" / "webhook" / "_legacy.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.routers.webhook._legacy":
                        importers.append(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app.routers.webhook._legacy":
                    importers.append(str(path.relative_to(ROOT)))
                elif module == "app.routers.webhook" and any(
                    alias.name == "_legacy" for alias in node.names
                ):
                    importers.append(str(path.relative_to(ROOT)))
                elif node.level == 1 and module == "" and any(
                    alias.name == "_legacy" for alias in node.names
                ):
                    importers.append(str(path.relative_to(ROOT)))

    assert importers == []


def test_turn_executor_execute_is_binding_only_router() -> None:
    executor_path = ROOT / "truffles-api" / "app" / "core" / "turn_executor.py"
    execute_node = _function_def(_class_def(executor_path, "TurnExecutor"), "execute")

    attrs = _decision_attr_reads(execute_node)

    assert "outcome" not in attrs
    assert "tool_action" not in attrs
    assert "binding_plan" not in attrs


def test_consultant_runtime_control_predicates_are_binding_only() -> None:
    runtime_path = ROOT / "truffles-api" / "app" / "core" / "consultant_runtime.py"
    runtime_class = _class_def(runtime_path, "ConsultantRuntime")
    handoff_node = _function_def(runtime_class, "_decision_requests_handoff")
    collect_node = _function_def(runtime_class, "_decision_collects")

    handoff_attrs = _decision_attr_reads(handoff_node)
    collect_attrs = _decision_attr_reads(collect_node)

    assert "outcome" not in handoff_attrs
    assert "outcome" not in collect_attrs


def test_boundary_request_dataclasses_do_not_shape_planner_action() -> None:
    executor_path = ROOT / "truffles-api" / "app" / "core" / "turn_executor.py"

    assert "action" not in _class_field_names(executor_path, "BlockBoundaryRequest")
    assert "action" not in _class_field_names(executor_path, "DegradeBoundaryRequest")


def test_turn_planner_boundary_signal_builders_have_fixed_shape() -> None:
    from app.core.turn_planner import TurnPlanner

    planner = TurnPlanner()
    preflight = planner.build_preflight_reject_signal(
        reason_code="missing_remote_jid",
        control_label="missing_remote_jid",
        interaction_owner="reasoning_core_missing_remote_jid",
    )
    degrade = planner.build_controlled_degrade_signal(
        reason_code="runtime_exception",
        control_label="runtime_error",
        interaction_owner="reasoning_core_exception_degrade",
    )

    assert preflight.decision == "block"
    assert preflight.reason_code == "missing_remote_jid"
    assert preflight.control_label == "missing_remote_jid"
    assert preflight.interaction_owner == "reasoning_core_missing_remote_jid"

    assert degrade.decision == "degrade"
    assert degrade.reason_code == "runtime_exception"
    assert degrade.control_label == "runtime_error"
    assert degrade.interaction_owner == "reasoning_core_exception_degrade"


def test_workstream8_observability_and_release_gate_artifacts_exist() -> None:
    runtime_trace_text = (
        ROOT / "truffles-api" / "app" / "core" / "runtime_trace_contract.py"
    ).read_text(encoding="utf-8")
    shadow_replay_text = (ROOT / "ops" / "shadow_replay.py").read_text(encoding="utf-8")
    chain_controller_text = (
        ROOT / "scripts" / "quality_chain_controller.sh"
    ).read_text(encoding="utf-8")
    runtime_contract_schema = (
        ROOT / "contracts" / "runtime" / "runtime_trace_contract.v1.jsonschema"
    ).read_text(encoding="utf-8")
    release_gate_schema = (
        ROOT / "contracts" / "runtime" / "release_gate_evidence.v1.jsonschema"
    ).read_text(encoding="utf-8")

    assert "class RuntimeTraceContractV1" in runtime_trace_text
    assert '"runtime_trace_contract.v1"' in runtime_contract_schema
    assert '"release_gate_evidence.v1"' in release_gate_schema
    assert "def _score_runtime_trace_contract_diff(" in shadow_replay_text
    assert "runtime_trace_contract.shadow_score" in shadow_replay_text
    assert "def _write_release_gate_artifacts(" in chain_controller_text
    assert '"release_gate_evidence.v1"' in chain_controller_text


def test_workstream8_hotspots_emit_standardized_proof_and_release_evidence() -> None:
    runtime_text = (
        ROOT / "truffles-api" / "app" / "core" / "consultant_runtime.py"
    ).read_text(encoding="utf-8")
    executor_text = (
        ROOT / "truffles-api" / "app" / "core" / "turn_executor.py"
    ).read_text(encoding="utf-8")
    shadow_replay_text = (ROOT / "ops" / "shadow_replay.py").read_text(encoding="utf-8")
    chain_controller_text = (
        ROOT / "scripts" / "quality_chain_controller.sh"
    ).read_text(encoding="utf-8")

    assert "runtime_trace_contract" in runtime_text
    assert "runtime_trace_contract" in executor_text
    assert "runtime_trace_contract.mismatch_pointers" in shadow_replay_text
    assert "release_gate.json" in chain_controller_text
    assert '"decision": "rollback_executed"' in chain_controller_text
