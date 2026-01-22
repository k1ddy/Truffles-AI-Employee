from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_webhook_trace():
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


class DummyMessage:
    def __init__(self, metadata=None):
        self.message_metadata = metadata


def test_merge_message_timing_adds_pipeline_ms():
    message = DummyMessage({})

    webhook_trace._merge_message_timing(message, {"pipeline_ms": 12.3})

    timing = message.message_metadata["decision_meta"]["timing"]
    assert timing["pipeline_ms"] == 12.3


def test_merge_message_timing_merges_nested_payloads():
    message = DummyMessage(
        {
            "decision_meta": {
                "timing": {
                    "stages": {"send_ms": 1.2},
                    "outbox": {"wait_ms": 10.0},
                }
            }
        }
    )

    webhook_trace._merge_message_timing(
        message,
        {"stages": {"booking_ms": 3.4}, "outbox": {"process_ms": 20.0}},
    )

    timing = message.message_metadata["decision_meta"]["timing"]
    assert timing["stages"]["send_ms"] == 1.2
    assert timing["stages"]["booking_ms"] == 3.4
    assert timing["outbox"]["wait_ms"] == 10.0
    assert timing["outbox"]["process_ms"] == 20.0
