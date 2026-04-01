import ast
import hashlib
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def _load_quality_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assignments = {
        "CHAOS_BOOKING_REPLY_TYPES",
        "LLM_QUALITY_THRESHOLDS",
        "LLM_QUALITY_THRESHOLD_DIRECTIONS",
        "LLM_QUALITY_REGRESSION_KEYS",
        "LLM_QUALITY_BLOCKING_REASONS",
        "LLM_QUALITY_HQ1_CLASSES",
        "LLM_QUALITY_HQ1_RESCHEDULE_MARKERS",
        "LLM_QUALITY_HQ1_MASTER_MARKERS",
        "LLM_QUALITY_HQ1_SERVICE_OVERVIEW_MARKERS",
        "LLM_QUALITY_HQ1_HALLUCINATION_MARKERS",
        "LLM_POLICY_OVERRIDE_REASON_WHITELIST",
        "LLM_POLICY_OVERRIDE_KEYWORD_REASON_CODES",
        "LLM_POLICY_OVERRIDE_NON_SEMANTIC_GUARD_REASON_CODES",
        "LLM_QUALITY_REGEX_LEXICON_TOKENS",
        "LLM_QUALITY_REGEX_LEXICON_RESOLVER_PREFIXES",
        "LLM_QUALITY_REGEX_LEXICON_TEST_PREFIX",
        "LLM_QUALITY_HARDCODE_CORE_PREFIXES",
        "LLM_QUALITY_HARDCODE_SCOPE_WEBHOOK_PREFIX",
        "LLM_QUALITY_HARDCODE_SCOPE_SERVICE_PREFIX",
        "LLM_QUALITY_HARDCODE_SCOPE_SERVICE_FILES",
        "LLM_QUALITY_HARDCODE_SCOPE_SERVICE_SUFFIXES",
        "LLM_QUALITY_MATRIX_MIN_NON_SALON_PACKS",
        "LLM_QUALITY_MATRIX_NON_SALON_EXCLUDED_SLUGS",
        "LLM_QUALITY_OPEN_WORLD_REQUIRED_LANGUAGE_PROFILES",
        "LLM_QUALITY_OPEN_WORLD_REQUIRED_SURFACE_NOISE_PROFILES",
        "LLM_QUALITY_OPEN_WORLD_REQUIRED_SEMANTIC_VARIATION_PROFILES",
        "LLM_QUALITY_OPEN_WORLD_REQUIRED_SLOT_FORMAT_PROFILES",
        "LLM_QUALITY_HARDCODE_ALLOW_MARKER",
        "LLM_QUALITY_HARDCODE_TECHNICAL_ALLOW_SNIPPETS",
        "LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE",
        "LLM_QUALITY_PROGRESS_SKIP_TAGS",
        "LLM_QUALITY_REQUIRED_RUN_ARTIFACTS",
        "LLM_QUALITY_EVIDENCE_HANDOFF_REQUIRED_ARTIFACTS",
        "LLM_QUALITY_MANUAL_AUDIT_AUX_ARTIFACTS",
        "LLM_QUALITY_SCENARIO_GOVERNANCE_REGISTRY",
        "LLM_QUALITY_SCENARIO_GOVERNANCE_SCHEMA_VERSION",
        "LLM_QUALITY_SCENARIO_REALISM_POLICY_VERSION",
        "LLM_QUALITY_SCENARIO_REALISM_REQUIRED_BUCKETS",
        "LLM_QUALITY_SCENARIO_REALISM_MIN_DIALOG_COUNT",
        "LLM_QUALITY_SCENARIO_REALISM_MIN_TURN_COUNT",
        "LLM_QUALITY_ORACLE_ALIGNMENT_VALUES",
        "LLM_QUALITY_ORACLE_WINNER_VALUES",
    }
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_llm_quality_is_timeout_degrade_reason",
        "_clean_webhook_secret",
        "_llm_quality_secret_fingerprint",
        "_llm_quality_resolve_expected_webhook_secret",
        "_llm_quality_webhook_secret_preflight",
        "_llm_quality_is_judge_mode_enabled",
        "_llm_quality_baseline_is_canonical",
        "_llm_quality_build_infra_status",
        "_llm_quality_build_delivery_acceptance_status",
        "_llm_quality_compute_invariant_metrics",
        "_llm_quality_check_thresholds",
        "_llm_quality_check_regression",
        "_llm_quality_collect_override_reason_codes",
        "_llm_quality_collect_semantic_intent_override_audit",
        "_llm_quality_collect_plan_delta_audit",
        "_llm_quality_init_rewrite_governance_state",
        "_llm_quality_track_rewrite_governance",
        "_llm_quality_finalize_rewrite_governance",
        "_llm_quality_collect_blocking_reasons",
        "_llm_quality_is_weak_oracle_expectation",
        "_llm_quality_build_run_integrity_status",
        "_llm_quality_validate_scenario_artifacts",
        "_llm_quality_is_lexicon_regex_delta_file",
        "_llm_quality_build_lexicon_regex_delta_status",
        "_llm_quality_is_hardcode_core_file",
        "_llm_quality_line_has_phrase_branching",
        "_llm_quality_collect_hardcode_core_violations",
        "_llm_quality_build_hardcode_core_gate_status",
        "_llm_quality_is_doc_only_changed_file",
        "_llm_quality_load_json_object",
        "_llm_quality_resolve_manual_audit_status",
        "_llm_quality_build_run_economy_status",
        "_llm_quality_parse_coverage_tokens",
        "_llm_quality_build_quality_constant_status",
        "_parse_csv_values",
        "_llm_quality_normalize_matrix_client_slugs",
        "_llm_quality_collect_scenario_profile_coverage",
        "_llm_quality_build_open_world_profile_status",
        "_llm_quality_build_p6_acceptance_closure_status",
        "_llm_quality_build_cross_domain_matrix_contract_status",
        "_llm_quality_collect_workaround_marker_hits",
        "_llm_quality_collect_workaround_register_ids",
        "_llm_quality_build_workaround_register_status",
        "_llm_quality_build_replay_command",
        "_llm_quality_manifest_mode",
        "_llm_quality_required_artifact_paths",
        "_llm_quality_collect_artifact_integrity",
        "_llm_quality_collect_evidence_handoff_status",
        "_llm_quality_build_governance_closure_status",
        "_llm_quality_is_iso_timestamp",
        "_llm_quality_extract_chain_id",
        "_llm_quality_extract_oracle_conflict_count",
        "_llm_quality_validate_manual_audit_sla",
        "_llm_quality_sync_manual_audit_summary",
        "_llm_quality_find_latest_pending_manual_audit",
        "_llm_quality_find_latest_completed_manual_audit",
        "_llm_quality_build_manual_audit_gate_status",
        "_llm_quality_build_forensic_sla_gate_status",
        "_llm_quality_build_oracle_conflict_gate_status",
        "_llm_quality_build_secret_transport_gate_status",
        "_llm_quality_load_scenario_governance_registry",
        "_llm_quality_save_scenario_governance_registry",
        "_llm_quality_build_scenario_realism_sla",
        "_llm_quality_next_scenario_promotion_status",
        "_llm_quality_build_scenario_governance_status",
        "_llm_quality_update_scenario_governance_registry",
        "_llm_quality_finalize_scenario_governance_registry",
        "_llm_quality_chain_resolve_requested_mode",
        "_llm_quality_acceptance_entrypoint_hint",
        "_llm_quality_digest_file",
        "_llm_quality_hq1_normalize_text",
        "_llm_quality_hq1_contains_any",
        "_llm_quality_hq1_has_hallucination_signal",
        "_llm_quality_collect_hq1_classes",
        "_llm_quality_should_expect_booking_progress",
        "_llm_quality_should_promote_judge_fail",
        "_llm_quality_collect_human_semantic_strict_reasons",
    }

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
        "json": json,
        "os": os,
        "re": re,
        "shlex": shlex,
        "subprocess": subprocess,
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _write_manual_audit_aux_artifacts(run_dir: Path):
    (run_dir / "manual_audit_workspace.md").write_text("# workspace", encoding="utf-8")
    (run_dir / "manual_audit_workspace.json").write_text("{}", encoding="utf-8")
    (run_dir / "family_registry.json").write_text("{}", encoding="utf-8")
    (run_dir / "judge_conflicts.jsonl").write_text("", encoding="utf-8")


def _done_manual_audit_payload(run_dir: Path, run_id: str, **overrides):
    payload = {
        "status": "done",
        "run_id": run_id,
        "analyst": "a1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analyst_root_causes": ["contract_validated"],
        "analyst_next_steps": ["promote_next_chain_step"],
        "findings": [],
        "oracle_arbitration": {
            "conflict_count": 0,
            "judge_alignment": "not_applicable",
            "winner": "contract",
            "resolution_summary": "manual audit completed",
        },
        "artifacts": {
            "manual_audit_workspace_markdown": str(run_dir / "manual_audit_workspace.md"),
            "manual_audit_workspace_json": str(run_dir / "manual_audit_workspace.json"),
            "family_registry_json": str(run_dir / "family_registry.json"),
            "judge_conflicts_jsonl": str(run_dir / "judge_conflicts.jsonl"),
        },
    }
    payload.update(overrides)
    return payload


def test_webhook_secret_preflight_enforces_branch_secret_match():
    ns = _load_quality_helpers()
    resolve_expected = ns["_llm_quality_resolve_expected_webhook_secret"]
    preflight = ns["_llm_quality_webhook_secret_preflight"]

    expected, source = resolve_expected(
        {
            "branch_webhook_secret": "branch-secret",
            "client_webhook_secret": "client-secret",
        }
    )
    result = preflight(
        provided_secret="client-secret",
        expected_secret=expected,
        expected_source=source,
        secret_source="explicit",
    )

    assert result["valid"] is False
    assert "secret_mismatch" in result["reasons"]


def test_webhook_secret_preflight_accepts_expected_branch_secret():
    ns = _load_quality_helpers()
    resolve_expected = ns["_llm_quality_resolve_expected_webhook_secret"]
    preflight = ns["_llm_quality_webhook_secret_preflight"]

    expected, source = resolve_expected(
        {
            "branch_webhook_secret": "branch-secret",
            "client_webhook_secret": "client-secret",
        }
    )
    result = preflight(
        provided_secret="branch-secret",
        expected_secret=expected,
        expected_source=source,
        secret_source="runtime_expected",
    )

    assert result["valid"] is True
    assert result["reasons"] == []


def test_secret_transport_gate_blocks_explicit_secret_in_acceptance_lane():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_secret_transport_gate_status"]

    status = build(
        mode="block",
        lane_effective="acceptance",
        webhook_secret_source="explicit",
    )

    assert status["required"] is True
    assert status["enforced"] is True
    assert status["valid"] is False
    assert "secret_exposure_detected:argv_webhook_secret" in status["reasons"]


def test_secret_transport_gate_is_non_blocking_outside_acceptance_lane():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_secret_transport_gate_status"]

    status = build(
        mode="block",
        lane_effective="dev",
        webhook_secret_source="explicit",
    )

    assert status["required"] is False
    assert status["enforced"] is False
    assert status["valid"] is True
    assert "secret_exposure_detected:argv_webhook_secret" in status["reasons"]


def test_baseline_canonical_requires_judge_on():
    ns = _load_quality_helpers()
    baseline_is_canonical = ns["_llm_quality_baseline_is_canonical"]

    canonical, reason = baseline_is_canonical({"config": {"judge_mode": "sample"}})
    assert canonical is True
    assert reason is None

    canonical, reason = baseline_is_canonical({"config": {"judge_mode": "critical"}})
    assert canonical is True
    assert reason is None

    canonical, reason = baseline_is_canonical({"config": {"judge_mode": "off"}})
    assert canonical is False
    assert reason == "judge_mode_off"


