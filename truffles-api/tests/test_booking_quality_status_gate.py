import ast
import hashlib
from pathlib import Path


def _load_quality_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assignments = {
        "LLM_QUALITY_THRESHOLDS",
        "LLM_QUALITY_THRESHOLD_DIRECTIONS",
        "LLM_QUALITY_REGRESSION_KEYS",
    }
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
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
    namespace = {"hashlib": hashlib}
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
