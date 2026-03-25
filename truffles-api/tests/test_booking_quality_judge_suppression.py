import ast
from pathlib import Path


def _load_suppress_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_functions = {
        "_llm_quality_booking_collect_contract",
        "_llm_quality_booking_collect_prompt_ok",
        "_llm_quality_normalize_expect_token",
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
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
        meta={
            "tool_decision": "provider_unavailable",
            "llm_policy_override_reason_code": "tool_unavailable",
        },
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
        meta={
            "tool_decision": "provider_unavailable",
            "llm_policy_override_reason_code": "tool_unavailable",
        },
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
        meta={
            "tool_decision": "ok",
            "llm_policy_override_reason_code": "required_slot_missing",
        },
        meta_action="reply",
        expected_reply_type_value="service_choice",
        booking_active=True,
        turn_tags=["media", "booking"],
        outbox_text="На какую услугу хотите записаться?",
    )

    assert suppress is True


def test_suppresses_missed_question_for_media_booking_prompt_without_reason_code():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"action": "booking_prompt"},
        meta_action="booking_prompt",
        expected_reply_type_value="service_choice",
        booking_active=True,
        turn_tags=["media"],
        outbox_text="На какую услугу хотите записаться?",
    )

    assert suppress is True


def test_suppresses_missed_question_when_followup_prompt_is_present():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "tool_decision": "ok",
            "llm_policy_override_reason_code": "required_slot_missing",
        },
        meta_action="reply",
        expected_reply_type_value="name",
        booking_active=True,
        turn_tags=["booking"],
        outbox_text="Как вас зовут?",
    )

    assert suppress is True


def test_suppresses_missed_question_for_booking_prompt_followup_without_reason_code():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "action": "booking_prompt",
            "expected_reply_reason": "booking_prompt",
        },
        meta_action="booking_prompt",
        expected_reply_type_value="name",
        booking_active=True,
        turn_tags=["reschedule", "booking"],
        outbox_text="Отлично, время подходит. Как вас зовут?",
    )

    assert suppress is True


def test_suppresses_missed_question_for_check_booking_collect_reference_prompt():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "action": "check_booking_prompt",
            "intent": "check_booking",
            "expected_reply_reason": "calendar_get_booking_collect_reference",
        },
        meta_action="check_booking_prompt",
        expected_reply_type_value="name",
        booking_active=True,
        turn_tags=["confirm", "check_booking"],
        outbox_text="Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.",
    )

    assert suppress is True


def test_suppresses_missed_question_for_master_service_not_found_collect():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "action": "reply",
            "intent": "master_query",
            "clarify_reason": "master_service_not_found",
            "expected_reply_reason": "master_service_not_found",
            "info_sections": ["master"],
        },
        meta_action="reply",
        expected_reply_type_value="service_choice",
        booking_active=True,
        turn_tags=["master", "booking"],
        outbox_text='Po usluge "Маникюр" utochnu dostupnyh masterov u administratora.',
    )

    assert suppress is True


def test_does_not_suppress_missed_question_for_calendar_list_slots_booking_reply():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "intent": "calendar.list_slots",
            "tool_decision": "ok",
            "llm_policy_override_reason_code": "required_slot_missing",
        },
        meta_action="reply",
        expected_reply_type_value="service_choice",
        booking_active=True,
        turn_tags=["booking"],
        outbox_text="На какую услугу хотите записаться?",
    )

    assert suppress is False


def test_suppresses_missed_question_for_calendar_get_booking_contract_answer():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "action": "reply",
            "intent": "calendar.get_booking",
            "tool_decision": "not_found",
            "llm_policy_override_reason_code": "required_slot_missing",
        },
        meta_action="reply",
        expected_reply_type_value="time",
        booking_active=True,
        turn_tags=["booking", "check_booking"],
        outbox_text="Проверил: пока не вижу подтвержденной записи.",
    )

    assert suppress is True


def test_suppresses_missed_question_for_media_calendar_prompt_with_followup():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_decision": "ok",
        },
        meta_action="reply",
        expected_reply_type_value="time",
        booking_active=True,
        turn_tags=["media"],
        outbox_text="Понял. На какую дату и время вам удобно?",
    )

    assert suppress is True


def test_does_not_suppress_missed_question_without_whitelist_reason_code():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={"intent": "catalog.service_query", "tool_decision": "not_found_fallback"},
        meta_action="reply",
        expected_reply_type_value="service_choice",
        booking_active=False,
        turn_tags=["booking"],
        outbox_text="На какую услугу хотите записаться?",
    )

    assert suppress is False


def test_suppresses_missed_question_for_not_found_service_fallback_with_reason_code():
    fn = _load_suppress_helper()

    suppress = fn(
        judge_result={"verdict": "fail", "reasons": ["missed_question"]},
        strict_reasons=[],
        meta={
            "intent": "catalog.service_query",
            "tool_decision": "not_found_fallback",
            "llm_policy_override_reason_code": "contract_validation_failure",
        },
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
        meta={
            "intent": "out_of_domain",
            "tool_decision": None,
            "llm_policy_override_reason_code": "contract_validation_failure",
        },
        meta_action="out_of_domain",
        expected_reply_type_value=None,
        booking_active=False,
        turn_tags=["media"],
        outbox_text="Я помогаю по салону: услуги, запись и цены.",
    )

    assert suppress is True