def test_baseline_canonical_rejects_dry_run_even_with_judge_enabled():
    ns = _load_quality_helpers()
    baseline_is_canonical = ns["_llm_quality_baseline_is_canonical"]

    canonical, reason = baseline_is_canonical(
        {
            "config": {"judge_mode": "all", "dry_run": True},
            "quality_status": {
                "infra_valid": True,
                "semantic_valid": True,
                "blocking_reason_count": 0,
            },
        }
    )
    assert canonical is False
    assert reason == "dry_run"


def test_baseline_canonical_rejects_invalid_quality_status():
    ns = _load_quality_helpers()
    baseline_is_canonical = ns["_llm_quality_baseline_is_canonical"]

    canonical, reason = baseline_is_canonical(
        {
            "config": {"judge_mode": "all"},
            "quality_status": {
                "infra_valid": True,
                "semantic_valid": True,
                "blocking_reason_count": 2,
            },
        }
    )
    assert canonical is False
    assert reason == "blocking_reasons_present"


def test_infra_status_marks_invalid_on_preflight_or_runtime_errors():
    ns = _load_quality_helpers()
    build_infra_status = ns["_llm_quality_build_infra_status"]

    status = build_infra_status(
        {
            "webhook_errors": 1,
            "infra_errors": 0,
            "decision_meta_errors": 0,
            "decision_trace_errors": 0,
        },
        {"valid": False, "reasons": ["secret_mismatch"]},
    )

    assert status["valid"] is False
    assert "webhook_errors" in status["reasons"]
    assert "webhook_secret_preflight:secret_mismatch" in status["reasons"]


def test_infra_status_marks_invalid_on_outbox_delivery_failures():
    ns = _load_quality_helpers()
    build_infra_status = ns["_llm_quality_build_infra_status"]

    status = build_infra_status(
        {
            "webhook_errors": 0,
            "infra_errors": 0,
            "decision_meta_errors": 0,
            "decision_trace_errors": 0,
            "outbox_delivery_failed_turns": 2,
            "outbox_delivery_timeout_turns": 1,
        },
        {"valid": True, "reasons": []},
        failure_counts={"outbox_delivery_failed": 2, "outbox_delivery_timeout": 1},
    )

    assert status["valid"] is False
    assert "outbox_delivery_failed_turns" in status["reasons"]
    assert "outbox_delivery_timeout_turns" in status["reasons"]
    assert "outbox_delivery_failed" in status["reasons"]
    assert "outbox_delivery_timeout" in status["reasons"]


def test_delivery_acceptance_marks_waiver_for_billing_blocked():
    ns = _load_quality_helpers()
    build_delivery = ns["_llm_quality_build_delivery_acceptance_status"]

    status = build_delivery(
        {
            "outbox_delivery_failed_turns": 0,
            "outbox_delivery_timeout_turns": 0,
            "delivery_waiver_billing_turns": 2,
        },
        failure_counts={"delivery_waiver_billing": 2},
    )

    assert status["valid"] is True
    assert status["status"] == "waived"
    assert status["waived"] is True
    assert status["waivers"] == ["delivery_waiver_billing"]
    assert status["counts"]["delivery_waiver_billing_turns"] == 2


def test_thresholds_include_degraded_fallback_rate_gate():
    ns = _load_quality_helpers()
    check_thresholds = ns["_llm_quality_check_thresholds"]

    metrics = {
        "rates": {
            "reply_rate": 1.0,
            "strict_pass_rate": 1.0,
            "expected_reply_rate": 1.0,
            "info_answer_rate": 1.0,
            "hard_fail_rate": 0.0,
            "unknown_state_rate": 0.0,
            "degraded_fallback_rate": 0.6,
            "booking_slot_progress_rate": 1.0,
            "handoff_correct_rate": 1.0,
        }
    }
    _results, breaches = check_thresholds(metrics)

    assert "degraded_fallback_rate" in breaches


def test_threshold_defaults_are_aligned_with_acceptance_contract():
    ns = _load_quality_helpers()
    thresholds = ns["LLM_QUALITY_THRESHOLDS"]

    assert thresholds["strict_pass_rate"] == 0.95
    assert thresholds["degraded_fallback_rate"] == 0.05
    assert thresholds["fact_without_evidence_rate"] == 0.0
    assert thresholds["irrelevant_fact_rate"] == 0.0
    assert thresholds["booking_commit_without_required_contact"] == 0.0
    assert thresholds["semantic_override_rate"] == 0.0
    assert thresholds["stale_state_leak_rate"] == 0.0


def test_compute_invariant_metrics_collects_required_rates():
    ns = _load_quality_helpers()
    compute = ns["_llm_quality_compute_invariant_metrics"]

    metrics = compute(
        failure_counts={
            "fact_without_evidence": 2,
            "irrelevant_fact": 1,
            "booking_commit_without_required_contact": 1,
            "stale_state_leak": 3,
        },
        stats={"turns": 20},
        rewrite_governance={"rewrite_budget_turns": 2, "policy_core_turns": 10},
    )

    assert metrics["counts"]["fact_without_evidence"] == 2
    assert metrics["rates"]["fact_without_evidence_rate"] == 0.1
    assert metrics["rates"]["irrelevant_fact_rate"] == 0.05
    assert metrics["rates"]["booking_commit_without_required_contact"] == 0.05
    assert metrics["rates"]["semantic_override_rate"] == 0.2
    assert metrics["rates"]["stale_state_leak_rate"] == 0.15


def test_thresholds_include_llm_first_invariant_gates():
    ns = _load_quality_helpers()
    check_thresholds = ns["_llm_quality_check_thresholds"]

    metrics = {
        "rates": {
            "reply_rate": 1.0,
            "strict_pass_rate": 1.0,
            "expected_reply_rate": 1.0,
            "info_answer_rate": 1.0,
            "hard_fail_rate": 0.0,
            "unknown_state_rate": 0.0,
            "degraded_fallback_rate": 0.0,
            "booking_slot_progress_rate": 1.0,
            "handoff_correct_rate": 1.0,
            "fact_without_evidence_rate": 0.1,
            "irrelevant_fact_rate": 0.1,
            "booking_commit_without_required_contact": 0.1,
            "semantic_override_rate": 0.1,
            "stale_state_leak_rate": 0.1,
        }
    }

    _results, breaches = check_thresholds(metrics)

    assert "fact_without_evidence_rate" in breaches
    assert "irrelevant_fact_rate" in breaches
    assert "booking_commit_without_required_contact" in breaches
    assert "semantic_override_rate" in breaches
    assert "stale_state_leak_rate" in breaches


def test_regression_checks_degraded_fallback_rate_as_max_direction():
    ns = _load_quality_helpers()
    check_regression = ns["_llm_quality_check_regression"]

    metrics = {"rates": {"degraded_fallback_rate": 0.45}}
    baseline = {"rates": {"degraded_fallback_rate": 0.25}}
    results, breaches = check_regression(metrics, baseline, tolerance=0.02)

    assert results["degraded_fallback_rate"]["direction"] == "max"
    assert "degraded_fallback_rate" in breaches


def test_timeout_degrade_reason_classifier_detects_deadline_and_timeout_markers():
    ns = _load_quality_helpers()
    is_timeout = ns["_llm_quality_is_timeout_degrade_reason"]

    assert is_timeout("policy_error:deadline_exceeded") is True
    assert is_timeout("provider_timeout") is True
    assert is_timeout("policy_validation:low_confidence") is False


def test_rewrite_governance_blocks_missing_and_unknown_reason_codes():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_override_reason_code": "contract_validation_failure",
        },
    )
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_override_reason_missing_detected": True,
        },
    )
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_override_reason_codes": ["custom_override"],
        },
    )
    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=0.5,
        max_keyword_override_rate=0.0,
    )

    assert status["valid"] is False
    assert status["rewrite_turns"] == 3
    assert status["rewrite_reason_missing_turns"] == 1
    assert status["rewrite_unknown_reason_turns"] == 1
    assert "rewrite_reason_missing" in status["blocking_counts"]
    assert "rewrite_reason_unknown" in status["blocking_counts"]
    assert status["rewrite_reason_coverage"] < 1.0


def test_rewrite_governance_blocks_semantic_intent_override_audit_violations():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_core": {
                "semantic_arbiter": {"audit": {"intent_override_count": 1}},
                "semantic_intent_overrides": [
                    {"reason_code": "contract_validation_failure", "from_intent": "info", "to_intent": "master"}
                ],
            },
        },
    )
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_core": {
                "semantic_arbiter": {"audit": {"intent_override_count": 1}},
                "semantic_intent_overrides": [{"from_intent": "info", "to_intent": "master"}],
            },
        },
    )
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_core": {
                "semantic_arbiter": {"audit": {"intent_override_count": 1}},
                "semantic_intent_overrides": [
                    {"reason_code": "custom_override", "from_intent": "info", "to_intent": "master"}
                ],
            },
        },
    )
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_core": {
                "semantic_arbiter": {"audit": {"intent_override_count": 2}},
                "semantic_intent_overrides": [
                    {"reason_code": "contract_validation_failure", "from_intent": "info", "to_intent": "master"}
                ],
            },
        },
    )
    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=1.0,
        max_keyword_override_rate=1.0,
    )

    assert status["valid"] is False
    assert status["semantic_intent_override_turns"] == 4
    assert status["semantic_intent_override_reason_missing_turns"] == 2
    assert status["semantic_intent_override_reason_unknown_turns"] == 1
    assert status["semantic_intent_override_count_mismatch_turns"] == 1
    assert "semantic_intent_override_reason_missing" in status["blocking_counts"]
    assert "semantic_intent_override_reason_unknown" in status["blocking_counts"]
    assert "semantic_intent_override_count_mismatch" in status["blocking_counts"]


def test_rewrite_governance_uses_discrete_turn_budget_ceiling():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    for index in range(88):
        meta = {"policy_core_mode": "policy_core"}
        if index in {3, 41}:
            meta["llm_policy_override_reason_code"] = "required_slot_missing"
        track(state, meta)

    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=0.02,
        max_keyword_override_rate=0.0,
    )

    assert status["rewrite_turns"] == 2
    assert status["max_rewrite_turns"] == 2
    assert "post_llm_semantic_rewrite_budget_exceeded" not in status["blocking_counts"]
    assert status["valid"] is True


def test_rewrite_governance_ignores_semantic_override_audit_without_effective_change():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    track(
        state,
        {
            "policy_core_mode": "policy_core",
            "llm_policy_core": {
                "semantic_arbiter": {
                    "audit": {
                        "intent_override_count": 1,
                        "action_changed": False,
                        "intent_changed": False,
                        "tool_action_changed": False,
                        "intent_override_reason_codes": ["contract_validation_failure"],
                    }
                },
                "semantic_intent_overrides": [
                    {
                        "reason_code": "contract_validation_failure",
                        "from_intent": "info",
                        "to_intent": "master",
                    }
                ],
            },
        },
    )
    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=0.0,
        max_keyword_override_rate=0.0,
    )

    assert status["semantic_intent_override_turns"] == 1
    assert status["rewrite_turns"] == 0
    assert "post_llm_semantic_rewrite_budget_exceeded" not in status["blocking_counts"]
    assert status["valid"] is True


def test_rewrite_governance_excludes_non_semantic_contract_guard_from_budget():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    for index in range(120):
        meta = {"policy_core_mode": "policy_core"}
        if index in {7, 33, 58}:
            meta["llm_policy_override_reason_code"] = "contract_validation_failure"
            meta["llm_policy_plan_audit"] = {
                "action_changed": False,
                "intent_changed": False,
                "tool_action_changed": True,
            }
        track(state, meta)

    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=0.02,
        max_keyword_override_rate=0.0,
    )

    assert status["rewrite_turns"] == 3
    assert status["non_semantic_contract_guard_turns"] == 3
    assert status["rewrite_budget_turns"] == 0
    assert status["post_llm_semantic_rewrite_rate"] == 0.0
    assert "post_llm_semantic_rewrite_budget_exceeded" not in status["blocking_counts"]
    assert status["valid"] is True


