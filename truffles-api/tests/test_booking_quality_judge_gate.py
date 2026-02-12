import ast
from pathlib import Path


def _load_should_judge_turn():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "LLM_QUALITY_JUDGE_CRITICAL_TAGS" in names:
                selected_nodes.append(node)
                break
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_llm_quality_should_judge_turn":
            selected_nodes.append(node)
            break

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_should_judge_turn"]


def test_should_judge_turn_skips_when_user_text_missing():
    fn = _load_should_judge_turn()
    ok, reason = fn(
        judge_enabled=True,
        judge_mode="all",
        state="bot_active",
        bot_response=True,
        user_text=None,
    )
    assert ok is False
    assert reason == "missing_user_text"


def test_should_judge_turn_skips_pending_state():
    fn = _load_should_judge_turn()
    ok, reason = fn(
        judge_enabled=True,
        judge_mode="all",
        state="pending",
        bot_response=True,
        user_text="хочу записаться",
    )
    assert ok is False
    assert reason == "pending_state"


def test_should_judge_turn_allows_regular_user_turn():
    fn = _load_should_judge_turn()
    ok, reason = fn(
        judge_enabled=True,
        judge_mode="all",
        state="bot_active",
        bot_response=True,
        user_text="хочу записаться на завтра",
    )
    assert ok is True
    assert reason is None


def test_should_judge_turn_critical_mode_skips_non_critical_turn():
    fn = _load_should_judge_turn()
    ok, reason = fn(
        judge_enabled=True,
        judge_mode="critical",
        state="bot_active",
        bot_response=True,
        user_text="ок",
        turn_tags=["noise"],
        expected_action=None,
        expected_reply_type=None,
        expected_state=None,
        expected_info_sections=[],
        info_tags=[],
        booking_active=False,
        booking_progress_expected=False,
        evaluation_reasons=[],
    )
    assert ok is False
    assert reason == "critical_skip"
