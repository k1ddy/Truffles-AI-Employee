import ast
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


def test_scenario_contract_blocks_confirm_before_check_booking():
    fn = _load_scenario_contract_helper()
    result = fn(
        dialogs=[
            {
                "turns": [
                    {"text": "Хочу записаться", "tags": ["booking"]},
                    {"text": "Да, подтверждаю", "tags": ["confirm"]},
                    {"text": "Проверьте мою запись", "tags": ["check_booking"]},
                ]
            }
        ],
        scenario_coverage="booking,info,interrupt",
    )

    assert result["valid"] is False
    assert "check_confirm_sequence_missing" in result["reasons"]