def test_rewrite_governance_counts_contract_guard_action_change_against_budget():
    ns = _load_quality_helpers()
    init_state = ns["_llm_quality_init_rewrite_governance_state"]
    track = ns["_llm_quality_track_rewrite_governance"]
    finalize = ns["_llm_quality_finalize_rewrite_governance"]

    state = init_state()
    for index in range(120):
        meta = {"policy_core_mode": "policy_core"}
        if index in {3, 18, 42, 77}:
            meta["llm_policy_override_reason_code"] = "contract_validation_failure"
            meta["llm_policy_plan_audit"] = {
                "action_changed": True,
                "intent_changed": False,
                "tool_action_changed": True,
            }
        track(state, meta)

    status = finalize(
        state,
        max_post_llm_semantic_rewrite_rate=0.02,
        max_keyword_override_rate=0.0,
    )

    assert status["rewrite_turns"] == 4
    assert status["non_semantic_contract_guard_turns"] == 0
    assert status["rewrite_budget_turns"] == 4
    assert status["blocking_counts"]["post_llm_semantic_rewrite_budget_exceeded"] == 4
    assert status["valid"] is False


def test_collect_blocking_reasons_merges_governance_counts():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_blocking_reasons"]
    result = collect(
        {"expected_reply_type_mismatch": 2},
        extra_counts={
            "post_llm_semantic_rewrite_budget_exceeded": 1,
            "rewrite_reason_missing": 3,
        },
    )
    assert result["count"] == 6
    assert result["reasons"]["expected_reply_type_mismatch"] == 2
    assert result["reasons"]["post_llm_semantic_rewrite_budget_exceeded"] == 1
    assert result["reasons"]["rewrite_reason_missing"] == 3


def test_weak_oracle_expectation_detects_empty_contract():
    ns = _load_quality_helpers()
    is_weak = ns["_llm_quality_is_weak_oracle_expectation"]

    assert is_weak({"action": None, "info_sections": [], "reply_type": None, "state": None}) is True
    assert is_weak({"expected_reply": True}) is True
    assert is_weak({"reply_type": "time"}) is False
    assert is_weak({"expected_reply": True, "action": "collect"}) is False


def test_run_economy_blocks_full_run_without_non_doc_delta():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    status = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["docs/TASK_PACKAGES/TP-test.md"],
    )

    assert status["valid"] is False
    assert status["enforced"] is True
    assert "full_run_without_code_delta" in status["reasons"]


def test_run_economy_blocks_replay_without_baseline_or_reset():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    status = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file="/tmp/booking_quality/run/scenarios.json",
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
    )

    assert status["valid"] is False
    assert "replay_without_baseline_summary" in status["reasons"]
    assert "replay_without_reset_before_dialog" in status["reasons"]


def test_run_economy_allows_replay_with_baseline_and_reset():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    status = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file="/tmp/booking_quality/run/scenarios.json",
        baseline_summary="/tmp/booking_quality/lock/summary.json",
        reset_before_dialog=True,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
    )

    assert status["valid"] is True
    assert status["reasons"] == []


def test_run_economy_blocks_lock_with_unchanged_non_canonical_fingerprint():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert initial["valid"] is True
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    blocked = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": False,
            "run_id": "lock-non-canonical",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert blocked["valid"] is False
    assert "lock_fingerprint_unchanged_after_non_canonical" in blocked["reasons"]


def test_run_economy_allows_lock_with_unchanged_canonical_fingerprint():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    allowed = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": True,
            "run_id": "lock-canonical",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert allowed["valid"] is True
    assert "lock_fingerprint_unchanged_after_non_canonical" not in allowed["reasons"]


def test_run_economy_allows_non_canonical_lock_retry_for_process_stop_reason():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    allowed = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": False,
            "stop_reason": "invalid_quality_constant_preflight",
            "run_id": "lock-process-fail",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert allowed["valid"] is True
    assert allowed["non_canonical_lock_retry_eligible"] is True
    assert allowed["non_canonical_lock_retry_applied"] is True
    assert "lock_fingerprint_unchanged_after_non_canonical" not in allowed["reasons"]


def test_run_economy_allows_non_canonical_lock_retry_for_audited_infra_invalid_lock(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    previous_run_dir = tmp_path / "previous-lock"
    previous_run_dir.mkdir()
    summary_path = previous_run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "infra_valid": False,
                "artifact_integrity": {"valid": True},
                "manual_audit": {"status": "done"},
                "quality_status": {
                    "run_integrity_valid": False,
                    "infra_reasons": ["webhook_errors"],
                    "run_integrity_reasons": ["run_completion_gap"],
                },
            }
        ),
        encoding="utf-8",
    )

    allowed = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": False,
            "stop_reason": "max_failures_reached:1",
            "summary_path": str(summary_path),
            "run_id": "lock-infra-fail",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert allowed["valid"] is True
    assert allowed["non_canonical_lock_retry_eligible"] is True
    assert allowed["non_canonical_lock_retry_reason"] == "audited_infra_invalid_non_canonical"
    assert allowed["non_canonical_lock_retry_applied"] is True
    assert "lock_fingerprint_unchanged_after_non_canonical" not in allowed["reasons"]


def test_run_economy_blocks_non_canonical_lock_retry_for_unaudited_infra_invalid_lock(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    previous_run_dir = tmp_path / "previous-lock-pending"
    previous_run_dir.mkdir()
    summary_path = previous_run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "infra_valid": False,
                "artifact_integrity": {"valid": True},
                "manual_audit": {"status": "pending"},
                "quality_status": {
                    "run_integrity_valid": False,
                    "infra_reasons": ["webhook_errors"],
                    "run_integrity_reasons": ["run_completion_gap"],
                },
            }
        ),
        encoding="utf-8",
    )

    blocked = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": False,
            "stop_reason": "max_failures_reached:1",
            "summary_path": str(summary_path),
            "run_id": "lock-infra-pending",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert blocked["valid"] is False
    assert blocked["non_canonical_lock_retry_eligible"] is False
    assert blocked["non_canonical_lock_retry_reason"] is None
    assert blocked["non_canonical_lock_retry_applied"] is False
    assert "lock_fingerprint_unchanged_after_non_canonical" in blocked["reasons"]
    assert "lock_retry_override_not_eligible" in blocked["reasons"]


def test_run_economy_blocks_non_canonical_lock_retry_for_non_process_stop_reason():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    initial = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    lock_fingerprint = initial["lock_fingerprint"]
    assert isinstance(lock_fingerprint, str) and lock_fingerprint

    blocked = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file=None,
        baseline_summary=None,
        reset_before_dialog=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        previous_lock_state={
            "lock_fingerprint": lock_fingerprint,
            "canonical_valid": False,
            "stop_reason": "done",
            "run_id": "lock-semantic-fail",
        },
        run_mode="llm",
        dialog_count=10,
        min_turns=10,
        max_turns=15,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
    )
    assert blocked["valid"] is False
    assert blocked["non_canonical_lock_retry_eligible"] is False
    assert blocked["non_canonical_lock_retry_applied"] is False
    assert "lock_fingerprint_unchanged_after_non_canonical" in blocked["reasons"]
    assert "lock_retry_override_not_eligible" in blocked["reasons"]


def test_run_economy_blocks_replay_with_non_canonical_baseline():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    status = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file="/tmp/booking_quality/run/scenarios.json",
        baseline_summary="/tmp/booking_quality/lock/summary.json",
        reset_before_dialog=True,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        baseline_preflight={
            "checked": True,
            "canonical": False,
            "canonical_reason": "infra_invalid",
            "load_error": None,
        },
    )

    assert status["valid"] is False
    assert "replay_baseline_non_canonical" in status["reasons"]


def test_run_economy_blocks_replay_with_unreadable_baseline_summary():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_run_economy_status"]

    status = build(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        scenarios_file="/tmp/booking_quality/run/scenarios.json",
        baseline_summary="/tmp/booking_quality/lock/summary.json",
        reset_before_dialog=True,
        allow_no_code_delta=False,
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
        baseline_preflight={
            "checked": True,
            "canonical": None,
            "canonical_reason": None,
            "load_error": "baseline_parse_failed",
        },
    )

    assert status["valid"] is False
    assert "replay_baseline_unreadable" in status["reasons"]


def test_quality_constant_acceptance_lane_requires_canonical_envelope():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_quality_constant_status"]

    valid = build(
        mode="block",
        lane="acceptance",
        scenarios_file="/tmp/booking_quality/lock/scenarios.json",
        run_mode="llm",
        count=10,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
        judge_mode="all",
        run_economy_gate="block",
        manual_audit_gate="block",
        tool_evidence_policy="strict",
        fail_on_thresholds=True,
        fail_on_regression=True,
        allow_weak_oracle=False,
        allow_incomplete_run_artifacts=False,
        allow_judge_off=False,
        allow_no_code_delta=False,
        skip_outbox=False,
        update_baseline=False,
        timeout_profile="realistic",
        timeout=30,
        poll_timeout=25,
        trace_timeout=25,
    )
    assert valid["valid"] is True
    assert valid["reasons"] == []
    assert valid["lane_effective"] == "acceptance"

    invalid = build(
        mode="block",
        lane="acceptance",
        scenarios_file="/tmp/booking_quality/lock/scenarios.json",
        run_mode="llm",
        count=8,
        include_media=False,
        scenario_coverage="booking,info,interrupt",
        judge_mode="off",
        run_economy_gate="warn",
        manual_audit_gate="warn",
        tool_evidence_policy="auto",
        fail_on_thresholds=False,
        fail_on_regression=False,
        allow_weak_oracle=True,
        allow_incomplete_run_artifacts=True,
        allow_judge_off=True,
        allow_no_code_delta=True,
        skip_outbox=True,
        update_baseline=False,
        timeout_profile="fast-replay",
        timeout=12,
        poll_timeout=10,
        trace_timeout=10,
    )
    assert invalid["valid"] is False
    assert "acceptance_requires_fail_on_thresholds" in invalid["reasons"]
    assert "acceptance_requires_fail_on_regression_replay" in invalid["reasons"]
    assert "acceptance_requires_judge_mode" in invalid["reasons"]
    assert "acceptance_requires_count_gte_10" in invalid["reasons"]
    assert "acceptance_requires_include_media" in invalid["reasons"]
    assert "acceptance_missing_coverage:handoff" in invalid["reasons"]
    assert "acceptance_requires_run_economy_block" in invalid["reasons"]
    assert "acceptance_requires_manual_audit_block" in invalid["reasons"]
    assert "acceptance_requires_tool_evidence_strict" in invalid["reasons"]
    assert "acceptance_disallows_allow_judge_off" in invalid["reasons"]
    assert "acceptance_disallows_allow_no_code_delta" in invalid["reasons"]
    assert "acceptance_disallows_skip_outbox" in invalid["reasons"]
    assert "acceptance_requires_timeout_profile_realistic" in invalid["reasons"]
    assert "acceptance_requires_timeout_gte_30" in invalid["reasons"]
    assert "acceptance_requires_poll_timeout_gte_25" in invalid["reasons"]
    assert "acceptance_requires_trace_timeout_gte_25" in invalid["reasons"]


def test_quality_constant_dev_lane_disallows_baseline_update_only():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_quality_constant_status"]

    allowed = build(
        mode="block",
        lane="dev",
        scenarios_file=None,
        run_mode="llm",
        count=3,
        include_media=False,
        scenario_coverage="booking",
        judge_mode="off",
        run_economy_gate="warn",
        manual_audit_gate="warn",
        tool_evidence_policy="auto",
        fail_on_thresholds=False,
        fail_on_regression=False,
        allow_weak_oracle=True,
        allow_incomplete_run_artifacts=True,
        allow_judge_off=True,
        allow_no_code_delta=True,
        skip_outbox=True,
        update_baseline=False,
        timeout_profile="fast-replay",
        timeout=12,
        poll_timeout=10,
        trace_timeout=10,
    )
    assert allowed["valid"] is True
    assert allowed["reasons"] == []
    assert allowed["lane_effective"] == "dev"

    blocked = build(
        mode="block",
        lane="dev",
        scenarios_file=None,
        run_mode="llm",
        count=3,
        include_media=False,
        scenario_coverage="booking",
        judge_mode="off",
        run_economy_gate="warn",
        manual_audit_gate="warn",
        tool_evidence_policy="auto",
        fail_on_thresholds=False,
        fail_on_regression=False,
        allow_weak_oracle=True,
        allow_incomplete_run_artifacts=True,
        allow_judge_off=True,
        allow_no_code_delta=True,
        skip_outbox=True,
        update_baseline=True,
        timeout_profile="fast-replay",
        timeout=12,
        poll_timeout=10,
        trace_timeout=10,
    )
    assert blocked["valid"] is False
    assert blocked["reasons"] == ["dev_lane_disallows_update_baseline"]


