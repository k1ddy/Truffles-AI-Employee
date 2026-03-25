import ast
from pathlib import Path


def _load_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assignments = {
        "LLM_QUALITY_OUTBOX_SUCCESS_STATUSES",
        "LLM_QUALITY_OUTBOX_FAILURE_STATUSES",
        "LLM_QUALITY_OUTBOX_PENDING_STATUSES",
    }
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_normalize_outbox_status",
        "_llm_quality_resolve_outbox_status",
        "_llm_quality_outbox_delivery_state",
        "_llm_quality_is_unobserved_turn",
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
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def test_unobserved_turn_detected_for_duplicate_ack_without_text():
    ns = _load_helpers()
    fn = ns["_llm_quality_is_unobserved_turn"]

    observed = fn(
        expected_response=True,
        outbox_text=None,
        outbox_payload_status=None,
        outbox_summary={"count": 1, "status": None},
        bot_response_inferred_duplicate_ack=True,
        meta={"action": "reply"},
    )

    assert observed is True


def test_unobserved_turn_detected_for_pending_transport_without_text():
    ns = _load_helpers()
    fn = ns["_llm_quality_is_unobserved_turn"]

    observed = fn(
        expected_response=True,
        outbox_text="",
        outbox_payload_status="PENDING",
        outbox_summary={"count": 1, "status": "PENDING"},
        bot_response_inferred_duplicate_ack=False,
        meta={"action": "reply"},
    )

    assert observed is True


def test_unobserved_turn_not_detected_when_text_exists():
    ns = _load_helpers()
    fn = ns["_llm_quality_is_unobserved_turn"]

    observed = fn(
        expected_response=True,
        outbox_text="Свободные слоты: 10:00, 11:00",
        outbox_payload_status="SENT",
        outbox_summary={"count": 1, "status": "SENT"},
        bot_response_inferred_duplicate_ack=True,
        meta={"action": "reply"},
    )

    assert observed is False
