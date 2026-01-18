from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_webhook_trace():
    # Load trace module directly to avoid webhook package side effects in tests.
    trace_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "routers"
        / "webhook"
        / "trace.py"
    )
    spec = spec_from_file_location("webhook_trace", trace_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


webhook_trace = _load_webhook_trace()


def test_retain_decision_trace_keeps_priority_stages_over_limit():
    trace_list = [
        {"stage": "booking_interrupt"},
        {"stage": "multi_truth"},
    ]
    trace_list.extend(
        {"stage": "policy_gate"} for _ in range(webhook_trace.DECISION_TRACE_MAX + 1)
    )

    retained = webhook_trace._retain_decision_trace(trace_list)

    assert len(retained) == webhook_trace.DECISION_TRACE_MAX
    stages = {item.get("stage") for item in retained}
    assert "booking_interrupt" in stages
    assert "multi_truth" in stages