def test_quality_constant_acceptance_requires_zero_semantic_override_budgets():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_quality_constant_status"]

    status = build(
        mode="block",
        lane="acceptance",
        scenarios_file="/tmp/booking_quality/lock/scenarios.json",
        run_mode="llm",
        count=10,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
        judge_mode="all",
        run_economy_gate="block",
        manual_audit_gate="block",
        tool_evidence_policy="strict",
        fail_on_thresholds=True,
        fail_on_regression=True,
        allow_weak_oracle=False,
        allow_incomplete_run_artifacts=False,
        allow_judge_off=False,
        allow_no_code_delta=False,
        skip_outbox=False,
        update_baseline=False,
        timeout_profile="realistic",
        timeout=30,
        poll_timeout=25,
        trace_timeout=25,
        max_post_llm_semantic_rewrite_rate=0.02,
        max_keyword_override_rate=0.1,
    )

    assert status["valid"] is False
    assert "acceptance_requires_max_post_llm_semantic_rewrite_rate_zero" in status["reasons"]
    assert "acceptance_requires_max_keyword_override_rate_zero" in status["reasons"]


def test_quality_constant_acceptance_allows_non_canonical_lock_retry_for_lock_only():
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_quality_constant_status"]

    lock_mode = build(
        mode="block",
        lane="acceptance",
        scenarios_file=None,
        run_mode="llm",
        count=10,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
        judge_mode="all",
        run_economy_gate="block",
        manual_audit_gate="block",
        tool_evidence_policy="strict",
        fail_on_thresholds=True,
        fail_on_regression=False,
        allow_weak_oracle=False,
        allow_incomplete_run_artifacts=False,
        allow_judge_off=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        skip_outbox=False,
        update_baseline=False,
        timeout_profile="realistic",
        timeout=30,
        poll_timeout=25,
        trace_timeout=25,
    )
    assert lock_mode["valid"] is True
    assert "acceptance_non_canonical_lock_retry_requires_lock_mode" not in lock_mode["reasons"]

    replay_mode = build(
        mode="block",
        lane="acceptance",
        scenarios_file="/tmp/booking_quality/lock/scenarios.json",
        run_mode="llm",
        count=10,
        include_media=True,
        scenario_coverage="booking,info,interrupt,handoff",
        judge_mode="all",
        run_economy_gate="block",
        manual_audit_gate="block",
        tool_evidence_policy="strict",
        fail_on_thresholds=True,
        fail_on_regression=True,
        allow_weak_oracle=False,
        allow_incomplete_run_artifacts=False,
        allow_judge_off=False,
        allow_no_code_delta=False,
        allow_non_canonical_lock_retry=True,
        skip_outbox=False,
        update_baseline=False,
        timeout_profile="realistic",
        timeout=30,
        poll_timeout=25,
        trace_timeout=25,
    )
    assert replay_mode["valid"] is False
    assert "acceptance_non_canonical_lock_retry_requires_lock_mode" in replay_mode["reasons"]


def test_cross_domain_matrix_contract_accepts_two_non_salon_slugs():
    ns = _load_quality_helpers()
    build_contract = ns["_llm_quality_build_cross_domain_matrix_contract_status"]

    status = build_contract(
        mode="block",
        client_slugs=["demo_salon", "clinic_pack", "dental_pack"],
        excluded_slugs=["demo_salon", "generic"],
        min_non_salon=2,
    )

    assert status["valid"] is True
    assert status["required"] is True
    assert status["non_salon_count"] == 2
    assert status["reasons"] == []


def test_cross_domain_matrix_contract_blocks_when_non_salon_under_minimum():
    ns = _load_quality_helpers()
    build_contract = ns["_llm_quality_build_cross_domain_matrix_contract_status"]

    status = build_contract(
        mode="block",
        client_slugs=["demo_salon", "generic"],
        excluded_slugs=["demo_salon", "generic"],
        min_non_salon=2,
    )

    assert status["valid"] is False
    assert status["required"] is True
    assert status["reasons"] == ["cross_domain_non_salon_lt_2:0"]


def test_cross_domain_matrix_contract_warn_mode_is_non_blocking():
    ns = _load_quality_helpers()
    build_contract = ns["_llm_quality_build_cross_domain_matrix_contract_status"]

    status = build_contract(
        mode="warn",
        client_slugs=["demo_salon"],
        excluded_slugs=["demo_salon", "generic"],
        min_non_salon=2,
    )

    assert status["enforced"] is True
    assert status["required"] is False
    assert status["valid"] is False
    assert status["reasons"] == ["cross_domain_non_salon_lt_2:0"]


def test_cross_domain_matrix_slug_normalization_is_casefold_dedup():
    ns = _load_quality_helpers()
    normalize = ns["_llm_quality_normalize_matrix_client_slugs"]

    slugs = normalize("demo_salon,Clinic_Pack,clinic_pack,dental_pack")

    assert slugs == ["demo_salon", "Clinic_Pack", "dental_pack"]


