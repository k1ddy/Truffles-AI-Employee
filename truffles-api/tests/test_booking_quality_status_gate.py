import ast
import hashlib
import os
import re
from pathlib import Path


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
        "LLM_QUALITY_REGEX_LEXICON_TOKENS",
        "LLM_QUALITY_REGEX_LEXICON_RESOLVER_PREFIXES",
        "LLM_QUALITY_REGEX_LEXICON_TEST_PREFIX",
        "LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE",
        "LLM_QUALITY_PROGRESS_SKIP_TAGS",
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
        "_llm_quality_check_thresholds",
        "_llm_quality_check_regression",
        "_llm_quality_collect_override_reason_codes",
        "_llm_quality_init_rewrite_governance_state",
        "_llm_quality_track_rewrite_governance",
        "_llm_quality_finalize_rewrite_governance",
        "_llm_quality_collect_blocking_reasons",
        "_llm_quality_is_lexicon_regex_delta_file",
        "_llm_quality_build_lexicon_regex_delta_status",
        "_llm_quality_hq1_normalize_text",
        "_llm_quality_hq1_contains_any",
        "_llm_quality_hq1_has_hallucination_signal",
        "_llm_quality_collect_hq1_classes",
        "_llm_quality_should_expect_booking_progress",
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
    namespace = {"hashlib": hashlib, "os": os, "re": re}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


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
