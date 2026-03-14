import ast
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_scenario_contract_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_functions = {
        "_llm_quality_parse_coverage_tokens",
        "_llm_quality_build_scenario_contract_status",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_build_scenario_contract_status"]


def _load_full_diagnose_module():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    spec = spec_from_file_location("diagnose_script_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scenario_contract_blocks_booking_runs_without_check_and_confirm_tags():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"]},
                    {"text": "Можно на 19:00?", "tags": ["time"]},
                    {"text": "Меня зовут Лена", "tags": ["name"]},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is False
    assert "missing_tag:check_booking" in result["reasons"]
    assert "missing_tag:confirm" in result["reasons"]


def test_scenario_contract_accepts_booking_with_check_confirm_sequence():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
                {
                    "turns": [
                        {
                            "text": "Хочу записаться",
                            "tags": ["booking"],
                            "expect": {"reply_type": "time"},
                        },
                        {
                            "text": "Проверьте мою запись",
                            "tags": ["check_booking"],
                            "expect": {"action": "reply"},
                        },
                        {
                            "text": "Да, подтверждаю",
                            "tags": ["confirm"],
                            "expect": {"action": "reply"},
                        },
                    ]
                }
            ],
            scenario_coverage="booking,info,interrupt",
        )

    assert result["valid"] is True
    assert result["reasons"] == []
    assert result["dialogs_with_check_confirm_sequence"] == 1


def test_scenario_contract_accepts_independent_check_booking_and_confirm_coverage():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"], "expect": {"reply_type": "time"}},
                    {"text": "Да, подтверждаю", "tags": ["confirm"], "expect": {"action": "reply"}},
                ]
            },
            {
                "turns": [
                    {"text": "Проверьте мою запись", "tags": ["check_booking"], "expect": {"action": "reply"}},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is True
    assert result["reasons"] == []
    assert result["dialogs_with_check_confirm_sequence"] == 0


def test_scenario_contract_rejects_orphan_pending_question_turn():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"], "expect": {"reply_type": "time"}},
                    {"text": "Можно на 18:30?", "tags": ["time"], "expect": {"reply_type": "name"}},
                    {"text": "Меня зовут Айгуль", "tags": ["name"], "expect": {"reply_type": None}},
                    {"text": "Проверьте мою запись", "tags": ["check_booking"], "expect": {"action": "reply"}},
                    {
                        "text": "На какое время у вас есть слоты?",
                        "tags": ["ask_about_requested_slot"],
                        "expect": {
                            "reply_type": "time",
                            "meta_any": {"pending_question_act": ["ask_about_requested_slot"]},
                        },
                    },
                    {"text": "Да, подтверждаю", "tags": ["confirm"], "expect": {"action": "reply"}},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is False
    assert any(reason.startswith("orphan_pending_question_turn:d1:t5") for reason in result["reasons"])


def test_scenario_contract_accepts_pending_question_with_active_time_context():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"], "expect": {"reply_type": "time"}},
                    {
                        "text": "На какое время лучше записаться?",
                        "tags": ["ask_about_requested_slot"],
                        "expect": {
                            "reply_type": "time",
                            "meta_any": {"pending_question_act": ["ask_about_requested_slot"]},
                        },
                    },
                    {"text": "Да, подтверждаю", "tags": ["confirm"], "expect": {"action": "reply"}},
                    {"text": "Проверьте мою запись", "tags": ["check_booking"], "expect": {"action": "reply"}},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is True
    assert not any(reason.startswith("orphan_pending_question_turn:") for reason in result["reasons"])


def test_extract_expectations_compiles_active_time_specialist_followup_contract():
    module = _load_full_diagnose_module()

    expectations = module._llm_quality_extract_expectations(
        {
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_target": ["specialist"],
                    "pending_question_interaction": ["specialist_followup"],
                    "active_question_relation": ["referent_followup"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "decision": "booking_specialist_followup",
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                        "expected_reply_type": "time",
                    }
                ],
            },
        }
    )

    assert expectations["reply_type"] == "time"
    assert expectations["meta_any"]["pending_question_target"] == ["specialist"]
    assert expectations["meta_any"]["active_question_relation"] == ["referent_followup"]
    assert expectations["meta_any"]["expected_reply_type"] == ["time"]
    assert expectations["meta_any"].get("pending_question_interaction") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in expectations["trace_contains"]
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in expectations["trace_contains"]
    )


def test_scenario_contract_accepts_pending_question_after_generic_info_interrupt():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"], "expect": {"reply_type": "time"}},
                    {"text": "Какие услуги есть?", "tags": ["info"], "expect": {"expected_reply": True}},
                    {
                        "text": "Есть ли запись на выходные?",
                        "tags": ["slot_compare"],
                        "expect": {
                            "reply_type": "time",
                            "meta_any": {"pending_question_act": ["slot_compare"]},
                        },
                    },
                    {"text": "Проверьте мою запись", "tags": ["check_booking"], "expect": {"action": "reply"}},
                    {"text": "Да, подтверждаю", "tags": ["confirm"], "expect": {"action": "reply"}},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is True
    assert not any(reason.startswith("orphan_pending_question_turn:") for reason in result["reasons"])


def test_scenario_contract_acceptance_rejects_relaxed_envelope():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"], "expect": {"reply_type": "time"}},
                    {"text": "Проверьте запись", "tags": ["check_booking"], "expect": {"action": "reply"}},
                    {"text": "Да", "tags": ["confirm"], "expect": {"action": "reply"}},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
        requested_count=2,
        include_media=False,
        acceptance_contract=True,
    )

    assert result["valid"] is False
    assert "acceptance_count_lt_10" in result["reasons"]
    assert "acceptance_dialogs_lt_10" in result["reasons"]
    assert "acceptance_include_media_required" in result["reasons"]
    assert "acceptance_missing_coverage:handoff" in result["reasons"]
    assert "acceptance_handoff_tag_missing" in result["reasons"]


def test_scenario_contract_acceptance_accepts_canonical_envelope():
    fn = _load_scenario_contract_helper()
    dialogs = [
        {
            "turns": [
                {
                    "text": "Отправляю фото и хочу записаться",
                    "tags": ["booking", "media"],
                    "expect": {"reply_type": "time"},
                },
                {
                    "text": "Проверьте мою запись",
                    "tags": ["check_booking"],
                    "expect": {"action": "reply"},
                },
                {
                    "text": "Да, подтверждаю",
                    "tags": ["confirm"],
                    "expect": {"action": "reply"},
                },
                {
                    "text": "Соедините с менеджером",
                    "tags": ["handoff", "interrupt"],
                    "expect": {"action": "handoff"},
                },
            ]
        }
        for _ in range(10)
    ]
    result = fn(
        dialogs=dialogs,
        scenario_coverage="booking,info,interrupt,handoff",
        requested_count=10,
        include_media=True,
        acceptance_contract=True,
    )

    assert result["valid"] is True
    assert result["reasons"] == []