def test_workaround_register_gate_blocks_unregistered_marker(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_workaround_register_status"]

    source_file = tmp_path / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    source_file.parent.mkdir(parents=True)
    marker = "WORKAROUND" "_ID: WA-001"
    source_file.write_text(
        f"if True:\n    pass  # {marker}\n",
        encoding="utf-8",
    )
    register_dir = tmp_path / "docs"
    register_dir.mkdir()
    (register_dir / "WORKAROUND_REGISTER.json").write_text(
        json.dumps({"workarounds": [{"id": "WA-999"}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status = build_gate(
        mode="block",
        repo_root=str(tmp_path),
        base_ref="origin/main",
        register_path="docs/WORKAROUND_REGISTER.json",
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
    )

    assert status["valid"] is False
    assert status["marker_count"] == 1
    assert status["marker_ids"] == ["WA-001"]
    assert "workaround_id_unregistered:WA-001" in status["reasons"]


def test_workaround_register_gate_accepts_registered_marker(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_workaround_register_status"]

    source_file = tmp_path / "ops" / "diagnose.py"
    source_file.parent.mkdir(parents=True)
    marker = "WORKAROUND" "_ID: WA-200"
    source_file.write_text(
        f"# {marker}\nprint(\"ok\")\n",
        encoding="utf-8",
    )
    register_dir = tmp_path / "docs"
    register_dir.mkdir()
    (register_dir / "WORKAROUND_REGISTER.json").write_text(
        json.dumps(
            {
                "workarounds": [
                    {
                        "id": "WA-200",
                        "owner": "a1",
                        "status": "active",
                        "remove_when": "root cause fixed",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status = build_gate(
        mode="block",
        repo_root=str(tmp_path),
        base_ref="origin/main",
        register_path="docs/WORKAROUND_REGISTER.json",
        changed_files=["ops/diagnose.py"],
    )

    assert status["valid"] is True
    assert status["reasons"] == []
    assert status["missing_ids"] == []
    assert status["marker_ids"] == ["WA-200"]


def test_replay_command_forces_unique_jid_and_reset():
    ns = _load_quality_helpers()
    build_replay_command = ns["_llm_quality_build_replay_command"]
    args = SimpleNamespace(
        base_url="http://localhost:8000",
        client_slug="demo_salon",
        timeout_profile="realistic",
        timeout=30.0,
        poll_timeout=20.0,
        poll_interval=0.5,
        trace_timeout=15.0,
        trace_interval=0.5,
        min_wait=0.1,
        max_wait=0.2,
        manager_mode="simulate",
        pending_mode="ack",
        tool_hooks="auto",
        branch_slug=None,
        remote_jid=None,
        allow_non_allowlist=False,
        skip_outbox=False,
        reset_before_dialog=False,
        max_failures=0,
    )

    command = build_replay_command(args, "/tmp/booking_quality/run/scenarios.json", 10)
    parts = shlex.split(command.replace("TEST_MODE=1 ", "", 1))

    assert "--jid-mode" in parts
    assert parts[parts.index("--jid-mode") + 1] == "unique"
    assert "--reset-before-dialog" in parts
    assert "--allow-non-allowlist" in parts


def test_replay_command_skips_allow_non_allowlist_when_skip_outbox():
    ns = _load_quality_helpers()
    build_replay_command = ns["_llm_quality_build_replay_command"]
    args = SimpleNamespace(
        base_url="http://localhost:8000",
        client_slug="demo_salon",
        timeout_profile="realistic",
        timeout=30.0,
        poll_timeout=20.0,
        poll_interval=0.5,
        trace_timeout=15.0,
        trace_interval=0.5,
        min_wait=0.1,
        max_wait=0.2,
        manager_mode="simulate",
        pending_mode="ack",
        tool_hooks="auto",
        branch_slug=None,
        remote_jid=None,
        allow_non_allowlist=False,
        skip_outbox=True,
        reset_before_dialog=True,
        max_failures=0,
    )

    command = build_replay_command(args, "/tmp/booking_quality/run/scenarios.json", 10)
    parts = shlex.split(command.replace("TEST_MODE=1 ", "", 1))

    assert "--jid-mode" in parts
    assert parts[parts.index("--jid-mode") + 1] == "unique"
    assert "--reset-before-dialog" in parts
    assert "--skip-outbox" in parts
    assert "--allow-non-allowlist" not in parts


def test_validate_scenario_artifacts_blocks_missing_summary_and_brief(tmp_path):
    ns = _load_quality_helpers()
    validate = ns["_llm_quality_validate_scenario_artifacts"]
    scenario_file = tmp_path / "scenarios.json"
    scenario_file.write_text("{}", encoding="utf-8")

    try:
        validate(str(scenario_file), allow_incomplete=False)
    except SystemExit as exc:
        assert "incomplete scenarios-file artifacts" in str(exc)
    else:
        raise AssertionError("expected SystemExit for incomplete artifacts")

    status = validate(str(scenario_file), allow_incomplete=True)
    assert status["checked"] is True
    assert status["valid"] is False
    assert "summary.json" in status["missing"]
    assert "brief.md" in status["missing"]


def test_run_integrity_status_detects_completion_and_trace_gaps():
    ns = _load_quality_helpers()
    build_status = ns["_llm_quality_build_run_integrity_status"]

    status = build_status(
        dialogs=[
            {"turns": [{"text": "1"}, {"text": "2"}]},
            {"turns": [{"text": "3"}]},
        ],
        stats={"turns": 2, "trace_rows_written": 1},
    )

    assert status["valid"] is False
    assert status["expected_turns"] == 3
    assert status["responses_turns"] == 2
    assert status["trace_rows_written"] == 1
    assert "run_completion_gap" in status["reasons"]
    assert "trace_response_mismatch" in status["reasons"]


def test_run_integrity_status_is_valid_when_counts_match():
    ns = _load_quality_helpers()
    build_status = ns["_llm_quality_build_run_integrity_status"]

    status = build_status(
        dialogs=[{"turns": [{"text": "1"}, {"text": "2"}]}],
        stats={"turns": 2, "trace_rows_written": 2},
    )

    assert status["valid"] is True
    assert status["reasons"] == []
    assert status["missing_turns"] == 0
    assert status["trace_response_delta"] == 0


def test_lexicon_regex_delta_gate_requires_resolver_and_tests():
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_lexicon_regex_delta_status"]

    invalid = build_gate(
        mode="block",
        repo_root="/tmp/repo",
        base_ref="origin/main",
        changed_files=["truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml"],
    )
    assert invalid["valid"] is False
    assert "resolver_delta_missing" in invalid["reasons"]
    assert "contract_test_delta_missing" in invalid["reasons"]

    valid = build_gate(
        mode="block",
        repo_root="/tmp/repo",
        base_ref="origin/main",
        changed_files=[
            "truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml",
            "truffles-api/app/routers/webhook/decision.py",
            "truffles-api/tests/test_message_endpoint.py",
        ],
    )
    assert valid["valid"] is True


def test_line_has_phrase_branching_detects_raw_message_text_branch():
    ns = _load_quality_helpers()
    detector = ns["_llm_quality_line_has_phrase_branching"]

    assert detector('and "без записи" in _normalize_text(message_text)')
    assert detector('if "как вас зовут" in normalized_prompt_text:')


def test_line_has_phrase_branching_allows_resolver_or_allow_marker():
    ns = _load_quality_helpers()
    detector = ns["_llm_quality_line_has_phrase_branching"]

    assert not detector('if get_signal_lexicon_list(client_slug, "hours_keywords"):')
    assert not detector('if "без записи" in _normalize_text(message_text):  # hardcode-gate: allow')


def test_line_has_phrase_branching_blocks_domain_regex_in_signal_services():
    ns = _load_quality_helpers()
    detector = ns["_llm_quality_line_has_phrase_branching"]

    assert detector(
        '(re.compile(r"\\bпослезавтраш\\w*|\\bпослезавтра\\b", re.IGNORECASE), "послезавтра"),',
        path="truffles-api/app/services/booking_signal_service.py",
    )


def test_line_has_phrase_branching_allows_technical_format_regex_in_signal_services():
    ns = _load_quality_helpers()
    detector = ns["_llm_quality_line_has_phrase_branching"]

    assert not detector(
        'if re.search(r"\\d{4}-\\d{2}-\\d{2}", token):',
        path="truffles-api/app/services/booking_signal_service.py",
    )


def test_hardcode_core_gate_blocks_phrase_branching_in_core_diff():
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_hardcode_core_gate_status"]
    ns["_llm_quality_collect_hardcode_core_violations"] = (
        lambda **_kwargs: (
            [
                {
                    "path": "truffles-api/app/routers/webhook/decision.py",
                    "source": "worktree_diff",
                    "line": 'and "без записи" in _normalize_text(message_text)',
                }
            ],
            [],
        )
    )

    status = build_gate(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        changed_files=["truffles-api/app/routers/webhook/decision.py"],
    )

    assert status["valid"] is False
    assert status["enforced"] is True
    assert status["reasons"] == ["core_phrase_branching_detected"]
    assert status["core_changed_files"] == ["truffles-api/app/routers/webhook/decision.py"]
    assert status["violations"]


def test_hardcode_core_gate_ignores_non_core_changes():
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_hardcode_core_gate_status"]

    status = build_gate(
        mode="block",
        repo_root=".",
        base_ref="origin/main",
        changed_files=["docs/REPORTS/sample.md"],
    )

    assert status["valid"] is True
    assert status["reasons"] == []
    assert status["core_changed_files"] == []
    assert status["violations"] == []


def test_hardcode_core_gate_scopes_signal_services():
    ns = _load_quality_helpers()
    core_paths = set(ns["LLM_QUALITY_HARDCODE_CORE_PREFIXES"])

    assert "truffles-api/app/services/booking_signal_service.py" in core_paths
    assert "truffles-api/app/services/info_signal_service.py" in core_paths


def test_hardcode_core_scope_includes_webhook_and_runtime_signal_files():
    ns = _load_quality_helpers()
    is_scope_file = ns["_llm_quality_is_hardcode_core_file"]

    assert is_scope_file("truffles-api/app/routers/webhook/policy.py")
    assert is_scope_file("truffles-api/app/services/booking_signal_service.py")
    assert is_scope_file("truffles-api/app/services/any_runtime_service.py")
    assert is_scope_file("truffles-api/app/services/pack_runtime_service.py")
    assert not is_scope_file("docs/REPORTS/sample.md")


def test_hq1_classifier_detects_handoff_miss():
    ns = _load_quality_helpers()
    classify = ns["_llm_quality_collect_hq1_classes"]

    record = {
        "turn_text": "Я хочу изменить время записи.",
        "turn_tags": ["reschedule", "booking"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "check_booking",
            "tool_action": "calendar.reschedule",
            "tool_decision": "missing_slot",
        },
        "turn_expectations": {"action": "handoff", "info_sections": []},
        "evaluation": {"strict_reasons": ["expected_action_mismatch"]},
        "judge": None,
        "outbox_text": "Уточните, пожалуйста, новое время.",
    }

    assert classify(record) == ["handoff_miss"]


def test_hq1_classifier_ignores_check_booking_confirmation_without_handoff_signal():
    ns = _load_quality_helpers()
    classify = ns["_llm_quality_collect_hq1_classes"]

    record = {
        "turn_text": "Подтвердите, пожалуйста, запись на стрижку.",
        "turn_tags": ["check_booking"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "calendar.get_booking",
            "tool_action": "calendar.get_booking",
            "tool_decision": "not_found",
        },
        "turn_expectations": {"action": None, "info_sections": []},
        "evaluation": {"strict_reasons": []},
        "judge": None,
        "outbox_text": "Не нашел активной записи, подскажите время и имя.",
    }

    assert "handoff_miss" not in classify(record)


def test_booking_progress_expectation_ignores_book_slot_conflict():
    ns = _load_quality_helpers()
    should_expect_progress = ns["_llm_quality_should_expect_booking_progress"]

    assert (
        should_expect_progress(
            "time",
            ["time"],
            {
                "intent": "calendar.book_slot",
                "tool_decision": "conflict",
            },
        )
        is False
    )
    assert (
        should_expect_progress(
            "time",
            ["time"],
            {
                "intent": "calendar.book_slot",
                "tool_decision": "ok",
            },
        )
        is True
    )


def test_hq1_classifier_detects_wrong_action_and_non_actionable_reply():
    ns = _load_quality_helpers()
    classify = ns["_llm_quality_collect_hq1_classes"]

    wrong_action_record = {
        "turn_text": "У вас есть мастера, которые работают с долгими стрижками?",
        "turn_tags": ["master"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "catalog.location",
            "tool_action": "catalog.location",
            "tool_decision": "ok",
        },
        "turn_expectations": {"action": None, "info_sections": ["master", "specialist"]},
        "evaluation": {"strict_reasons": ["expected_info_section_miss"]},
        "judge": None,
        "outbox_text": "Адрес и часы работы салона...",
    }
    classes = classify(wrong_action_record)
    assert "wrong_action" in classes

    non_actionable_record = {
        "turn_text": "Какой у вас ассортимент услуг?",
        "turn_tags": ["info"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "contract_invalid",
        },
        "turn_expectations": {"action": None, "info_sections": []},
        "evaluation": {"strict_reasons": ["judge_fail"]},
        "judge": {"verdict": "fail", "reasons": ["non_actionable_reply"]},
        "outbox_text": "Не удалось подтвердить действие автоматически. Уточните, пожалуйста, детали.",
    }
    classes = classify(non_actionable_record)
    assert "non_actionable_reply" in classes


def test_hq1_classifier_detects_booking_flow_break_and_hallucinated_fact():
    ns = _load_quality_helpers()
    classify = ns["_llm_quality_collect_hq1_classes"]

    booking_flow_record = {
        "turn_text": "Можно на 17:45?",
        "turn_tags": ["booking", "time_alt"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "conflict",
        },
        "turn_expectations": {"action": None, "info_sections": []},
        "evaluation": {"strict_reasons": ["expected_reply_type_mismatch"]},
        "judge": None,
        "outbox_text": "На 17:45 свободного окна нет. Доступны: 12:00, 13:00, 17:00.",
    }
    classes = classify(booking_flow_record)
    assert "booking_flow_break" in classes

    hallucinated_record = {
        "turn_text": "Сколько стоит маникюр?",
        "turn_tags": ["price"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "price_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "ok",
        },
        "turn_expectations": {"action": None, "info_sections": ["price"]},
        "evaluation": {"strict_reasons": ["judge_fail"]},
        "judge": {
            "verdict": "fail",
            "reasons": ["hallucination_fact"],
            "summary": "Ответ содержит выдуманные факты.",
        },
        "outbox_text": "Маникюр стоит 99999 тенге и включает подарок.",
    }
    classes = classify(hallucinated_record)
    assert "hallucinated_fact" in classes


def test_hq1_classifier_ignores_media_turn_for_booking_flow_break():
    ns = _load_quality_helpers()
    classify = ns["_llm_quality_collect_hq1_classes"]

    record = {
        "turn_text": "Я могу прислать фото, если нужно.",
        "turn_tags": ["media"],
        "conversation_state": "bot_active",
        "decision_meta": {
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "ok",
        },
        "turn_expectations": {"action": None, "info_sections": []},
        "evaluation": {"strict_reasons": ["judge_fail"]},
        "judge": {"verdict": "fail", "reasons": ["missed_question"]},
        "outbox_text": "Понял, завтра по услуге «Стрижка». Подскажите, пожалуйста, точное время.",
    }

    assert "booking_flow_break" not in classify(record)


def test_judge_fail_promotion_requires_semantic_contract_reason():
    ns = _load_quality_helpers()
    should_promote = ns["_llm_quality_should_promote_judge_fail"]

    assert (
        should_promote(
            judge_result={"verdict": "fail", "reasons": ["wrong_action"]},
            strict_reasons=["expected_action_mismatch"],
        )
        is True
    )


def test_judge_fail_not_promoted_on_delivery_waiver_only():
    ns = _load_quality_helpers()
    should_promote = ns["_llm_quality_should_promote_judge_fail"]

    assert (
        should_promote(
            judge_result={"verdict": "fail", "reasons": ["billing_block"]},
            strict_reasons=["delivery_waiver_billing"],
        )
        is False
    )


def test_human_semantic_strict_reasons_promote_required_info_miss():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_human_semantic_strict_reasons"]

    reasons = collect(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        meta={"action": "fact", "intent": "pricing", "tool_action": "catalog.service_query"},
        turn_tags=["price"],
        expected_info_sections=["pricing", "price"],
        actual_info_sections=["promotions"],
        actual_info_intents=["pricing"],
        expected_reply_type="time",
        actual_expected_reply_type="time",
    )

    assert "human_semantic_required_info_miss" in reasons


def test_human_semantic_strict_reasons_promote_media_consult_miss():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_human_semantic_strict_reasons"]

    reasons = collect(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        meta={"action": "collect", "intent": "consult", "tool_action": "collect"},
        turn_tags=["media"],
        expected_info_sections=[],
        actual_info_sections=[],
        actual_info_intents=[],
        expected_reply_type=None,
        actual_expected_reply_type=None,
    )

    assert reasons == ["human_semantic_media_cue_miss"]


def test_human_semantic_strict_reasons_promote_check_booking_recovery_miss():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_human_semantic_strict_reasons"]

    reasons = collect(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        meta={"action": "fact", "intent": "check_booking", "tool_action": "calendar.get_booking"},
        turn_tags=["confirm"],
        expected_info_sections=[],
        actual_info_sections=[],
        actual_info_intents=[],
        expected_reply_type="time",
        actual_expected_reply_type="name",
    )

    assert reasons == ["human_semantic_check_booking_recovery_miss"]


def test_collect_blocking_reasons_merges_hq1_counts():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_blocking_reasons"]
    result = collect(
        {"expected_reply_type_mismatch": 1},
        extra_counts={"handoff_miss": 2, "booking_flow_break": 1},
    )
    assert result["count"] == 4
    assert result["reasons"]["handoff_miss"] == 2
    assert result["reasons"]["booking_flow_break"] == 1


def test_collect_blocking_reasons_includes_unobserved_turn():
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_blocking_reasons"]

    result = collect({"unobserved_turn": 2}, extra_counts={})

    assert result["count"] == 2
    assert result["reasons"]["unobserved_turn"] == 2


def test_manifest_mode_detects_canary_from_run_id():
    ns = _load_quality_helpers()
    resolve_mode = ns["_llm_quality_manifest_mode"]

    mode, source = resolve_mode(None, "booking-canary-contract-a1", {})
    assert mode == "canary"
    assert source == "run_id"


def test_artifact_integrity_marks_missing_required_run_artifacts(tmp_path):
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_artifact_integrity"]
    required = set(ns["LLM_QUALITY_REQUIRED_RUN_ARTIFACTS"])

    status = collect(str(tmp_path))

    assert status["valid"] is False
    assert set(status["required"]) == required
    assert set(status["missing"]) == required


def test_artifact_integrity_marks_valid_when_required_run_artifacts_exist(tmp_path):
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_artifact_integrity"]
    required = ns["LLM_QUALITY_REQUIRED_RUN_ARTIFACTS"]

    for name in required:
        (tmp_path / name).write_text("ok\n", encoding="utf-8")

    status = collect(str(tmp_path))

    assert status["valid"] is True
    assert status["missing"] == []
    assert sorted(status["required"]) == sorted(required)


def test_evidence_handoff_status_accepts_complete_bundle_with_done_manual_audit(tmp_path):
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_evidence_handoff_status"]

    run_dir = tmp_path / "run-complete"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_manual_audit_aux_artifacts(run_dir)
    for artifact in (
        "summary.json",
        "brief.md",
        "scenarios.json",
        "responses.jsonl",
        "trace_bundle.jsonl",
        "run_manifest.json",
        "manual_audit.md",
    ):
        (run_dir / artifact).write_text("{}", encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-complete",
                "quality_status": {"manual_audit_required": True},
                "manual_audit": {
                    "status": "done",
                    "path": str(run_dir / "manual_audit.md"),
                    "json_path": str(run_dir / "manual_audit.json"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(_done_manual_audit_payload(run_dir, "run-complete"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status = collect(output_dir=str(run_dir), summary={"run_id": "run-complete"})
    assert status["valid"] is True
    assert status["reasons"] == []
    assert status["manual_audit_done"] is True
    assert status["missing"] == []


def test_evidence_handoff_status_blocks_on_missing_manifest_and_pending_audit(tmp_path):
    ns = _load_quality_helpers()
    collect = ns["_llm_quality_collect_evidence_handoff_status"]

    run_dir = tmp_path / "run-missing"
    run_dir.mkdir(parents=True, exist_ok=True)
    for artifact in (
        "summary.json",
        "brief.md",
        "scenarios.json",
        "responses.jsonl",
        "trace_bundle.jsonl",
        "manual_audit.md",
    ):
        (run_dir / artifact).write_text("{}", encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-missing",
                "quality_status": {"manual_audit_required": True},
                "manual_audit": {
                    "status": "pending",
                    "path": str(run_dir / "manual_audit.md"),
                    "json_path": str(run_dir / "manual_audit.json"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(
            {
                "status": "pending",
                "run_id": "run-missing",
                "audited_at": datetime.now(timezone.utc).isoformat(),
                "finding_count": 1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status = collect(output_dir=str(run_dir), summary={"run_id": "run-missing"})
    assert status["valid"] is False
    assert "manual_audit_not_done" in status["reasons"]
    assert any(
        reason.startswith("evidence_artifacts_missing:") for reason in status["reasons"]
    )


def test_governance_closure_status_valid_for_complete_runtime_evidence(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_governance_closure_status"]

    run_dir = tmp_path / "run-governance-ok"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_manual_audit_aux_artifacts(run_dir)
    for artifact in (
        "summary.json",
        "brief.md",
        "scenarios.json",
        "responses.jsonl",
        "trace_bundle.jsonl",
        "run_manifest.json",
        "manual_audit.md",
    ):
        (run_dir / artifact).write_text("{}", encoding="utf-8")

    summary = {
        "run_id": "run-governance-ok",
        "infra_valid": True,
        "semantic_valid": True,
        "manual_audit": {
            "status": "done",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_required": True,
            "manual_audit_status": "done",
        },
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(_done_manual_audit_payload(run_dir, "run-governance-ok"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status = build(output_dir=str(run_dir), summary=summary)
    assert status["valid"] is True
    assert status["enforced"] is True
    assert status["reasons"] == []
    assert status["checks"]["manual_audit_done"] is True
    assert status["evidence_paths"]["run_manifest"] == str(run_dir / "run_manifest.json")


def test_governance_closure_status_invalid_for_incomplete_evidence(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_governance_closure_status"]

    run_dir = tmp_path / "run-governance-bad"
    run_dir.mkdir(parents=True, exist_ok=True)
    for artifact in (
        "summary.json",
        "brief.md",
        "scenarios.json",
        "responses.jsonl",
        "manual_audit.md",
    ):
        (run_dir / artifact).write_text("{}", encoding="utf-8")

    summary = {
        "run_id": "run-governance-bad",
        "infra_valid": True,
        "semantic_valid": True,
        "manual_audit": {
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_required": True,
            "manual_audit_status": "pending",
        },
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(
            {
                "status": "pending",
                "run_id": "run-governance-bad",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status = build(output_dir=str(run_dir), summary=summary)
    assert status["valid"] is False
    assert "manual_audit_not_done" in status["reasons"]
    assert "artifact_integrity_invalid_or_missing" in status["reasons"]
    assert "evidence_handoff_invalid_or_missing" in status["reasons"]
    assert status["checks"]["manual_audit_done"] is False


def test_open_world_profile_status_requires_all_profiles(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_open_world_profile_status"]

    scenarios_path = tmp_path / "scenarios-ru.json"
    scenarios_path.write_text(
        json.dumps(
            {
                "language_profile": "ru",
                "semantic_variation_profile": "canonical",
                "slot_format_profile": "canonical",
                "surface_noise_profile": "clean",
                "dialogs": [
                    {
                        "dialog_id": "d1",
                        "language_profile": "ru",
                        "semantic_variation_profile": "canonical",
                        "slot_format_profile": "canonical",
                        "surface_noise_profile": "clean",
                        "turns": [{"text": "test"}],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status = build(scenario_paths=[str(scenarios_path)])

    assert status["valid"] is False
    assert "language_profiles_missing:kk,mixed,mixed_translit" in status["reasons"]
    assert "surface_noise_profiles_missing:typo" in status["reasons"]
    assert "semantic_variation_profiles_missing:synonym" in status["reasons"]
    assert "slot_format_profiles_missing:variant" in status["reasons"]


def test_p6_acceptance_closure_status_valid_for_complete_proof_bundle(tmp_path):
    ns = _load_quality_helpers()
    build = ns["_llm_quality_build_p6_acceptance_closure_status"]

    deterministic_profiles = [
        ("ru", "canonical", "canonical", "clean"),
        ("kk", "canonical", "canonical", "clean"),
        ("mixed", "synonym", "variant", "typo"),
        ("mixed_translit", "synonym", "variant", "typo"),
    ]
    deterministic_paths = []
    for index, (language, semantic, slot_format, surface_noise) in enumerate(
        deterministic_profiles,
        start=1,
    ):
        path = tmp_path / f"deterministic-{index}.json"
        path.write_text(
            json.dumps(
                {
                    "language_profile": language,
                    "semantic_variation_profile": semantic,
                    "slot_format_profile": slot_format,
                    "surface_noise_profile": surface_noise,
                    "dialogs": [
                        {
                            "dialog_id": f"d{index}",
                            "language_profile": language,
                            "semantic_variation_profile": semantic,
                            "slot_format_profile": slot_format,
                            "surface_noise_profile": surface_noise,
                            "turns": [{"text": f"turn-{index}"}],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        deterministic_paths.append(str(path))

    child_rows = []
    for index, (client_slug, branch_slug, seed) in enumerate(
        (("demo_salon", "branch-a", 42), ("dental_pack", "branch-b", 1337)),
        start=1,
    ):
        child_dir = tmp_path / f"child-{index}"
        child_dir.mkdir(parents=True, exist_ok=True)
        child_summary_path = child_dir / "summary.json"
        child_summary_path.write_text(
            json.dumps(
                {
                    "config": {"seed": seed},
                    "judge": {"enabled": True},
                    "metrics": {
                        "rates": {
                            "fact_without_evidence_rate": 0.0,
                            "irrelevant_fact_rate": 0.0,
                            "booking_commit_without_required_contact": 0.0,
                            "semantic_override_rate": 0.0,
                            "stale_state_leak_rate": 0.0,
                        }
                    },
                    "quality_constant": {"lane_effective": "dev"},
                    "quality_status": {
                        "blocking_reason_count": 0,
                        "threshold_breaches": [],
                        "run_integrity_valid": True,
                        "fact_without_evidence_rate": 0.0,
                        "irrelevant_fact_rate": 0.0,
                        "booking_commit_without_required_contact": 0.0,
                        "semantic_override_rate": 0.0,
                        "stale_state_leak_rate": 0.0,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        child_rows.append(
            {
                "client_slug": client_slug,
                "branch_slug": branch_slug,
                "run_id": f"matrix-row-{index}",
                "status": "ok",
                "infra_valid": True,
                "semantic_valid": True,
                "scenario_context_valid": True,
                "summary": str(child_summary_path),
            }
        )

    matrix_summary_path = tmp_path / "matrix_summary.json"
    matrix_summary_path.write_text(
        json.dumps(
            {
                "all_ok": True,
                "cross_domain_contract": {"required": True, "valid": True},
                "failure_families": {"family_count": 0, "families": []},
                "rows": child_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status = build(
        matrix_summary_paths=[str(matrix_summary_path)],
        deterministic_scenario_paths=deterministic_paths,
    )

    assert status["valid"] is True
    assert status["reasons"] == []
    assert status["matrix"]["row_count"] == 2
    assert status["matrix"]["distinct_clients"] == ["demo_salon", "dental_pack"]
    assert status["matrix"]["distinct_seeds"] == ["1337", "42"]


def test_llm_quality_open_world_closure_command_blocks_on_missing_profiles(tmp_path):
    deterministic_path = tmp_path / "deterministic-ru.json"
    deterministic_path.write_text(
        json.dumps(
            {
                "language_profile": "ru",
                "semantic_variation_profile": "canonical",
                "slot_format_profile": "canonical",
                "surface_noise_profile": "clean",
                "dialogs": [
                    {
                        "dialog_id": "ru-only",
                        "language_profile": "ru",
                        "semantic_variation_profile": "canonical",
                        "slot_format_profile": "canonical",
                        "surface_noise_profile": "clean",
                        "turns": [{"text": "test"}],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    child_dir = tmp_path / "child"
    child_dir.mkdir(parents=True, exist_ok=True)
    child_summary_path = child_dir / "summary.json"
    child_summary_path.write_text(
        json.dumps(
            {
                "config": {"seed": 42},
                "judge": {"enabled": True},
                "quality_status": {
                    "blocking_reason_count": 0,
                    "threshold_breaches": [],
                    "run_integrity_valid": True,
                    "fact_without_evidence_rate": 0.0,
                    "irrelevant_fact_rate": 0.0,
                    "booking_commit_without_required_contact": 0.0,
                    "semantic_override_rate": 0.0,
                    "stale_state_leak_rate": 0.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    matrix_summary_path = tmp_path / "matrix_summary.json"
    matrix_summary_path.write_text(
        json.dumps(
            {
                "all_ok": True,
                "cross_domain_contract": {"required": True, "valid": True},
                "failure_families": {"family_count": 0, "families": []},
                "rows": [
                    {
                        "client_slug": "demo_salon",
                        "branch_slug": "branch-a",
                        "run_id": "matrix-row-1",
                        "status": "ok",
                        "infra_valid": True,
                        "semantic_valid": True,
                        "scenario_context_valid": True,
                        "summary": str(child_summary_path),
                    },
                    {
                        "client_slug": "dental_pack",
                        "branch_slug": "branch-b",
                        "run_id": "matrix-row-2",
                        "status": "ok",
                        "infra_valid": True,
                        "semantic_valid": True,
                        "scenario_context_valid": True,
                        "summary": str(child_summary_path),
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "python3",
            "ops/diagnose.py",
            "llm-quality-open-world-closure",
            "--matrix-summary",
            str(matrix_summary_path),
            "--deterministic-scenarios",
            str(deterministic_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["command"] == "llm-quality-open-world-closure"
    assert payload["valid"] is False
    assert "language_profiles_missing:kk,mixed,mixed_translit" in payload["reasons"]


def test_manual_audit_gate_blocks_when_latest_run_is_pending(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_manual_audit_gate_status"]

    run_dir = tmp_path / "run-pending"
    run_dir.mkdir()
    summary = {
        "run_id": "run-pending",
        "quality_status": {"manual_audit_required": True},
        "manual_audit": {
            "required": True,
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    gate = build_gate(mode="block", output_dir=str(tmp_path / "run-next"))

    assert gate["valid"] is False
    assert gate["reasons"] == ["manual_audit_pending:run-pending"]
    assert gate["pending_run"]["run_id"] == "run-pending"


def test_manual_audit_gate_passes_when_pending_run_has_done_audit(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_manual_audit_gate_status"]

    run_dir = tmp_path / "run-audited"
    run_dir.mkdir()
    _write_manual_audit_aux_artifacts(run_dir)
    summary = {
        "run_id": "run-audited",
        "quality_status": {"manual_audit_required": True},
        "manual_audit": {
            "required": True,
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(_done_manual_audit_payload(run_dir, "run-audited"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    gate = build_gate(mode="block", output_dir=str(tmp_path / "run-next"))

    assert gate["valid"] is True
    assert gate["reasons"] == []
    assert gate["pending_run"] is None


def test_manual_audit_sync_updates_summary_and_quality_status(tmp_path):
    ns = _load_quality_helpers()
    sync_summary = ns["_llm_quality_sync_manual_audit_summary"]

    run_dir = tmp_path / "run-audit-sync"
    run_dir.mkdir()
    _write_manual_audit_aux_artifacts(run_dir)
    summary_path = run_dir / "summary.json"
    summary_payload = {
        "run_id": "run-audit-sync",
        "brief_path": str(run_dir / "brief.md"),
        "manual_audit": {
            "required": True,
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
            "command": "python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/run --status done --strict-artifacts",
        },
        "quality_status": {
            "manual_audit_required": True,
            "manual_audit_status": "pending",
            "manual_audit_path": str(run_dir / "manual_audit.md"),
        },
    }
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(_done_manual_audit_payload(run_dir, "run-audit-sync"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    changed = sync_summary(
        run_dir=str(run_dir),
        status="done",
        manual_audit_path=str(run_dir / "manual_audit.md"),
        manual_audit_json_path=str(run_dir / "manual_audit.json"),
    )

    assert changed is True
    updated = json.loads(summary_path.read_text(encoding="utf-8"))
    assert updated["manual_audit"]["status"] == "done"
    assert updated["quality_status"]["manual_audit_status"] == "done"
    assert updated["quality_status"]["manual_audit_path"] == str(run_dir / "manual_audit.md")


def test_manual_audit_sync_refreshes_stale_evidence_handoff(tmp_path):
    ns = _load_quality_helpers()
    sync_summary = ns["_llm_quality_sync_manual_audit_summary"]

    run_dir = tmp_path / "run-audit-refresh"
    run_dir.mkdir()
    _write_manual_audit_aux_artifacts(run_dir)
    summary_path = run_dir / "summary.json"
    for artifact in (
        "brief.md",
        "scenarios.json",
        "responses.jsonl",
        "trace_bundle.jsonl",
        "run_manifest.json",
        "manual_audit.md",
    ):
        (run_dir / artifact).write_text("{}", encoding="utf-8")
    stale_summary = {
        "run_id": "run-audit-refresh",
        "infra_valid": True,
        "semantic_valid": True,
        "run_integrity": {"valid": True, "reasons": []},
        "manual_audit": {
            "required": True,
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
            "command": "python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/run --status done --strict-artifacts",
        },
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_required": True,
            "manual_audit_status": "pending",
            "manual_audit_path": str(run_dir / "manual_audit.md"),
            "evidence_handoff_valid": False,
            "evidence_handoff_reasons": [
                "evidence_artifacts_missing:manual_audit.json,manual_audit.md",
                "manual_audit_not_done",
            ],
        },
        "evidence_handoff": {
            "valid": False,
            "reasons": [
                "evidence_artifacts_missing:manual_audit.json,manual_audit.md",
                "manual_audit_not_done",
            ],
            "missing": ["manual_audit.json", "manual_audit.md"],
        },
    }
    summary_path.write_text(
        json.dumps(stale_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "manual_audit.json").write_text(
        json.dumps(_done_manual_audit_payload(run_dir, "run-audit-refresh"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    changed = sync_summary(
        run_dir=str(run_dir),
        status="done",
        manual_audit_path=str(run_dir / "manual_audit.md"),
        manual_audit_json_path=str(run_dir / "manual_audit.json"),
    )

    assert changed is True
    updated = json.loads(summary_path.read_text(encoding="utf-8"))
    assert updated["manual_audit"]["status"] == "done"
    assert updated["quality_status"]["manual_audit_status"] == "done"
    assert updated["evidence_handoff"]["valid"] is True
    assert updated["evidence_handoff"]["missing"] == []
    assert updated["quality_status"]["evidence_handoff_valid"] is True
    assert updated["quality_status"]["evidence_handoff_reasons"] == []


def test_manual_audit_sync_copies_human_semantic_verdict_into_summary(tmp_path):
    ns = _load_quality_helpers()
    sync_summary = ns["_llm_quality_sync_manual_audit_summary"]

    run_dir = tmp_path / "run-human-semantic-sync"
    run_dir.mkdir()
    _write_manual_audit_aux_artifacts(run_dir)
    summary_path = run_dir / "summary.json"
    summary_payload = {
        "run_id": "run-human-semantic-sync",
        "infra_valid": True,
        "semantic_valid": True,
        "manual_audit": {
            "required": True,
            "status": "pending",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_required": True,
            "manual_audit_status": "pending",
            "manual_audit_path": str(run_dir / "manual_audit.md"),
        },
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "brief.md").write_text("brief", encoding="utf-8")
    (run_dir / "scenarios.json").write_text("{\"dialogs\": []}", encoding="utf-8")
    (run_dir / "responses.jsonl").write_text("", encoding="utf-8")
    (run_dir / "trace_bundle.jsonl").write_text("", encoding="utf-8")
    (run_dir / "run_manifest.json").write_text("{}", encoding="utf-8")
    (run_dir / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_dir,
                "run-human-semantic-sync",
                analyst="a922",
                analyst_root_causes=["oracle_false_green"],
                analyst_next_steps=["strengthen_oracle"],
                oracle_arbitration={
                    "conflict_count": 0,
                    "judge_alignment": "corroborated",
                    "winner": "contract",
                    "resolution_summary": "manual audit completed",
                },
                human_semantic={
                    "valid": False,
                    "summary": "contract-green but human-semantic red",
                },
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    changed = sync_summary(
        run_dir=str(run_dir),
        status="done",
        manual_audit_path=str(run_dir / "manual_audit.md"),
        manual_audit_json_path=str(run_dir / "manual_audit.json"),
    )

    assert changed is True
    updated = json.loads(summary_path.read_text(encoding="utf-8"))
    assert updated["contract_valid"] is True
    assert updated["human_semantic_valid"] is False
    assert updated["human_semantic_summary"] == "contract-green but human-semantic red"
    assert updated["product_quality_valid"] is False
    assert updated["quality_status"]["contract_valid"] is True
    assert updated["quality_status"]["human_semantic_valid"] is False
    assert updated["quality_status"]["human_semantic_summary"] == "contract-green but human-semantic red"
    assert updated["quality_status"]["product_quality_valid"] is False


def _write_run_summary(run_dir, run_id, *, chain_id=None):
    _write_manual_audit_aux_artifacts(run_dir)
    (run_dir / "manual_audit.md").write_text("# audit", encoding="utf-8")
    summary = {
        "run_id": run_id,
        "quality_status": {"manual_audit_required": True},
        "manual_audit": {
            "required": True,
            "status": "done",
            "path": str(run_dir / "manual_audit.md"),
            "json_path": str(run_dir / "manual_audit.json"),
        },
    }
    if chain_id:
        summary["config"] = {"chain_id": chain_id}
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_forensic_sla_gate_blocks_incomplete_manual_audit_payload(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_forensic_sla_gate_status"]

    run_dir = tmp_path / "run-audit-incomplete"
    run_dir.mkdir()
    _write_run_summary(run_dir, "run-audit-incomplete", chain_id="chain-a")
    (run_dir / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_dir,
                "run-audit-incomplete",
                generated_at="2026-02-28T10:00:00Z",
                oracle_arbitration=None,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id="chain-a",
    )

    assert gate["valid"] is False
    assert any(reason.startswith("forensic_sla_invalid:run-audit-incomplete") for reason in gate["reasons"])


def test_oracle_conflict_gate_blocks_when_conflict_winner_is_not_contract(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_oracle_conflict_gate_status"]

    run_dir = tmp_path / "run-oracle-conflict"
    run_dir.mkdir()
    _write_run_summary(run_dir, "run-oracle-conflict", chain_id="chain-a")
    (run_dir / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_dir,
                "run-oracle-conflict",
                generated_at="2026-02-28T10:00:00Z",
                analyst_root_causes=["judge mismatch"],
                analyst_next_steps=["fix rubric"],
                findings=[{"id": "judge_eval_conflict", "severity": "medium"}],
                oracle_arbitration={
                    "judge_alignment": "conflicted",
                    "winner": "judge",
                    "conflict_count": 1,
                    "resolution_summary": "picked judge verdict",
                },
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id="chain-a",
    )

    assert gate["valid"] is False
    assert any("oracle_winner_must_be_contract:run-oracle-conflict:judge" == reason for reason in gate["reasons"])


def test_forensic_sla_gate_filters_latest_run_by_chain_id(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_forensic_sla_gate_status"]

    run_chain = tmp_path / "run-chain-a"
    run_chain.mkdir()
    _write_run_summary(run_chain, "run-chain-a", chain_id="chain-a")
    (run_chain / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_chain,
                "run-chain-a",
                generated_at="2026-03-01T08:00:00Z",
                analyst_root_causes=["stable"],
                analyst_next_steps=["continue"],
                oracle_arbitration={
                    "judge_alignment": "corroborated",
                    "winner": "contract",
                    "conflict_count": 0,
                    "resolution_summary": "aligned",
                },
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_other = tmp_path / "run-chain-b-invalid"
    run_other.mkdir()
    _write_run_summary(run_other, "run-chain-b-invalid", chain_id="chain-b")
    (run_other / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_other,
                "run-chain-b-invalid",
                generated_at="2026-03-01T08:00:01Z",
                analyst="a2",
                analyst_root_causes=["missing arbitration"],
                analyst_next_steps=["fix"],
                oracle_arbitration=None,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id="chain-a",
    )

    assert gate["valid"] is True
    assert gate["latest_run"]["run_id"] == "run-chain-a"
    assert gate["reasons"] == []


def test_forensic_sla_gate_requires_chain_id_in_acceptance_mode(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_forensic_sla_gate_status"]

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id=None,
    )

    assert gate["valid"] is False
    assert "forensic_sla_chain_id_missing" in gate["reasons"]


def test_oracle_conflict_gate_filters_latest_run_by_chain_id(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_oracle_conflict_gate_status"]

    run_chain = tmp_path / "run-oracle-chain-a"
    run_chain.mkdir()
    _write_run_summary(run_chain, "run-oracle-chain-a", chain_id="chain-a")
    (run_chain / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_chain,
                "run-oracle-chain-a",
                generated_at="2026-03-01T08:10:00Z",
                analyst_root_causes=["none"],
                analyst_next_steps=["continue"],
                oracle_arbitration={
                    "judge_alignment": "corroborated",
                    "winner": "contract",
                    "conflict_count": 0,
                    "resolution_summary": "aligned",
                },
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_other = tmp_path / "run-oracle-chain-b-conflict"
    run_other.mkdir()
    _write_run_summary(run_other, "run-oracle-chain-b-conflict", chain_id="chain-b")
    (run_other / "manual_audit.json").write_text(
        json.dumps(
            _done_manual_audit_payload(
                run_other,
                "run-oracle-chain-b-conflict",
                generated_at="2026-03-01T08:10:01Z",
                analyst="a2",
                analyst_root_causes=["judge mismatch"],
                analyst_next_steps=["fix rubric"],
                findings=[{"id": "judge_eval_conflict", "severity": "medium"}],
                oracle_arbitration={
                    "judge_alignment": "conflicted",
                    "winner": "judge",
                    "conflict_count": 1,
                    "resolution_summary": "picked judge",
                },
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id="chain-a",
    )

    assert gate["valid"] is True
    assert gate["latest_run"]["run_id"] == "run-oracle-chain-a"
    assert gate["reasons"] == []


def test_oracle_conflict_gate_requires_chain_id_in_acceptance_mode(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_oracle_conflict_gate_status"]

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        chain_id=None,
    )

    assert gate["valid"] is False
    assert "oracle_conflict_chain_id_missing" in gate["reasons"]


def test_scenario_governance_gate_blocks_replay_without_registry_entry(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_scenario_governance_status"]

    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        run_mode="llm",
        run_id="booking-replay-test",
        scenarios_file=str(scenarios_path),
        baseline_summary=None,
        scenario_contract={"valid": True},
        registry_path=str(tmp_path / "scenario_registry.json"),
        chain_controller_status={"mode": "replay"},
    )

    assert gate["valid"] is False
    assert "scenario_registry_missing_entry" in gate["reasons"]


def test_scenario_governance_gate_blocks_legacy_registry_schema(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_scenario_governance_status"]
    digest_file = ns["_llm_quality_digest_file"]

    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scenario_fp = digest_file(str(scenarios_path))
    registry_path = tmp_path / "scenario_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": {
                    scenario_fp: {
                        "scenario_fingerprint": scenario_fp,
                        "acceptance_eligible": True,
                        "coverage_tokens": ["booking", "info", "interrupt", "handoff"],
                        "promotion": {"status": "eligible"},
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        run_mode="llm",
        run_id="booking-replay-test",
        scenarios_file=str(scenarios_path),
        baseline_summary=None,
        scenario_contract={"valid": True},
        registry_path=str(registry_path),
        chain_controller_status={"mode": "replay"},
    )

    assert gate["valid"] is False
    assert "scenario_registry_schema_version_unsupported" in gate["reasons"]


def test_scenario_governance_gate_accepts_registered_replay_scenarios(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_scenario_governance_status"]
    digest_file = ns["_llm_quality_digest_file"]
    schema_version = ns["LLM_QUALITY_SCENARIO_GOVERNANCE_SCHEMA_VERSION"]
    policy_version = ns["LLM_QUALITY_SCENARIO_REALISM_POLICY_VERSION"]

    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scenario_fp = digest_file(str(scenarios_path))
    registry_path = tmp_path / "scenario_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "version": schema_version,
                "entries": {
                    scenario_fp: {
                        "scenario_fingerprint": scenario_fp,
                        "acceptance_eligible": True,
                        "coverage_tokens": ["booking", "info", "interrupt", "handoff"],
                        "promotion": {"status": "eligible"},
                        "realism_sla": {
                            "policy_version": policy_version,
                            "valid": True,
                            "taxonomy_mapping_version": "2026-03-03.stage-d.v1",
                            "required_business_buckets": [
                                "production-like",
                                "expert-hard",
                                "chaos-noise",
                            ],
                            "business_bucket_presence": {
                                "production-like": True,
                                "expert-hard": True,
                                "chaos-noise": True,
                            },
                            "business_valid": True,
                            "bucket_presence": {
                                "booking": True,
                                "info": True,
                                "interrupt": True,
                                "handoff": True,
                            },
                        },
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        run_mode="llm",
        run_id="booking-replay-test",
        scenarios_file=str(scenarios_path),
        baseline_summary=None,
        scenario_contract={"valid": True},
        registry_path=str(registry_path),
        chain_controller_status={"mode": "replay"},
    )

    assert gate["valid"] is True
    assert gate["reasons"] == []


def test_scenario_governance_gate_blocks_missing_business_bucket(tmp_path):
    ns = _load_quality_helpers()
    build_gate = ns["_llm_quality_build_scenario_governance_status"]
    digest_file = ns["_llm_quality_digest_file"]
    schema_version = ns["LLM_QUALITY_SCENARIO_GOVERNANCE_SCHEMA_VERSION"]
    policy_version = ns["LLM_QUALITY_SCENARIO_REALISM_POLICY_VERSION"]

    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scenario_fp = digest_file(str(scenarios_path))
    registry_path = tmp_path / "scenario_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "version": schema_version,
                "entries": {
                    scenario_fp: {
                        "scenario_fingerprint": scenario_fp,
                        "acceptance_eligible": True,
                        "coverage_tokens": ["booking", "info", "interrupt", "handoff"],
                        "promotion": {"status": "eligible"},
                        "realism_sla": {
                            "policy_version": policy_version,
                            "valid": True,
                            "taxonomy_mapping_version": "2026-03-03.stage-d.v1",
                            "required_business_buckets": [
                                "production-like",
                                "expert-hard",
                                "chaos-noise",
                            ],
                            "business_bucket_presence": {
                                "production-like": True,
                                "expert-hard": True,
                                "chaos-noise": False,
                            },
                            "business_valid": False,
                            "bucket_presence": {
                                "booking": True,
                                "info": True,
                                "interrupt": True,
                                "handoff": True,
                            },
                        },
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = build_gate(
        mode="block",
        output_dir=str(tmp_path / "run-next"),
        lane_effective="acceptance",
        run_mode="llm",
        run_id="booking-replay-test",
        scenarios_file=str(scenarios_path),
        baseline_summary=None,
        scenario_contract={"valid": True},
        registry_path=str(registry_path),
        chain_controller_status={"mode": "replay"},
    )

    assert gate["valid"] is False
    assert "scenario_registry_realism_business_sla_failed" in gate["reasons"]
    assert "scenario_registry_business_bucket_missing:chaos-noise" in gate["reasons"]


def test_scenario_governance_registry_update_writes_entry(tmp_path):
    ns = _load_quality_helpers()
    update_registry = ns["_llm_quality_update_scenario_governance_registry"]
    schema_version = ns["LLM_QUALITY_SCENARIO_GOVERNANCE_SCHEMA_VERSION"]

    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result = update_registry(
        registry_path=str(tmp_path / "scenario_registry.json"),
        scenario_path=str(scenarios_path),
        run_id="booking-lock-abc",
        lane_effective="acceptance",
        scenario_contract={
            "valid": True,
            "coverage_tokens": ["booking", "info", "interrupt", "handoff"],
            "tag_counts": {
                "check_booking": 5,
                "confirm": 5,
                "interrupt": 2,
                "noise": 1,
                "policy": 1,
            },
            "dialog_count": 10,
            "turn_count": 120,
            "weak_expectation_ratio": 0.0,
            "reply_type_coverage": 0.95,
            "action_coverage": 0.9,
            "info_coverage": 0.85,
        },
        chain_controller_status={"mode": "lock", "chain_id": "demo"},
    )

    assert result["updated"] is True
    assert result["scenario_fingerprint"]
    payload = json.loads((tmp_path / "scenario_registry.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == schema_version
    assert result["scenario_fingerprint"] in payload["entries"]
    entry = payload["entries"][result["scenario_fingerprint"]]
    assert entry["realism_sla"]["valid"] is True
    assert entry["realism_sla"]["business_valid"] is True
    assert entry["realism_sla"]["taxonomy_mapping_version"] == "2026-03-03.stage-d.v1"
    assert entry["promotion"]["status"] == "eligible"
    assert entry["promotion"]["lifecycle"][-1]["status"] == "eligible"


def test_scenario_governance_registry_finalize_promotes_full_to_approved(tmp_path):
    ns = _load_quality_helpers()
    update_registry = ns["_llm_quality_update_scenario_governance_registry"]
    finalize_registry = ns["_llm_quality_finalize_scenario_governance_registry"]

    registry_path = tmp_path / "scenario_registry.json"
    scenarios_path = tmp_path / "scenarios.json"
    scenarios_path.write_text(
        json.dumps({"dialogs": [{"turns": [{"text": "hi"}]}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    update = update_registry(
        registry_path=str(registry_path),
        scenario_path=str(scenarios_path),
        run_id="booking-lock-abc",
        lane_effective="acceptance",
        scenario_contract={
            "valid": True,
            "coverage_tokens": ["booking", "info", "interrupt", "handoff"],
            "dialog_count": 10,
            "turn_count": 120,
            "weak_expectation_ratio": 0.0,
            "reply_type_coverage": 0.95,
            "action_coverage": 0.9,
            "info_coverage": 0.85,
        },
        chain_controller_status={"mode": "lock", "chain_id": "demo"},
    )
    assert update["updated"] is True

    finalize = finalize_registry(
        registry_path=str(registry_path),
        scenario_path=str(scenarios_path),
        run_id="booking-full-abc",
        lane_effective="acceptance",
        chain_controller_status={"mode": "full", "chain_id": "demo"},
        summary_path=str(tmp_path / "summary.json"),
        infra_valid=True,
        semantic_valid=True,
        run_integrity_valid=True,
    )
    assert finalize["updated"] is True

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = payload["entries"][update["scenario_fingerprint"]]
    assert entry["promotion"]["status"] == "approved"
    assert entry["promotion"]["approved_run_id"] == "booking-full-abc"
    assert entry["promotion"]["lifecycle"][-1]["status"] == "approved"


def test_acceptance_entrypoint_hint_lock_mode_contains_guarded_wrapper():
    ns = _load_quality_helpers()
    build_hint = ns["_llm_quality_acceptance_entrypoint_hint"]

    args = SimpleNamespace(
        scenarios_file=None,
        base_url="http://127.0.0.1:18100",
        client_slug="demo_salon",
    )
    hint = build_hint(args=args, run_id="booking-lock-20260301-a1")

    assert hint.startswith("scripts/llm_quality_guarded.sh --mode lock")
    assert "--run-id booking-lock-20260301-a1" in hint
    assert "--quality-lane acceptance" in hint
    assert "--pg-checklist" in hint


def test_acceptance_entrypoint_hint_replay_mode_contains_required_flags():
    ns = _load_quality_helpers()
    build_hint = ns["_llm_quality_acceptance_entrypoint_hint"]

    args = SimpleNamespace(
        scenarios_file="/tmp/booking_quality/booking-lock-42/scenarios.json",
        base_url="http://127.0.0.1:18100",
        client_slug="demo_salon",
    )
    hint = build_hint(args=args, run_id="booking-replay-20260301-a1")

    assert hint.startswith("scripts/llm_quality_guarded.sh --mode replay")
    assert "--scenarios-file /tmp/booking_quality/booking-lock-<id>/scenarios.json" in hint
    assert "--baseline-summary /tmp/booking_quality/booking-lock-<id>/summary.json" in hint
    assert "--reset-before-dialog" in hint
    assert "--fail-on-regression" in hint


def test_llm_quality_gates_defaults_do_not_raise_type_error():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["python3", "ops/diagnose.py", "llm-quality-gates", "--pretty"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode in {0, 2}
    assert "TypeError" not in (result.stderr or "")
    assert result.stdout.strip()

    payload = json.loads(result.stdout)
    assert payload.get("command") == "llm-quality-gates"
    quality_constant_gate = (payload.get("gates") or {}).get("quality_constant_gate")
    assert isinstance(quality_constant_gate, dict)
    assert quality_constant_gate.get("timeout_profile") == "realistic"
