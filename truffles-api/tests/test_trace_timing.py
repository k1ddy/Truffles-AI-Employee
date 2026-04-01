from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app import logging_config


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


def test_build_trace_attributes_filters():
    context = {
        "message_id": "msg-1",
        "outbox_id": "out-1",
        "trace_id": "trace-1",
        "client_slug": "demo",
        "conversation_id": "conv-1",
        "branch_id": "branch-1",
        "extra": "skip",
        "outbox_ids": ["out-1"],
    }

    attrs = logging_config.build_trace_attributes(context)

    assert attrs["message_id"] == "msg-1"
    assert attrs["outbox_id"] == "out-1"
    assert attrs["trace_id"] == "trace-1"
    assert attrs["client_slug"] == "demo"
    assert attrs["conversation_id"] == "conv-1"
    assert attrs["branch_id"] == "branch-1"
    assert "extra" not in attrs
    assert "outbox_ids" not in attrs
