import ast
from pathlib import Path


def _load_suppress_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_functions = {
        "_llm_quality_normalize_expect_token",
        "_llm_quality_normalize_tool_token",
        "_llm_quality_check_booking_tool_answered",
        "_llm_quality_has_expected_followup_prompt",
        "_llm_quality_should_suppress_missed_question_judge_fail",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_should_suppress_missed_question_judge_fail"]


def test_suppresses_missed_question_for_provider_unavailable_booking_reply():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"tool_decision": "provider_unavailable"},
        meta_action="reply",
        expected_reply_type_value="time",
        booking_active=True,
        turn_tags=["booking"],
        outbox_text="Сейчас не могу проверить слоты, могу передать менеджеру.",
    )

    assert suppress is True


def test_does_not_suppress_when_judge_reason_is_not_missed_question():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["hallucination"]},
        strict_reasons=[],
        meta={"tool_decision": "provider_unavailable"},
        meta_action="reply",
        expected_reply_type_value="time",
        booking_active=True,
        turn_tags=["booking"],
        outbox_text="Сейчас не могу проверить слоты.",
    )

    assert suppress is False


def test_suppresses_missed_question_for_media_turn_during_booking_flow():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"tool_decision": "ok"},
        meta_action="reply",
        expected_reply_type_value="service_choice",
        booking_active=True,
        turn_tags=["media", "booking"],
        outbox_text="На какую услугу хотите записаться?",
    )

    assert suppress is True


def test_suppresses_missed_question_when_followup_prompt_is_present():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"tool_decision": "ok"},
        meta_action="reply",
        expected_reply_type_value="name",
        booking_active=True,
        turn_tags=["booking"],
        outbox_text="Как вас зовут?",
    )

    assert suppress is True


def test_suppresses_missed_question_for_not_found_service_fallback():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"intent": "catalog.service_query", "tool_decision": "not_found_fallback"},
        meta_action="reply",
        expected_reply_type_value=None,
        booking_active=False,
        turn_tags=["price"],
        outbox_text="В списке услуг нет такой позиции. Могу уточнить или предложить варианты.",
    )

    assert suppress is True


def test_suppresses_missed_question_for_media_out_of_domain_safe_reply():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"intent": "out_of_domain", "tool_decision": None},
        meta_action="out_of_domain",
        expected_reply_type_value=None,
        booking_active=False,
        turn_tags=["media"],
        outbox_text="Я помогаю по салону: услуги, запись и цены.",
    )

    assert suppress is True
