import ast
from pathlib import Path


def _load_fast_collect_guard(
    *,
    verification_signal: bool = False,
    info_signal: bool = False,
    fast_path_enabled: bool = False,
):
    source_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_should_use_expected_reply_collect_fast_path":
            target = node
            break
    if target is None:
        raise AssertionError("helper not found")
    module = ast.Module(body=[target], type_ignores=[])
    fake_os = type(
        "FakeOS",
        (),
        {"environ": {"POLICY_CORE_EXPECTED_REPLY_COLLECT_FAST_PATH": "1" if fast_path_enabled else "0"}},
    )
    namespace = {
        "os": fake_os,
        "EXPECTED_REPLY_SERVICE": "service_choice",
        "EXPECTED_REPLY_TIME": "time",
        "EXPECTED_REPLY_NAME": "name",
        "_looks_like_info_query": lambda *_args, **_kwargs: info_signal,
        "_looks_like_booking_verification_request": (
            lambda *_args, **_kwargs: verification_signal
        ),
        "_normalize_service_text": lambda text: (text or "").strip(),
        "_match_service": lambda *_args, **_kwargs: False,
        "_matches_service_request_lexicon": lambda *_args, **_kwargs: False,
        "is_human_request_message": lambda *_args, **_kwargs: False,
        "is_frustration_message": lambda *_args, **_kwargs: False,
    }
    exec(compile(module, str(source_path), "exec"), namespace, namespace)
    return namespace["_should_use_expected_reply_collect_fast_path"]


def _base_kwargs():
    return {
        "message_text": "Подтвердите, пожалуйста, запись на стрижку.",
        "expected_reply_type": "name",
        "expected_reply_matched": False,
        "expected_reply_blocked_by_info": False,
        "intent_decomp_set": {"check_booking"},
        "info_class_intents": set(),
        "booking_wants_flow": True,
        "booking_slot_signal": False,
        "consult_intent": False,
        "booking_reference_present": False,
        "booking_slots_complete": False,
        "refusal_flags": None,
        "client_slug": "demo_salon",
    }


def test_fast_collect_disabled_by_default():
    fn = _load_fast_collect_guard()
    assert fn(**_base_kwargs()) is False


def test_fast_collect_enabled_allows_check_booking_when_slots_incomplete_without_reference():
    fn = _load_fast_collect_guard(fast_path_enabled=True)
    assert fn(**_base_kwargs()) is True


def test_fast_collect_enabled_blocks_check_booking_when_reference_present():
    fn = _load_fast_collect_guard(fast_path_enabled=True)
    kwargs = _base_kwargs()
    kwargs["booking_reference_present"] = True
    assert fn(**kwargs) is False


def test_fast_collect_enabled_allows_check_booking_when_slots_complete_without_reference():
    fn = _load_fast_collect_guard(fast_path_enabled=True)
    kwargs = _base_kwargs()
    kwargs["booking_slots_complete"] = True
    assert fn(**kwargs) is True


def test_fast_collect_enabled_allows_booking_intent_when_slots_incomplete():
    fn = _load_fast_collect_guard(fast_path_enabled=True)
    kwargs = _base_kwargs()
    kwargs["intent_decomp_set"] = {"booking"}
    assert fn(**kwargs) is True


def test_fast_collect_enabled_allows_booking_intent_even_with_slot_signal():
    fn = _load_fast_collect_guard(fast_path_enabled=True)
    kwargs = _base_kwargs()
    kwargs["intent_decomp_set"] = {"booking"}
    kwargs["booking_slot_signal"] = True
    assert fn(**kwargs) is True


def test_fast_collect_enabled_allows_verification_text_signal_when_intent_other_and_slot_signal():
    fn = _load_fast_collect_guard(verification_signal=True, fast_path_enabled=True)
    kwargs = _base_kwargs()
    kwargs["intent_decomp_set"] = {"other"}
    kwargs["booking_slot_signal"] = True
    assert fn(**kwargs) is True


def test_fast_collect_enabled_blocks_info_signal():
    fn = _load_fast_collect_guard(info_signal=True, fast_path_enabled=True)
    assert fn(**_base_kwargs()) is False
