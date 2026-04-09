import importlib.util
import sys
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "focused_family_proof.py"
    spec = importlib.util.spec_from_file_location("focused_family_proof", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_turn_payload_includes_runtime_tenant_context():
    mod = _load_module()
    context = mod.RuntimeClientContext(
        client_id="11111111-1111-4111-8111-111111111111",
        client_slug="demo_salon",
        branch_id="22222222-2222-4222-8222-222222222222",
        branch_slug="main",
        instance_id="instance-1",
        webhook_secret="secret",
        webhook_secret_source="branch",
    )

    payload = mod.build_turn_payload(
        message="Хочу записаться",
        context=context,
        remote_jid="77010000000@s.whatsapp.net",
        message_id="msg-1",
        sender="focused_family_proof",
        timestamp=1700000000,
    )

    assert payload["client_slug"] == "demo_salon"
    assert payload["body"]["message"] == "Хочу записаться"
    assert payload["body"]["metadata"]["remoteJid"] == "77010000000@s.whatsapp.net"
    assert payload["body"]["metadata"]["instanceId"] == "instance-1"
    assert payload["tenant_context"] == {
        "client_id": "11111111-1111-4111-8111-111111111111",
        "client_slug": "demo_salon",
        "branch_id": "22222222-2222-4222-8222-222222222222",
        "branch_slug": "main",
        "instance_id": "instance-1",
        "source": "webhook",
        "origin_source": "focused_family_proof",
    }


def test_validate_runtime_fingerprint_detects_commit_mismatch(monkeypatch):
    mod = _load_module()

    monkeypatch.setattr(
        mod,
        "_fetch_json",
        lambda *_args, **_kwargs: {
            "version": "a922-18189-f40d7150",
            "git_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "build_time": "2026-04-03T00:00:00Z",
        },
    )

    fingerprint = mod.validate_runtime_fingerprint(
        base_url="http://127.0.0.1:18189",
        expected_commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        timeout=5.0,
    )

    assert fingerprint.valid is False
    assert "git_commit_mismatch" in fingerprint.reasons
    assert fingerprint.runtime_version == "a922-18189-f40d7150"


def test_timeout_error_is_eligible_for_db_fallback():
    mod = _load_module()

    assert mod._error_allows_db_fallback("TimeoutError:timed out") is True
    assert mod._error_allows_db_fallback("http.client.RemoteDisconnected: closed") is True
    assert mod._error_allows_db_fallback("HTTP Error 401: Unauthorized") is False


def test_extract_turn_snapshot_returns_canonical_evidence():
    mod = _load_module()
    bundle = {
        "conversation_id": "conv-1",
        "state": "bot_active",
        "context": {
            "decision_trace": [
                {"stage": "preflight", "recorded_at": "2026-04-03T10:00:00Z"},
                {
                    "stage": "runtime",
                    "recorded_at": "2026-04-03T10:00:01Z",
                    "runtime_trace_contract": {
                        "owner_transition": {"requested_outcome": "collect"},
                        "action_transition": {
                            "contract_action": "collect",
                            "execution_tool_action": "collect",
                            "reply_kind": "collect",
                        },
                    },
                },
            ]
        },
        "messages": [
            {"role": "user", "content": "Привет", "message_id": "old", "decision_meta": {"action": "fact"}},
            {
                "role": "user",
                "content": "Я хочу записаться к Динаре.",
                "message_id": "msg-2",
                "decision_meta": {
                    "action": "collect",
                    "tool_action": "collect",
                    "source": "llm_policy_core",
                    "expected_reply_type": "time",
                    "expected_reply_reason": "follow-up",
                    "pending_question_target": "specialist",
                    "active_question_relation": "referent_followup",
                    "runtime_trace_contract": {
                        "owner_transition": {"requested_outcome": "collect"},
                        "action_transition": {
                            "contract_action": "collect",
                            "execution_tool_action": "collect",
                            "reply_kind": "collect",
                        },
                    },
                },
            },
            {
                "role": "assistant",
                "content": "Хорошо, ориентир по мастеру — Динара. На какую дату и время вам удобно?",
                "message_id": None,
                "decision_meta": None,
            },
        ],
    }

    snapshot = mod.extract_turn_snapshot(bundle=bundle, message_id="msg-2", previous_trace_count=1)

    assert snapshot is not None
    assert snapshot["conversation_id"] == "conv-1"
    assert snapshot["assistant_content"].startswith("Хорошо, ориентир")
    assert snapshot["decision_meta_subset"] == {
        "action": "collect",
        "tool_action": "collect",
        "source": "llm_policy_core",
        "expected_reply_type": "time",
        "expected_reply_reason": "follow-up",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
    }
    assert snapshot["runtime_trace_contract_subset"] == {
        "owner_requested_outcome": "collect",
        "contract_action": "collect",
        "execution_tool_action": "collect",
        "reply_kind": "collect",
    }
    assert snapshot["decision_trace"] == [
        {
            "stage": "runtime",
            "recorded_at": "2026-04-03T10:00:01Z",
            "runtime_trace_contract": {
                "owner_transition": {"requested_outcome": "collect"},
                "action_transition": {
                    "contract_action": "collect",
                    "execution_tool_action": "collect",
                    "reply_kind": "collect",
                },
            },
        }
    ]
