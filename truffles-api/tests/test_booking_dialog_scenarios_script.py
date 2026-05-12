import io
import json
import random
import urllib.error
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from app.services.llm_quality_contracts import (
    advance_booking_scenario_management_context,
    advance_booking_scenario_multi_service_clarify_context,
    advance_booking_scenario_partial_date_anchor_context,
    advance_booking_scenario_pending_question_context,
    apply_booking_scenario_active_name_master_info_interrupt_expectations,
    apply_booking_scenario_active_name_time_availability_followup_expectations,
    apply_booking_scenario_active_pending_question_cancel_interrupt_expectations,
    apply_booking_scenario_active_pending_question_info_interrupt_expectations,
    apply_booking_scenario_active_time_master_info_interrupt_expectations,
    apply_booking_scenario_active_time_specialist_followup_expectations,
    apply_booking_scenario_ambiguous_time_fill_expectations,
    apply_booking_scenario_exact_time_fill_collect_expectations,
    apply_booking_scenario_grounded_partial_date_daypart_fill_expectations,
    apply_booking_scenario_grounded_time_specialist_availability_transition_expectations,
    apply_booking_scenario_multi_service_booking_clarify_expectations,
    apply_booking_scenario_partial_date_fill_collect_expectations,
    apply_booking_scenario_pending_master_info_interrupt_expectations,
    apply_booking_scenario_pending_specialist_availability_followup_expectations,
    apply_booking_scenario_service_grounded_booking_expectations,
    apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations,
    booking_scenario_expectation_has_contract_reason,
    booking_scenario_looks_like_booking_manage_context_followup,
    booking_scenario_looks_like_check_booking_followup,
    booking_scenario_looks_like_generic_booking_request,
    booking_scenario_looks_like_reschedule_followup,
    booking_scenario_looks_like_unsupported_service_inquiry,
    booking_scenario_normalize_active_name_master_info_tags,
    booking_scenario_normalize_active_time_master_info_tags,
    booking_scenario_normalize_active_time_specialist_master_tags,
    booking_scenario_normalize_active_time_weak_time_question_tags,
    booking_scenario_normalize_malformed_check_booking_tags,
    booking_scenario_normalize_partial_date_slot_constraint_tags,
    booking_scenario_normalize_pending_question_tags,
    booking_scenario_normalize_slot_compare_exact_time_fill_tags,
    booking_scenario_normalize_slot_compare_partial_date_constraint_tags,
    booking_scenario_normalize_stateful_booking_tags,
    booking_scenario_orphan_pending_question_expect_override,
    booking_scenario_booking_manage_context_expect_override,
    booking_scenario_time_collect_expect_override,
    clear_booking_scenario_multi_service_info_interrupt_followup_expectations,
    has_booking_scenario_orphan_pending_question_tags,
    merge_booking_scenario_expectations,
    rewrite_booking_scenario_check_booking_followup_tags,
    rewrite_booking_scenario_orphan_pending_question_tags,
    rewrite_booking_scenario_reschedule_followup_tags,
    sanitize_booking_scenario_llm_turns,
)
from app.services.scenario_contract_compiler import (
    compile_active_time_specialist_followup_expectations,
    should_compile_active_time_specialist_followup_expectations,
)


@lru_cache(maxsize=1)
def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "scripts" / "booking_dialog_scenarios.py",
        base.parents[2] / "scripts" / "booking_dialog_scenarios.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip(
            "booking_dialog_scenarios.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("booking_dialog_scenarios", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _LazyModule:
    def __getattr__(self, name):
        return getattr(_load_module(), name)

    def __setattr__(self, name, value):
        setattr(_load_module(), name, value)

    def __delattr__(self, name):
        delattr(_load_module(), name)


_module = _LazyModule()
_merge_expectations = merge_booking_scenario_expectations


def test_resolve_openai_api_key_reads_local_truffles_api_env(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("OPENAI_API_KEY=test-from-env-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "test-from-env-file"
    assert source is not None and "truffles-api/.env" in source


def test_resolve_openai_api_key_accepts_env_alias(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_KEY", "alias-from-env")
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "alias-from-env"
    assert source == "env:OPENAI_API_KEY:OPENAI_KEY"


def test_resolve_openai_api_key_expands_env_reference(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text(
        "OPENAI_API_KEY_FALLBACK=expanded-script-key\nOPENAI_API_KEY=${OPENAI_API_KEY_FALLBACK}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "expanded-script-key"
    assert source is not None and "truffles-api/.env" in source


def test_merge_expectations_applies_override_fields():
    expect = _merge_expectations(
        ["booking", "handoff", "master"],
        {
            "action": "handoff",
            "reply_type": "name",
            "state": "pending",
            "expected_reply": "false",
            "info_sections": ["master"],
        },
    )

    assert expect["action"] == "handoff"
    assert expect["reply_type"] == "name"
    assert expect["state"] == "pending"
    assert expect["expected_reply"] is False
    assert "master" in (expect.get("info_sections") or [])


def test_merge_expectations_preserves_structured_oracle_fields():
    expect = _merge_expectations(
        ["booking"],
        {
            "meta": {
                "action": "booking_prompt",
                "source": "booking",
                "expected_reply_type": "time",
            },
            "meta_any": {
                "source": ["booking", "llm_policy_core"],
            },
            "meta_contains": {
                "info_sections": ["hours"],
            },
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "decision": "set",
                    "expected_reply_type": "time",
                }
            ],
        },
    )

    assert expect["meta"]["expected_reply_type"] == "time"
    assert expect["meta_any"]["source"] == ["booking", "llm_policy_core"]
    assert expect["meta_contains"]["info_sections"] == ["hours"]
    assert expect["trace_contains"][0]["stage"] == "question_contract"


def test_merge_expectations_sanitizes_handoff_override_without_handoff_tags():
    expect = _merge_expectations(
        ["confirm"],
        {
            "action": "booking_escalated",
            "state": "manager_active",
            "expected_reply": "true",
        },
    )

    assert expect["action"] is None
    assert expect["state"] == "bot_active"
    assert expect["expected_reply"] is True


def test_sanitize_booking_manage_followups_keep_handoff_context():
    turns = sanitize_booking_scenario_llm_turns(
        [
            {"kind": "text", "text": "мне надо отменить запись", "tags": ["cancel", "handoff"]},
            {"kind": "text", "text": "маникюр завтра на 7 вечера", "tags": ["service", "date", "time"]},
            {"kind": "text", "text": "Лена 87071112233", "tags": ["name", "phone"]},
        ],
        {},
        None,
    )

    assert turns[1]["tags"] == ["cancel", "service", "date", "time", "handoff"]
    assert turns[1]["expect"]["action"] == "handoff"
    assert turns[1]["expect"]["state"] == "pending"
    assert turns[2]["tags"] == ["cancel", "name", "phone", "handoff"]
    assert turns[2]["expect"]["action"] == "handoff"
    assert turns[2]["expect"]["expected_reply"] is None


def test_sanitize_complaint_handoff_followups_keep_pending_context():
    turns = sanitize_booking_scenario_llm_turns(
        [
            {
                "kind": "text",
                "text": "мне испортили покрытие, хочу чтобы админ связался",
                "tags": ["complaint", "handoff", "human"],
            },
            {"kind": "text", "text": "Марина 87024445566", "tags": ["name", "phone"]},
        ],
        {},
        None,
    )

    assert turns[1]["tags"] == ["handoff", "name", "phone"]
    assert turns[1]["expect"]["action"] == "handoff"
    assert turns[1]["expect"]["state"] == "pending"
    assert turns[1]["expect"]["expected_reply"] is None


def test_sanitize_medical_handoff_human_followup_does_not_expect_new_reply():
    turns = sanitize_booking_scenario_llm_turns(
        [
            {
                "kind": "text",
                "text": "аллергия и воспаление, можно депиляцию?",
                "tags": ["medical", "safety", "handoff"],
            },
            {"kind": "text", "text": "лучше с мастером поговорить", "tags": ["handoff", "human"]},
        ],
        {},
        None,
    )

    assert turns[1]["tags"] == ["handoff", "human"]
    assert turns[1]["expect"]["action"] == "handoff"
    assert turns[1]["expect"]["state"] == "pending"
    assert turns[1]["expect"]["expected_reply"] is None


def test_shared_partial_date_slot_constraint_helper_rewrites_into_time_collect():
    rewritten_tags, changed = booking_scenario_normalize_partial_date_slot_constraint_tags(
        "Мне нужно записаться на завтра.",
        ["slot_constraint"],
        active_reply_type="time",
    )

    assert changed is True
    assert rewritten_tags == ["time"]


def test_shared_slot_compare_partial_date_constraint_helper_rewrites_into_slot_constraint():
    rewritten_tags, changed = (
        booking_scenario_normalize_slot_compare_partial_date_constraint_tags(
            "Есть ли свободные слоты на завтра?",
            ["slot_compare"],
            active_reply_type="time",
        )
    )

    assert changed is True
    assert rewritten_tags == ["slot_constraint"]


def test_shared_slot_compare_exact_time_helper_rewrites_into_time():
    rewritten_tags, changed = booking_scenario_normalize_slot_compare_exact_time_fill_tags(
        "Можно в 19:00?",
        ["slot_compare"],
        active_reply_type="time",
    )

    assert changed is True
    assert rewritten_tags == ["time"]


def test_shared_followup_helpers_normalize_booking_management_tags():
    assert has_booking_scenario_orphan_pending_question_tags(
        ["ask_about_requested_slot"],
        active_reply_type="name",
    )
    assert rewrite_booking_scenario_orphan_pending_question_tags(
        ["ask_about_requested_slot", "price", "booking"]
    ) == ["price", "booking"]
    assert rewrite_booking_scenario_reschedule_followup_tags(
        ["slot_compare", "booking", "price"]
    ) == ["reschedule", "price"]
    assert rewrite_booking_scenario_check_booking_followup_tags(["booking", "price"]) == [
        "check_booking",
        "price",
    ]
    assert booking_scenario_looks_like_booking_manage_context_followup(["date", "phone"])
    assert not booking_scenario_looks_like_booking_manage_context_followup(["booking", "date"])


def test_shared_followup_helpers_return_detached_expect_payloads():
    orphan_expect = booking_scenario_orphan_pending_question_expect_override()
    orphan_expect["meta_any"]["expected_reply_type"].append("mutated")
    orphan_expect["trace_contains"][0]["expected_reply_type"] = "mutated"

    fresh_orphan_expect = booking_scenario_orphan_pending_question_expect_override()
    assert fresh_orphan_expect["meta_any"]["expected_reply_type"] == ["service_choice"]
    manage_expect = booking_scenario_booking_manage_context_expect_override()
    manage_expect["state"] = "mutated"
    assert booking_scenario_booking_manage_context_expect_override()["state"] == "pending"
    assert fresh_orphan_expect["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
        }
    ]

    time_expect = booking_scenario_time_collect_expect_override()
    time_expect["meta_any"]["expected_reply_type"].append("mutated")

    fresh_time_expect = booking_scenario_time_collect_expect_override()
    assert fresh_time_expect["meta_any"]["expected_reply_type"] == ["time"]


def test_shared_management_stateful_helpers_detect_followup_predicates():
    assert booking_scenario_looks_like_reschedule_followup(
        "Давайте перенесем запись на завтра к 15:00",
        ["booking", "time"],
    )
    assert booking_scenario_looks_like_check_booking_followup(
        "Проверьте мою запись, пожалуйста",
        ["booking"],
    )
    assert booking_scenario_looks_like_generic_booking_request(
        "Хочу записаться на маникюр"
    )
    assert not booking_scenario_looks_like_generic_booking_request(
        "Давайте перенесем дату на завтра"
    )


def test_shared_management_stateful_helpers_normalize_stateful_and_malformed_tags():
    normalized_stateful = booking_scenario_normalize_stateful_booking_tags(
        "Можно ли завтра утром?",
        ["booking", "price"],
        active_reply_type="time",
    )
    assert normalized_stateful == ["mixed_fill_plus_question", "price"]

    normalized_malformed, changed = (
        booking_scenario_normalize_malformed_check_booking_tags(
            "Хочу записаться на массаж",
            ["check_booking", "price"],
        )
    )
    assert changed is True
    assert normalized_malformed == ["booking", "price"]


def test_shared_management_stateful_helpers_shape_ambiguous_time_expectations():
    base_expect = {
        "reply_type": "service_choice",
        "expected_reply": True,
        "meta": {"expected_reply_type": "service_choice"},
        "meta_any": {
            "expected_reply_type": ["service_choice"],
            "pending_question_act": ["slot_compare"],
            "pending_question_target": ["time"],
            "pending_question_interaction": ["followup"],
            "pending_question_owner": ["bot"],
            "active_question_relation": ["followup"],
        },
        "trace_contains": [
            {
                "stage": "pending_question_interaction",
                "pending_question_act": "slot_compare",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "service_choice",
            },
        ],
    }

    shaped = apply_booking_scenario_ambiguous_time_fill_expectations(
        base_expect,
        tags=["time"],
        text="Можно в 7 или позже?",
        active_reply_type="time",
    )

    assert shaped["reply_type"] == "time"
    assert shaped["meta"]["expected_reply_type"] == "time"
    assert shaped["meta_any"]["expected_reply_type"] == ["time"]
    assert "pending_question_act" not in shaped["meta_any"]
    assert {
        "stage": "question_contract",
        "expected_reply_type": "time",
    } in shaped["trace_contains"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in shaped["trace_contains"]
    )

    fresh_expect = apply_booking_scenario_ambiguous_time_fill_expectations(
        {
            "reply_type": "service_choice",
            "expected_reply": True,
            "meta_any": {"expected_reply_type": ["service_choice"]},
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "expected_reply_type": "service_choice",
                }
            ],
        },
        tags=["time"],
        text="Можно в 7 или позже?",
        active_reply_type="time",
    )
    assert fresh_expect["meta_any"]["expected_reply_type"] == ["time"]


def test_shared_pending_question_contract_reason_helper_reads_meta_and_trace():
    expect = {
        "meta_any": {"expected_reply_contract_reason": ["multi_service_booking_clarify"]},
        "trace_contains": [{"stage": "question_contract", "reason": "catalog_service_booking_progress"}],
    }

    assert booking_scenario_expectation_has_contract_reason(expect, "multi_service_booking_clarify")
    assert booking_scenario_expectation_has_contract_reason(expect, "catalog_service_booking_progress")
    assert not booking_scenario_expectation_has_contract_reason(expect, "missing_reason")


def test_shared_active_pending_question_info_interrupt_helper_preserves_question_contract():
    updated = apply_booking_scenario_active_pending_question_info_interrupt_expectations(
        {
            "reply_type": None,
            "meta": {"expected_reply_type": "service_choice"},
            "meta_any": {
                "pending_question_act": ["ask_about_requested_slot"],
                "pending_question_target": ["time"],
            },
            "trace_contains": [
                {
                    "stage": "pending_question_interaction",
                    "pending_question_target": "time",
                }
            ],
        },
        tags=["price"],
        active_reply_type="time",
    )

    assert updated["reply_type"] == "time"
    assert updated["expected_reply"] is True
    assert updated["meta"]["expected_reply_type"] == "time"
    assert updated["meta_any"]["expected_reply_type"] == ["time"]
    assert "pending_question_act" not in updated["meta_any"]
    assert updated["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ]


def test_shared_multi_service_interrupt_clear_helper_drops_followup_contract():
    updated = clear_booking_scenario_multi_service_info_interrupt_followup_expectations(
        {
            "reply_type": "service_choice",
            "meta": {
                "expected_reply_type": "service_choice",
                "expected_reply_contract_reason": "multi_service_booking_clarify",
            },
            "meta_any": {
                "expected_reply_type": ["service_choice"],
                "expected_reply_contract_reason": ["multi_service_booking_clarify"],
                "pending_question_interaction": ["ask_about_requested_slot"],
            },
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "expected_reply_type": "service_choice",
                    "reason": "multi_service_booking_clarify",
                },
                {"stage": "booking_interrupt", "decision": "info_reply"},
            ],
        },
        tags=["price"],
        multi_service_clarify_active=True,
    )

    assert updated["reply_type"] is None
    assert "meta" not in updated
    assert "meta_any" not in updated
    assert updated["trace_contains"] == [{"stage": "booking_interrupt", "decision": "info_reply"}]


def test_shared_pending_question_context_helpers_preserve_and_reset_state():
    active_reply_type = advance_booking_scenario_pending_question_context(
        "time",
        tags=["price"],
        expect={"reply_type": None},
    )
    assert active_reply_type == "time"

    clarified_reply_type = advance_booking_scenario_pending_question_context(
        "time",
        tags=["info"],
        expect={
            "reply_type": "service_choice",
            "meta_any": {"expected_reply_contract_reason": ["multi_service_booking_clarify"]},
        },
    )
    assert clarified_reply_type is None

    assert advance_booking_scenario_multi_service_clarify_context(
        True,
        tags=["price"],
        expect={"reply_type": None},
    )
    assert not advance_booking_scenario_multi_service_clarify_context(
        True,
        tags=["booking"],
        expect={"reply_type": None},
    )

    assert advance_booking_scenario_partial_date_anchor_context(
        True,
        active_reply_type="time",
        tags=["price"],
        text="Сколько стоит эта услуга?",
        expect={
            "reply_type": "time",
            "trace_contains": [{"stage": "question_contract", "reason": "catalog_service_booking_progress"}],
        },
    )
    assert not advance_booking_scenario_partial_date_anchor_context(
        True,
        active_reply_type="time",
        tags=["price"],
        text="Сколько стоит эта услуга?",
        expect={"reply_type": "time"},
    )


def test_shared_cancel_interrupt_helper_updates_question_contract():
    updated = apply_booking_scenario_active_pending_question_cancel_interrupt_expectations(
        {
            "trace_contains": [{"stage": "question_contract", "expected_reply_type": "service_choice"}],
        },
        tags=["cancel"],
        active_reply_type="name",
    )

    assert updated["reply_type"] == "name"
    assert updated["expected_reply"] is True
    assert updated["meta_any"]["expected_reply_type"] == ["name"]
    assert updated["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "name",
        }
    ]


def test_shared_booking_progress_helpers_shape_multi_service_and_service_grounded_contracts():
    clarified = apply_booking_scenario_multi_service_booking_clarify_expectations(
        {},
        tags=["booking"],
        text="Хочу маникюр и педикюр, сначала маникюр потом педикюр",
        service_candidates=("маникюр", "педикюр"),
        ctx=None,
    )

    assert clarified["reply_type"] == "service_choice"
    assert clarified["expected_reply"] is True
    assert clarified["meta"]["expected_reply_contract_reason"] == "multi_service_booking_clarify"
    assert clarified["meta_any"]["expected_reply_type"] == ["service_choice"]

    connectorless = apply_booking_scenario_multi_service_booking_clarify_expectations(
        {},
        tags=["booking", "multi_service"],
        text="маникюр педикюр керек",
        service_candidates=("маникюр", "педикюр"),
        ctx=None,
    )

    assert connectorless["reply_type"] == "service_choice"
    assert connectorless["expected_reply"] is True
    assert connectorless["meta_any"]["expected_reply_type"] == ["service_choice"]

    grounded = apply_booking_scenario_service_grounded_booking_expectations(
        {
            "reply_type": "service_choice",
            "meta": {
                "expected_reply_type": "service_choice",
                "expected_reply_reason": "collect:service",
            },
            "meta_any": {
                "expected_reply_type": ["service_choice"],
                "expected_reply_reason": ["collect:service"],
            },
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "expected_reply_type": "service_choice",
                    "reason": "collect:service",
                }
            ],
        },
        tags=["booking"],
        text="Хочу маникюр на вечер",
        service_candidates=("маникюр", "педикюр"),
        ctx=None,
    )

    assert grounded["reply_type"] == "time"
    assert grounded["meta"]["expected_reply_type"] == "time"
    assert "expected_reply_reason" not in grounded["meta"]
    assert grounded["meta_any"]["expected_reply_type"] == ["time"]
    assert "expected_reply_reason" not in grounded["meta_any"]
    assert grounded["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ]

    refined = apply_booking_scenario_service_grounded_booking_expectations(
        {
            "reply_type": "service_choice",
            "meta": {
                "expected_reply_type": "service_choice",
                "expected_reply_reason": "collect:service",
            },
            "meta_any": {
                "expected_reply_type": ["service_choice"],
                "expected_reply_reason": ["collect:service"],
            },
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "expected_reply_type": "service_choice",
                    "reason": "collect:service",
                }
            ],
        },
        tags=["booking"],
        text="Мне нужны услуги с укреплением ногтей.",
        service_candidates=("маникюр с укреплением ногтей", "педикюр"),
        ctx={"service": "маникюр"},
    )

    assert refined["reply_type"] == "time"
    assert refined["meta"]["expected_reply_type"] == "time"
    assert "expected_reply_reason" not in refined["meta"]
    assert refined["meta_any"]["expected_reply_type"] == ["time"]
    assert "expected_reply_reason" not in refined["meta_any"]
    assert refined["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ]


def test_shared_booking_progress_helpers_shape_collect_and_progress_followups():
    progressed = apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations(
        {"trace_contains": [{"stage": "question_contract", "expected_reply_type": "service_choice"}]},
        tags=["price"],
        text="Сколько стоит маникюр?",
        active_reply_type="service_choice",
        service_candidates=("маникюр", "педикюр"),
        ctx=None,
    )

    assert progressed["reply_type"] == "time"
    assert progressed["meta"]["expected_reply_contract_reason"] == "catalog_service_booking_progress"
    assert progressed["meta_any"]["expected_reply_type"] == ["time"]

    exact_time = apply_booking_scenario_exact_time_fill_collect_expectations(
        {"trace_contains": [{"stage": "pending_question_interaction"}]},
        tags=["time"],
        text="Давайте на 19:00",
        active_reply_type="time",
    )
    assert exact_time["reply_type"] == "name"
    assert exact_time["trace_contains"] == [
        {"stage": "question_contract", "expected_reply_type": "name"}
    ]

    partial_date = apply_booking_scenario_partial_date_fill_collect_expectations(
        {"trace_contains": [{"stage": "pending_question_interaction"}]},
        tags=["time"],
        text="Давайте завтра",
        active_reply_type="time",
    )
    assert partial_date["reply_type"] == "time"
    assert partial_date["trace_contains"] == [
        {"stage": "question_contract", "expected_reply_type": "time"}
    ]


def test_shared_booking_progress_helpers_shape_daypart_and_active_name_followups():
    daypart = apply_booking_scenario_grounded_partial_date_daypart_fill_expectations(
        {"trace_contains": [{"stage": "pending_question_interaction"}]},
        original_tags=["mixed_fill_plus_question"],
        tags=["time"],
        text="Мне нужна информация о свободных слотах на утро.",
        active_reply_type="time",
        partial_date_anchor_active=True,
    )

    assert daypart["reply_type"] == "time"
    assert daypart["trace_contains"] == [
        {"stage": "question_contract", "expected_reply_type": "time"}
    ]

    followup = apply_booking_scenario_active_name_time_availability_followup_expectations(
        {"trace_contains": [{"stage": "booking_interrupt", "decision": "info_reply"}]},
        original_tags=["booking"],
        tags=["booking"],
        text="А есть ли свободные слоты на 15:00?",
        active_reply_type="name",
    )

    assert followup["reply_type"] == "name"
    assert followup["meta_any"]["pending_question_owner"] == [
        "booking_time_availability_followup"
    ]
    assert any(
        entry.get("decision") == "booking_time_availability_followup"
        for entry in followup["trace_contains"]
    )


def test_shared_master_specialist_normalizers_retag_master_and_booking_paths():
    assert booking_scenario_normalize_pending_question_tags(
        "Какой мастер делает маникюр?",
        ["ask_about_requested_slot"],
    ) == ["master"]

    normalized_tags, changed = booking_scenario_normalize_active_name_master_info_tags(
        "Какие мастера доступны?",
        ["booking"],
        active_reply_type="name",
    )
    assert changed is True
    assert normalized_tags == ["master"]

    specialist_tags, specialist_changed = booking_scenario_normalize_active_time_specialist_master_tags(
        "Можно к мастеру Алия?",
        ["master"],
        active_reply_type=None,
    )
    assert specialist_changed is True
    assert specialist_tags == ["booking"]

    time_master_tags, time_master_changed = booking_scenario_normalize_active_time_master_info_tags(
        "Какие мастера есть?",
        ["booking"],
        active_reply_type="time",
    )
    assert time_master_changed is True
    assert time_master_tags == ["master"]


def test_shared_master_interrupt_helpers_shape_time_and_name_contracts():
    pending_master_expect = apply_booking_scenario_pending_master_info_interrupt_expectations(
        {},
        original_tags=["ask_about_requested_slot"],
        tags=["master"],
        text="Какой мастер делает маникюр?",
        active_reply_type="time",
    )

    assert pending_master_expect["reply_type"] == "time"
    assert "master" in pending_master_expect["info_sections"]
    assert pending_master_expect["meta_any"]["intent"] == ["master"]
    assert pending_master_expect["meta_any"]["pending_question_target"] == ["time"]

    active_name_expect = apply_booking_scenario_active_name_master_info_interrupt_expectations(
        {},
        original_tags=["booking"],
        tags=["master"],
        text="Какой мастер подойдет?",
        active_reply_type="name",
    )

    assert active_name_expect["reply_type"] == "name"
    assert "specialist" in active_name_expect["info_sections"]
    assert active_name_expect["meta_any"]["pending_question_target"] == ["specialist"]
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("pending_question_target") == "specialist"
        for entry in active_name_expect["trace_contains"]
    )

    active_time_expect = apply_booking_scenario_active_time_master_info_interrupt_expectations(
        {},
        original_tags=["booking"],
        tags=["master"],
        text="Какие мастера есть в субботу?",
        active_reply_type="time",
    )

    assert active_time_expect["reply_type"] == "time"
    assert active_time_expect["meta_any"]["pending_question_target"] == ["time"]
    assert active_time_expect["meta_any"]["booking_interrupt_info"] == [True]


def test_shared_specialist_followup_helpers_shape_availability_contracts():
    followup_expect = apply_booking_scenario_pending_specialist_availability_followup_expectations(
        {},
        original_tags=["ask_about_requested_slot"],
        tags=["master"],
        text="Какой мастер свободен завтра?",
        active_reply_type="time",
    )

    assert followup_expect["reply_type"] == "time"
    assert followup_expect["meta_any"]["pending_question_target"] == ["specialist"]
    assert followup_expect["meta_any"]["pending_question_interaction"] == [
        "specialist_availability_followup"
    ]
    assert any(
        entry.get("decision") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        for entry in followup_expect["trace_contains"]
    )

    transitioned_expect = apply_booking_scenario_grounded_time_specialist_availability_transition_expectations(
        {},
        original_tags=["slot_compare"],
        tags=["master"],
        text="Какой мастер свободен в это время?",
        active_reply_type="time",
    )

    assert transitioned_expect["reply_type"] == "name"
    assert transitioned_expect["meta_any"]["expected_reply_type"] == ["name"]
    assert transitioned_expect["meta_any"]["pending_question_target"] == ["specialist"]


def test_shared_active_time_specialist_followup_helper_shapes_booking_specialist_followup():
    updated = apply_booking_scenario_active_time_specialist_followup_expectations(
        {
            "trace_contains": [{"stage": "booking_interrupt", "pending_question_target": "specialist"}],
        },
        tags=["booking"],
        text="Можно к Алия?",
        active_reply_type="name",
    )

    assert updated["reply_type"] == "name"
    assert updated["meta_any"]["pending_question_target"] == ["specialist"]
    assert updated["meta_any"]["pending_question_owner"] == ["booking_specialist_followup"]
    assert any(
        entry.get("decision") == "booking_specialist_followup"
        and entry.get("active_question_relation") == "referent_followup"
        for entry in updated["trace_contains"]
    )


def test_merge_expectations_drops_info_override_without_info_tags():
    expect = _merge_expectations(
        ["booking"],
        {
            "info_sections": ["service_duration"],
            "expected_reply": "true",
        },
    )

    assert expect["info_sections"] == []
    assert expect["expected_reply"] is True


def test_merge_expectations_assigns_default_state_for_weak_tags():
    expect = _merge_expectations(["noise"], None)

    assert expect["state"] == "bot_active"


def test_merge_expectations_adds_pending_question_structured_contract():
    expect = _merge_expectations(["slot_compare"], None)

    assert expect["reply_type"] == "time"
    assert expect["meta_any"]["pending_question_act"] == ["slot_compare"]
    assert expect["meta_any"]["pending_question_target"] == ["time"]
    assert expect["meta_any"]["expected_reply_type"] == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_merge_expectations_retargets_named_specialist_pending_question_to_specialist():
    expect = _merge_expectations(
        ["ask_about_requested_slot"],
        None,
        text="Могу ли я записаться к Айгерим?",
    )

    assert expect["reply_type"] == "time"
    assert "master" in (expect.get("info_sections") or [])
    assert "specialist" in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("booking_interrupt_info") == [True]
    assert (expect.get("meta_any") or {}).get("intent") == ["master"]
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("decision") == "info_reply"
        and entry.get("pending_question_target") == "specialist"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_merge_expectations_keeps_time_target_for_u_vas_slot_question():
    expect = _merge_expectations(
        ["ask_about_requested_slot"],
        None,
        text="Какой у вас есть слоты на эту неделю?",
    )

    assert expect["reply_type"] == "time"
    assert "master" not in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("pending_question_target") == "specialist"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_downgrades_orphan_pending_question_fallback_to_service_choice():
    ctx = _module._build_context(random.Random(23))
    turns = [{"kind": "text", "text": "", "tags": ["ask_about_requested_slot"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(23))

    assert len(sanitized) == 1
    text = str(sanitized[0].get("text") or "").lower()
    assert "время" in text or "записаться" in text
    assert sanitized[0]["tags"] == ["booking"]
    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None


def test_sanitize_llm_turns_keeps_specialist_target_only_under_active_time_context():
    ctx = _module._build_context(random.Random(29))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Могу ли я записаться к Айгерим?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(29))

    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert expect.get("info_sections") == []
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == ["referent_followup"]
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("decision") == "info_reply"
        and entry.get("pending_question_target") == "specialist"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_booking_specialist_followup_preserves_active_name_contract():
    ctx = _module._build_context(random.Random(30))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне подходит 15:00.",
            "tags": ["time"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Сколько это стоит?",
            "tags": ["price"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться к Айгерим.",
            "tags": ["booking", "master"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(30))

    expect = sanitized[3].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert expect.get("info_sections") == []
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert (expect.get("meta_any") or {}).get("booking_interrupt_info") is None
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("pending_question_target") == "specialist"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_specialist_followup_after_cancel_and_promo():
    ctx = _module._build_context(random.Random(230))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне подходит 15:00.",
            "tags": ["time"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "А если не получится, то как отменить запись?",
            "tags": ["cancel"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Я слышал, у вас есть промо-акции?",
            "tags": ["promo"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": f"Я хотел бы записаться к {ctx['master']}.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(230))

    cancel_expect = sanitized[2].get("expect") or {}
    assert cancel_expect.get("reply_type") == "name"
    assert (cancel_expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]

    expect = sanitized[4].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "referent_followup"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "referent_followup"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_generic_master_info_interrupt_under_active_name_collect():
    ctx = _module._build_context(random.Random(30))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне подходит 15:00.",
            "tags": ["time"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Есть ли доступные специалисты?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "name",
                "meta_any": {"expected_reply_type": ["name"]},
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "name",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(30))

    assert sanitized[2]["tags"] == ["master"]
    expect = sanitized[2].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert "master" in (expect.get("info_sections") or [])
    assert "specialist" in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("intent") == ["master"]
    assert (expect.get("meta_any") or {}).get("source") == ["booking_info_contract"]
    assert (expect.get("meta_any") or {}).get("booking_interrupt_info") == [True]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("decision") == "info_reply"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("booking_interrupt_info") is True
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_time_target_for_u_vas_phrase_only_under_active_time_context():
    ctx = _module._build_context(random.Random(31))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какой у вас есть слоты на эту неделю?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(31))

    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert not any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("pending_question_target") == "specialist"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_time_collect_across_generic_info_interrupt():
    ctx = _module._build_context(random.Random(32))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "На какое время у вас есть свободные слоты?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Можно узнать подробнее о ваших услугах?",
            "tags": ["info"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне удобно время в 14:00.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(32))

    assert sanitized[3]["tags"] == ["time"]
    expect = sanitized[3].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )


def test_unsupported_service_followup_does_not_expect_booking_collect():
    turns = [
        {
            "kind": "text",
            "text": "делаете пирсинг?",
            "tags": ["interrupt", "consult"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "если да хочу записаться сегодня вечером",
            "tags": ["booking", "date", "time"],
            "expect": {
                "action": "collect",
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
    ]

    sanitized = sanitize_booking_scenario_llm_turns(turns, {}, random.Random(33))

    assert booking_scenario_looks_like_unsupported_service_inquiry(
        "делаете пирсинг?",
        ["interrupt", "consult"],
    )
    first_expect = sanitized[0].get("expect") or {}
    assert first_expect.get("action") == "fact"
    assert first_expect.get("reply_type") is None
    assert (first_expect.get("meta_any") or {}).get("action") == ["fact"]

    expect = sanitized[1].get("expect") or {}
    assert expect.get("action") == "fact"
    assert expect.get("reply_type") is None
    assert (expect.get("meta_any") or {}).get("action") == ["fact"]
    assert (expect.get("meta_any") or {}).get("intent") == [
        "services_overview",
        "out_of_domain",
    ]
    assert "expected_reply_type" not in (expect.get("meta_any") or {})
    assert not any(
        entry.get("stage") == "question_contract"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_booking_time_fill_after_slot_question():
    ctx = _module._build_context(random.Random(34))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "На какое время у вас есть свободные слоты?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне удобно время в 14:00.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(34))

    assert sanitized[2]["tags"] == ["time"]
    expect = sanitized[2].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_generic_master_info_interrupt_and_keeps_time_resume_contract_only_when_active():
    ctx = _module._build_context(random.Random(33))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "А кто будет делать маникюр?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(33))

    assert sanitized[1]["tags"] == ["master"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert expect.get("expected_reply") is True
    assert "master" in (expect.get("info_sections") or [])
    assert "specialist" in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("intent") == ["master"]
    assert (expect.get("meta_any") or {}).get("source") == ["booking_info_contract"]
    assert (expect.get("meta_any") or {}).get("booking_interrupt_info") == [True]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("decision") == "info_reply"
        and entry.get("pending_question_target") == "time"
        and entry.get("booking_interrupt_info") is True
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_generic_master_info_interrupt_kaкой_master_surface_only_when_active():
    ctx = _module._build_context(random.Random(35))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какой мастер делает педикюр?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(35))

    assert sanitized[1]["tags"] == ["master"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("source") == ["booking_info_contract"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_booking_tag_generic_master_info_interrupt_under_active_time():
    ctx = _module._build_context(random.Random(135))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какой у вас мастер?",
            "tags": ["booking"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(135))

    assert sanitized[1]["tags"] == ["master"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("intent") == ["master"]
    assert (expect.get("meta_any") or {}).get("source") == ["booking_info_contract"]
    assert (expect.get("meta_any") or {}).get("booking_interrupt_info") == [True]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") is None
    assert (expect.get("meta_any") or {}).get("pending_question_owner") is None
    assert (expect.get("meta_any") or {}).get("active_question_relation") is None
    assert any(
        entry.get("stage") == "booking_interrupt"
        and entry.get("decision") == "info_reply"
        and entry.get("pending_question_target") == "time"
        and entry.get("booking_interrupt_info") is True
        and "master" in (entry.get("info_sections") or [])
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_specialist_availability_followup_under_active_time_collect():
    ctx = _module._build_context(random.Random(36))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какой мастер свободен на этой неделе?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(36))

    assert sanitized[1]["tags"] == ["master"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert expect.get("expected_reply") is True
    assert "master" in (expect.get("info_sections") or [])
    assert "specialist" in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("source") == ["llm_policy_core"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "booking_interrupt"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_grounded_specialist_availability_transition():
    ctx = _module._build_context(random.Random(38))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на завтра?",
            "tags": ["mixed_fill_plus_question"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "А какие мастера доступны?",
            "tags": ["slot_compare"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(38))

    assert sanitized[2]["tags"] == ["master"]
    expect = sanitized[2].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert expect.get("expected_reply") is True
    assert "master" in (expect.get("info_sections") or [])
    assert "specialist" in (expect.get("info_sections") or [])
    assert (expect.get("meta_any") or {}).get("source") == ["llm_policy_core"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "specialist_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "booking_interrupt"
        for entry in (expect.get("trace_contains") or [])
    )


def test_merge_expectations_mixed_fill_plus_question_uses_resume_contract_only():
    expect = _merge_expectations(
        ["mixed_fill_plus_question"],
        None,
        text="Есть ли свободные слоты на утро?",
    )

    assert expect["reply_type"] == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_mixed_time_slot_question_only_when_active():
    ctx = _module._build_context(random.Random(37))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на утро?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(37))

    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_normalize_active_time_weak_time_question_tags_rewrites_time_to_resume_contract():
    normalized, changed = booking_scenario_normalize_active_time_weak_time_question_tags(
        "Есть ли свободные слоты на утро?",
        ["time"],
        active_reply_type="time",
    )

    assert changed is True
    assert normalized == ["mixed_fill_plus_question"]


def test_sanitize_llm_turns_preserves_time_after_weak_time_availability_question():
    ctx = _module._build_context(random.Random(71))
    turns = [
        {
            "kind": "text",
            "text": "Хотела бы записаться на маникюр на завтра.",
            "tags": ["booking"],
            "expect": {"reply_type": "time", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на утро?",
            "tags": ["time"],
            "expect": {"reply_type": "name"},
        },
        {
            "kind": "text",
            "text": "Я могу прийти только до 12:00.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(71))

    second_expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["time"]
    assert second_expect.get("reply_type") == "time"
    assert (second_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]

    third_expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["time"]
    assert third_expect.get("reply_type") == "time"
    assert (third_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (third_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (third_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_mixed_date_slot_question_only_when_active():
    ctx = _module._build_context(random.Random(41))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на завтра?",
            "tags": ["ask_about_requested_slot"],
            "expect": {},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(41))

    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_scrubs_stale_pending_question_act_from_mixed_override():
    ctx = _module._build_context(random.Random(42))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какой у вас есть свободный слот на завтра?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(42))

    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_explicit_time_fill_out_of_slot_constraint():
    ctx = _module._build_context(random.Random(44))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне подходит утро, например, в 10:00.",
            "tags": ["slot_constraint"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(44))

    assert sanitized[1]["tags"] == ["time"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_scrubs_stale_slot_constraint_expect_override_after_time_normalization():
    ctx = _module._build_context(random.Random(46))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться на 15:00.",
            "tags": ["slot_constraint"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_constraint"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(46))

    assert sanitized[1]["tags"] == ["time"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_partial_date_fill_to_name_collect():
    ctx = _module._build_context(random.Random(46))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Могу прийти в пятницу.",
            "tags": ["time"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(46))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["time"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_slot_constraint_without_grounded_time_fill():
    ctx = _module._build_context(random.Random(45))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "После обеда было бы удобнее.",
            "tags": ["slot_constraint"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(45))

    assert sanitized[1]["tags"] == ["slot_constraint"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == ["slot_constraint"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_ambiguous_lower_bound_time_fill_on_time_resume():
    ctx = _module._build_context(random.Random(145))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне нужно в 14:00 или позже.",
            "tags": ["time"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(145))

    assert sanitized[1]["tags"] == ["time"]
    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_time_resume_after_ambiguous_lower_bound_time_fill_and_pricing_interrupt():
    ctx = _module._build_context(random.Random(146))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на завтра?",
            "tags": ["mixed_fill_plus_question"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Мне нужно в 14:00 или позже.",
            "tags": ["time"],
            "expect": {},
        },
        {
            "kind": "text",
            "text": "Какова цена маникюра?",
            "tags": ["price"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(146))

    ambiguous_expect = sanitized[2].get("expect") or {}
    assert ambiguous_expect.get("reply_type") == "time"
    assert (ambiguous_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]

    pricing_expect = sanitized[3].get("expect") or {}
    assert pricing_expect.get("reply_type") == "time"
    assert pricing_expect.get("expected_reply") is True
    assert "pricing" in (pricing_expect.get("info_sections") or [])
    assert (pricing_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (pricing_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_downgrades_orphan_pending_question_after_booking_management_reset():
    ctx = _module._build_context(random.Random(43))
    turns = [
        {"kind": "text", "text": "Хочу записаться на маникюр.", "tags": ["booking"], "expect": {}},
        {"kind": "text", "text": "Можно на 18:30?", "tags": ["time"], "expect": {}},
        {"kind": "text", "text": "Меня зовут Айгуль.", "tags": ["name"], "expect": {}},
        {"kind": "text", "text": "Можно связаться с менеджером?", "tags": ["handoff", "human"], "expect": {}},
        {"kind": "text", "text": "Проверьте, пожалуйста, мою запись на завтра на 18:30.", "tags": ["check_booking"], "expect": {}},
        {"kind": "text", "text": "На какое время у вас есть слоты?", "tags": ["ask_about_requested_slot"], "expect": {}},
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(43))

    final_turn = sanitized[-1]
    assert final_turn["tags"] == ["booking"]
    expect = final_turn.get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_retags_malformed_check_booking_and_restores_slot_question_contract():
    ctx = _module._build_context(random.Random(243))
    turns = [
        {
            "kind": "text",
            "text": "Мне нужно записаться на маникюр на завтра.",
            "tags": ["check_booking"],
            "expect": {"expected_reply": True},
        },
        {
            "kind": "text",
            "text": "На какое время у вас есть свободные слоты?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "expected_reply": True,
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(243))

    first_turn = sanitized[0]
    first_expect = first_turn.get("expect") or {}
    assert first_turn["tags"] == ["booking"]
    assert first_expect.get("reply_type") == "time"

    second_turn = sanitized[1]
    second_expect = second_turn.get("expect") or {}
    assert second_turn["tags"] == ["ask_about_requested_slot"]
    assert second_expect.get("reply_type") == "time"
    assert (second_expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (second_expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (second_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (second_expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (second_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (second_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_booking_tag_slot_question_without_active_time():
    ctx = _module._build_context(random.Random(244))
    turns = [
        {
            "kind": "text",
            "text": "На какое время у вас есть свободные слоты?",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice", "expected_reply": True},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(244))

    expect = sanitized[0].get("expect") or {}
    assert sanitized[0]["tags"] == ["booking"]
    assert expect.get("reply_type") == "service_choice"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None


def test_sanitize_llm_turns_rewrites_check_booking_followup_and_clears_stale_service_choice():
    ctx = _module._build_context(random.Random(143))
    turns = [
        {"kind": "text", "text": "Хочу записаться на маникюр.", "tags": ["booking"], "expect": {}},
        {
            "kind": "media",
            "text": "Вот фото референса",
            "tags": ["media", "photo"],
            "expect": {},
        },
        {"kind": "text", "text": "Я хочу проверить свою запись.", "tags": ["check_booking"], "expect": {}},
        {
            "kind": "text",
            "text": "Когда у меня назначена встреча?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "expected_reply": True,
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
        {"kind": "text", "text": "Сколько я должна заплатить?", "tags": ["price"], "expect": {}},
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(143))

    followup_turn = sanitized[3]
    followup_expect = followup_turn.get("expect") or {}
    assert followup_turn["tags"] == ["check_booking"]
    assert followup_expect.get("expected_reply") is True
    assert followup_expect.get("reply_type") is None
    assert (followup_expect.get("meta_any") or {}).get("expected_reply_type") is None
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (followup_expect.get("trace_contains") or [])
    )

    pricing_turn = sanitized[4]
    pricing_expect = pricing_turn.get("expect") or {}
    assert pricing_turn["tags"] == ["price"]
    assert pricing_expect.get("reply_type") is None
    assert (pricing_expect.get("meta_any") or {}).get("expected_reply_type") is None


def test_sanitize_llm_turns_rewrites_check_booking_like_query_without_prior_management_tag():
    ctx = _module._build_context(random.Random(144))
    turns = [
        {"kind": "text", "text": "Хочу записаться на маникюр.", "tags": ["booking"], "expect": {}},
        {"kind": "media", "text": "Вот фото референса", "tags": ["media", "photo"], "expect": {}},
        {
            "kind": "text",
            "text": "Когда у меня назначена встреча?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "expected_reply": True,
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(144))

    followup_turn = sanitized[2]
    followup_expect = followup_turn.get("expect") or {}
    assert followup_turn["tags"] == ["check_booking"]
    assert followup_expect.get("expected_reply") is True
    assert followup_expect.get("reply_type") is None
    assert (followup_expect.get("meta_any") or {}).get("expected_reply_type") is None


def test_sanitize_llm_turns_marks_check_booking_entry_as_reply_required():
    ctx = _module._build_context(random.Random(145))
    turns = [
        {
            "kind": "text",
            "text": "Проверьте мою запись на четверг.",
            "tags": ["check_booking"],
            "expect": {"expected_reply": False},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(145))

    expect = sanitized[0].get("expect") or {}
    assert sanitized[0]["tags"] == ["check_booking"]
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None


def test_sanitize_llm_turns_marks_active_name_answer_as_reply_required():
    ctx = _module._build_context(random.Random(146))
    turns = [
        {
            "kind": "text",
            "text": f"Хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Завтра в 15:00",
            "tags": ["time"],
            "expect": {
                "reply_type": "name",
                "expected_reply": True,
                "meta_any": {"expected_reply_type": ["name"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "name"}
                ],
            },
        },
        {
            "kind": "text",
            "text": "Алина",
            "tags": ["name"],
            "expect": {
                "expected_reply": False,
                "meta_any": {"expected_reply_type": ["name"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "name"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(146))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["name"]
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") is None
    assert not any(
        entry.get("stage") in {"question_contract", "pending_question_interaction"}
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_rewrites_reschedule_followup_slot_compare_to_reschedule():
    ctx = _module._build_context(random.Random(46))
    turns = [
        {"kind": "text", "text": "Хочу записаться на маникюр.", "tags": ["booking"], "expect": {}},
        {
            "kind": "text",
            "text": "Мне нужно перенести свою запись на маникюр.",
            "tags": ["reschedule"],
            "expect": {"state": "pending", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Могу я перенести запись на послезавтра?",
            "tags": ["slot_compare"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(46))

    final_turn = sanitized[-1]
    assert final_turn["tags"] == ["reschedule"]
    expect = final_turn.get("expect") or {}
    assert expect.get("action") == "handoff"
    assert expect.get("state") == "pending"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_rewrites_reschedule_date_only_followup_to_reschedule():
    ctx = _module._build_context(random.Random(47))
    turns = [
        {"kind": "text", "text": f"Хочу записаться на {ctx['service']}.", "tags": ["booking"], "expect": {}},
        {
            "kind": "text",
            "text": "Я хочу перенести запись на коррекцию бровей.",
            "tags": ["reschedule"],
            "expect": {"state": "pending", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Нужно на следующую неделю.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Какое время вы можете предложить?",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(47))

    for idx in (2, 3):
        turn = sanitized[idx]
        expect = turn.get("expect") or {}
        assert turn["tags"] == ["reschedule"]
        assert expect.get("action") == "handoff"
        assert expect.get("state") == "pending"
        assert (expect.get("meta_any") or {}).get("pending_question_act") is None
        assert (expect.get("meta_any") or {}).get("pending_question_target") is None


def test_sanitize_llm_turns_normalizes_service_grounded_booking_reply_type_to_time():
    ctx = _module._build_context(random.Random(45))
    turns = [
        {
            "kind": "text",
            "text": "Я хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(45))

    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_time_after_service_refinement_under_active_time_continuity():
    ctx = _module._build_context(random.Random(145))
    ctx["service"] = "маникюр"
    turns = [
        {
            "kind": "text",
            "text": "Я хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
            },
        },
        {
            "kind": "text",
            "text": "Можно записать на завтра?",
            "tags": ["time"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
            },
        },
        {
            "kind": "text",
            "text": "Мне нужны услуги с укреплением ногтей.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta": {
                    "expected_reply_type": "service_choice",
                    "expected_reply_reason": "collect:service",
                },
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                    "expected_reply_reason": ["collect:service"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                        "reason": "collect:service",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(
        turns,
        ctx,
        random.Random(145),
        service_candidates=("маникюр", "маникюр с укреплением ногтей", "педикюр"),
    )

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["booking"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_reason") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_time_after_reschedule_service_refinement_and_requested_slot():
    ctx = _module._build_context(random.Random(246))
    ctx["service"] = "наращивание гелем"
    turns = [
        {
            "kind": "text",
            "text": "Салеметсиз бе, хочу записаться на Наращивание гелем.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
            },
        },
        {
            "kind": "text",
            "text": "Мне нужно перенести запись на дизайн ногтей.",
            "tags": ["reschedule"],
            "expect": {
                "reply_type": "service_choice",
                "meta": {
                    "expected_reply_type": "service_choice",
                    "expected_reply_reason": "collect:service",
                },
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                    "expected_reply_reason": ["collect:service"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                        "reason": "collect:service",
                    }
                ],
            },
        },
        {
            "kind": "text",
            "text": "Какой ближайший свободный слот?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta": {
                    "expected_reply_type": "service_choice",
                    "expected_reply_reason": "collect:service",
                },
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                    "expected_reply_reason": ["collect:service"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                        "reason": "collect:service",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(
        turns,
        ctx,
        random.Random(246),
        service_candidates=("наращивание гелем", "дизайн ногтей", "маникюр"),
    )

    reschedule_expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["reschedule"]
    assert reschedule_expect.get("reply_type") == "time"
    assert (reschedule_expect.get("meta") or {}).get("expected_reply_type") == "time"
    assert (reschedule_expect.get("meta") or {}).get("expected_reply_reason") is None

    requested_slot_expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["ask_about_requested_slot"]
    assert requested_slot_expect.get("reply_type") == "time"
    assert (requested_slot_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (requested_slot_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (requested_slot_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_multi_service_booking_request_stays_service_choice():
    ctx = _module._build_context(random.Random(966))
    turns = [
        {
            "kind": "text",
            "text": "маникюр педикюр керек",
            "tags": ["booking", "multi_service"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "expected_reply_type": ["time"],
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"},
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                ],
            },
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(966))

    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert (expect.get("meta_any") or {}).get("expected_reply_contract_reason") == [
        "multi_service_booking_clarify"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        and entry.get("reason") == "multi_service_booking_clarify"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_multi_service_hours_interrupt_clears_stale_time_followup():
    ctx = _module._build_context(random.Random(967))
    turns = [
        {
            "kind": "text",
            "text": "Мне нужен маникюр и педикюр.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
            },
        },
        {
            "kind": "text",
            "text": "Какой у вас график работы?",
            "tags": ["hours"],
            "expect": {
                "reply_type": "time",
                "expected_reply": True,
                "meta_any": {
                    "expected_reply_type": ["time"],
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"},
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(967))

    expect = sanitized[1].get("expect") or {}
    assert expect.get("reply_type") is None
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("expected_reply_type") is None
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert "hours" in (expect.get("info_sections") or [])
    assert not any(
        entry.get("stage") in {"question_contract", "pending_question_interaction"}
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_time_collect_for_specialist_target_followup_question():
    ctx = _module._build_context(random.Random(53))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Могу я выбрать специалиста?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(53))

    first_expect = sanitized[0].get("expect") or {}
    assert first_expect.get("reply_type") == "time"
    second_expect = sanitized[1].get("expect") or {}
    assert second_expect.get("reply_type") == "time"
    assert (second_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (second_expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (second_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_specialist_reference_booking_turn_under_active_time_collect():
    ctx = _module._build_context(random.Random(55))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Могу я выбрать специалиста?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
            },
        },
        {
            "kind": "text",
            "text": f"Хотелось бы к {ctx['master']}.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(55))

    expect = sanitized[2].get("expect") or {}
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_specialist_reference_service_choice_without_active_time_collect():
    ctx = _module._build_context(random.Random(57))
    turns = [
        {
            "kind": "text",
            "text": f"Хотелось бы к {ctx['master']}.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
            },
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(57))

    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]


def test_sanitize_llm_turns_normalizes_partial_date_mixed_question_under_active_time_collect():
    ctx = _module._build_context(random.Random(59))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": f"Хотелось бы к {ctx['master']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Можно ли записаться на завтра?",
            "tags": ["mixed_fill_plus_question"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"pending_question_target": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(59))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["booking"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_partial_date_slot_constraint_under_active_time_collect():
    ctx = _module._build_context(random.Random(60))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": f"Хотелось бы к {ctx['master']}.",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
            },
        },
        {
            "kind": "text",
            "text": "Мне нужно записаться на завтра.",
            "tags": ["slot_constraint"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"pending_question_act": ["slot_constraint"]},
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_constraint",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(60))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["time"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_availability_question_as_mixed_fill_plus_question():
    ctx = _module._build_context(random.Random(61))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на завтра?",
            "tags": ["mixed_fill_plus_question"],
            "expect": {"reply_type": "time"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(61))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None


def test_sanitize_llm_turns_normalizes_grounded_partial_date_daypart_fill_to_time():
    ctx = _module._build_context(random.Random(171))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться на завтра.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Мне нужна информация о свободных слотах на утро.",
            "tags": ["mixed_fill_plus_question"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(171))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["time"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_partial_date_anchor_resets_after_generic_hours_interrupt():
    ctx = _module._build_context(random.Random(173))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться на следующую неделю.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А во сколько вы работаете?",
            "tags": ["hours"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
        {
            "kind": "text",
            "text": "У вас есть свободные слоты на утро?",
            "tags": ["mixed_fill_plus_question"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
        {
            "kind": "text",
            "text": f"А сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(173))

    daypart_expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["mixed_fill_plus_question"]
    assert daypart_expect.get("reply_type") == "time"
    assert (daypart_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (daypart_expect.get("trace_contains") or [])
    )

    price_expect = sanitized[4].get("expect") or {}
    assert price_expect.get("reply_type") == "time"
    assert (price_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert "pricing" in (price_expect.get("info_sections") or [])
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (price_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_mixed_daypart_question_without_grounded_partial_date():
    ctx = _module._build_context(random.Random(172))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Мне нужна информация о свободных слотах на утро.",
            "tags": ["mixed_fill_plus_question"],
            "expect": {
                "reply_type": "time",
                "meta_any": {"expected_reply_type": ["time"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "time"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(172))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]


def test_sanitize_llm_turns_normalizes_named_specialist_master_question_under_active_time_collect():
    ctx = _module._build_context(random.Random(62))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": f"Есть ли возможность сделать это у {ctx['master']}?",
            "tags": ["master"],
            "expect": {
                "reply_type": "time",
                "info_sections": ["master"],
                "meta_any": {"intent": ["master"]},
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(62))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["booking"]
    assert expect.get("reply_type") == "time"
    assert expect.get("info_sections") == []
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("intent") is None
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_named_specialist_followup_after_time_fill():
    ctx = _module._build_context(random.Random(63))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Когда у вас есть свободные слоты?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Может быть, в пятницу после 3?",
            "tags": ["time"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Есть ли возможность сделать это у {ctx['master']}?",
            "tags": ["master"],
            "expect": {
                "reply_type": "name",
                "info_sections": ["master", "specialist"],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(63))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "time"
    assert expect.get("info_sections") == []
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "referent_followup"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_rewrites_slot_compare_named_specialist_choice_to_time_followup():
    turns = [
        {
            "kind": "text",
            "text": "Мне нужно записаться на маникюр на завтра.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А можно выбрать Айгерим?",
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "name",
                "info_sections": ["master", "specialist"],
                "meta_any": {
                    "pending_question_target": ["specialist"],
                    "expected_reply_type": ["time"],
                    "booking_interrupt_info": [True],
                    "intent": ["master"],
                },
            },
        },
        {
            "kind": "text",
            "text": "Какова цена на маникюр?",
            "tags": ["price"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, _module._build_context(random.Random(64)), random.Random(64))

    specialist_turn = sanitized[2]
    specialist_expect = specialist_turn.get("expect") or {}
    assert specialist_turn["tags"] == ["booking"]
    assert specialist_expect.get("reply_type") == "time"
    assert specialist_expect.get("info_sections") == []
    assert (specialist_expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (specialist_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "time"
        for entry in (specialist_expect.get("trace_contains") or [])
    )

    price_expect = sanitized[3].get("expect") or {}
    assert price_expect.get("reply_type") == "time"
    assert "pricing" in (price_expect.get("info_sections") or [])
    assert (price_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]


def test_sanitize_llm_turns_named_specialist_preference_availability_keeps_generalized_followup():
    ctx = _module._build_context(random.Random(631))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Когда будет ближайшая свободная дата?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "У вас есть свободные слоты на выходные?",
            "tags": ["slot_constraint"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Я предпочитаю {ctx['master']}, она свободна?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(631))

    expect = sanitized[4].get("expect") or {}
    meta_any = expect.get("meta_any") or {}

    assert sanitized[4]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert meta_any.get("pending_question_target") == ["specialist"]
    assert meta_any.get("active_question_relation") == ["referent_followup"]
    assert meta_any.get("expected_reply_type") == ["time"]
    assert meta_any.get("pending_question_act") is None
    assert meta_any.get("pending_question_owner") is None
    assert meta_any.get("pending_question_interaction") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_active_time_specialist_followup_compiler_drops_stale_pending_trace():
    raw_expect = {
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
    }

    assert should_compile_active_time_specialist_followup_expectations(raw_expect) is True

    compiled = compile_active_time_specialist_followup_expectations(raw_expect)

    assert compiled["reply_type"] == "time"
    assert (compiled.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (compiled.get("meta_any") or {}).get("active_question_relation") == [
        "referent_followup"
    ]
    assert (compiled.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (compiled.get("meta_any") or {}).get("pending_question_interaction") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (compiled.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (compiled.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_slot_constraint_named_specialist_preference_to_referent_followup():
    ctx = _module._build_context(random.Random(632))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Когда будет ближайшая свободная дата?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Я предпочитаю {ctx['master']}, она свободна?",
            "tags": ["slot_constraint"],
            "expect": {"reply_type": "time"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(632))

    expect = sanitized[3].get("expect") or {}
    meta_any = expect.get("meta_any") or {}

    assert sanitized[3]["tags"] == ["slot_constraint"]
    assert expect.get("reply_type") == "time"
    assert expect.get("expected_reply") is True
    assert meta_any.get("pending_question_target") == ["specialist"]
    assert meta_any.get("active_question_relation") == ["referent_followup"]
    assert meta_any.get("expected_reply_type") == ["time"]
    assert meta_any.get("pending_question_act") is None
    assert meta_any.get("pending_question_owner") is None
    assert meta_any.get("pending_question_interaction") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_price_interrupt_preserves_active_time_before_specialist_followup():
    ctx = _module._build_context(random.Random(63))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": f"Можно к {ctx['master']}?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {"stage": "question_contract", "expected_reply_type": "service_choice"}
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(63))

    interrupt_expect = sanitized[1].get("expect") or {}
    assert interrupt_expect.get("reply_type") == "time"
    assert (interrupt_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (interrupt_expect.get("trace_contains") or [])
    )

    followup_expect = sanitized[2].get("expect") or {}
    assert followup_expect.get("reply_type") == "time"
    assert (followup_expect.get("meta_any") or {}).get("pending_question_target") == ["specialist"]
    assert (followup_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "time"
        for entry in (followup_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_service_choice_price_interrupt_advances_to_time_on_grounded_service():
    ctx = _module._build_context(random.Random(63))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": f"Сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {"reply_type": "service_choice"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(63))

    interrupt_expect = sanitized[1].get("expect") or {}
    assert interrupt_expect.get("reply_type") == "time"
    assert (interrupt_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert (interrupt_expect.get("meta_any") or {}).get("expected_reply_contract_reason") == [
        "catalog_service_booking_progress"
    ]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        and entry.get("reason") == "catalog_service_booking_progress"
        for entry in (interrupt_expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_grounded_time_availability_probe_to_time_fill():
    ctx = _module._build_context(random.Random(64))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Есть ли варианты на 15:00?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(64))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["time"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_question_like_explicit_time_fill_to_time():
    ctx = _module._build_context(random.Random(64))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Может быть, на 14:00?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(64))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["time"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_question_like_daypart_exact_time_fill_to_time():
    ctx = _module._build_context(random.Random(64))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']} на завтра.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А можно на утро, скажем, на 10 утра?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(64))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["time"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_slot_compare_explicit_time_fill_after_info_interrupts():
    ctx = _module._build_context(random.Random(164))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": f"Сколько стоит {ctx['service']}?",
            "tags": ["price"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А есть ли какие-то скидки?",
            "tags": ["promo"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Как долго длится процедура?",
            "tags": ["duration"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Можно записаться на 15:00?",
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_compare"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_compare",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(164))

    expect = sanitized[4].get("expect") or {}
    assert sanitized[4]["tags"] == ["time"]
    assert expect.get("reply_type") == "name"
    assert expect.get("expected_reply") is True
    assert (expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (expect.get("meta_any") or {}).get("pending_question_target") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_generic_slot_compare_without_exact_time():
    ctx = _module._build_context(random.Random(165))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Лучше утром или вечером?",
            "tags": ["slot_compare"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(165))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["slot_compare"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == ["slot_compare"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_time_availability_followup():
    ctx = _module._build_context(random.Random(64))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Мне нужно время на 14:00.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А есть ли свободные слоты на 15:00?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(64))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_time_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_requested_slot_followup_without_temporal_scope():
    ctx = _module._build_context(random.Random(964))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']} на понедельник.",
            "tags": ["booking"],
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на утро?",
            "tags": ["time"],
        },
        {
            "kind": "text",
            "text": "На какое время вы можете меня записать?",
            "tags": ["ask_about_requested_slot"],
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(964))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_specialist_time_followup_after_master_interrupt():
    ctx = _module._build_context(random.Random(965))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
        },
        {
            "kind": "text",
            "text": "Можно записаться на завтра в 15:00?",
            "tags": ["time"],
        },
        {
            "kind": "text",
            "text": f"Как насчет специалиста {ctx['master']}?",
            "tags": ["booking", "master"],
        },
        {
            "kind": "text",
            "text": "Могу я записаться к ней на 14:00?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {"expected_reply_type": ["service_choice"]},
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(965))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_time_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_deictic_time_availability_followup():
    ctx = _module._build_context(random.Random(164))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться на завтра в 15:00.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А есть ли у вас места в это время?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(164))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_time_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_deictic_time_occupancy_followup():
    ctx = _module._build_context(random.Random(165))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Могу ли я записаться на 15:00?",
            "tags": ["time"],
            "expect": {"reply_type": "name"},
        },
        {
            "kind": "text",
            "text": "А если это время занято?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(165))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_time_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_preserves_active_name_deictic_day_availability_followup():
    ctx = _module._build_context(random.Random(264))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Я хочу записаться на 15:00.",
            "tags": ["booking"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "У вас есть свободные слоты на этот день?",
            "tags": ["booking"],
            "expect": {
                "reply_type": "service_choice",
                "meta_any": {
                    "expected_reply_type": ["service_choice"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(264))

    expect = sanitized[3].get("expect") or {}
    assert sanitized[3]["tags"] == ["booking"]
    assert expect.get("reply_type") == "name"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("pending_question_interaction") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_owner") == [
        "booking_time_availability_followup"
    ]
    assert (expect.get("meta_any") or {}).get("active_question_relation") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_ungrounded_slot_question_as_pending_question():
    ctx = _module._build_context(random.Random(65))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время свободно?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "Есть ли варианты по времени?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(65))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]


def test_sanitize_llm_turns_normalizes_question_like_daypart_constraint_to_slot_constraint():
    ctx = _module._build_context(random.Random(66))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "На какое время лучше записаться?",
            "tags": ["ask_about_requested_slot"],
            "expect": {"reply_type": "time"},
        },
        {
            "kind": "text",
            "text": "А можно на утро?",
            "tags": ["ask_about_requested_slot"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["ask_about_requested_slot"],
                    "pending_question_target": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(66))

    expect = sanitized[2].get("expect") or {}
    assert sanitized[2]["tags"] == ["slot_constraint"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == ["slot_constraint"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_slot_constraint_requested_slot_overclaim():
    ctx = _module._build_context(random.Random(67))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Какое время доступно?",
            "tags": ["slot_constraint"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_constraint"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(67))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_slot_compare_requested_slot_overclaim():
    ctx = _module._build_context(random.Random(67))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Какое время доступно?",
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_compare"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_compare",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(67))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_normalizes_slot_compare_days_availability_to_requested_slot():
    ctx = _module._build_context(random.Random(167))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Какие дни у вас доступны?",
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_compare"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_compare",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(167))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["ask_about_requested_slot"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "ask_about_requested_slot"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (expect.get("trace_contains") or [])
    )


@pytest.mark.parametrize(
    "text",
    [
        "Есть ли у вас время на завтра?",
        "У вас есть время на завтра?",
    ],
)
def test_sanitize_llm_turns_normalizes_slot_compare_partial_date_availability_to_slot_constraint(
    text,
):
    ctx = _module._build_context(random.Random(168))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": text,
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_compare"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_compare",
                        "pending_question_target": "time",
                    },
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "time",
                    },
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(168))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["slot_constraint"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == [
        "slot_constraint"
    ]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (expect.get("trace_contains") or [])
    )


@pytest.mark.parametrize(
    "text",
    [
        "Есть ли у вас время на завтра утром или вечером?",
        "У вас есть время на завтра утром или вечером?",
    ],
)
def test_sanitize_llm_turns_keeps_slot_compare_partial_date_with_explicit_alternatives(
    text,
):
    ctx = _module._build_context(random.Random(169))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": text,
            "tags": ["slot_compare"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_compare"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_compare",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(169))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["slot_compare"]
    assert (expect.get("meta_any") or {}).get("pending_question_act") == ["slot_compare"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        and entry.get("pending_question_target") == "time"
        for entry in (expect.get("trace_contains") or [])
    )


def test_sanitize_llm_turns_keeps_slot_constraint_requested_slot_temporal_constraint():
    ctx = _module._build_context(random.Random(68))
    turns = [
        {
            "kind": "text",
            "text": f"Я хочу записаться на {ctx['service']}.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Какое время доступно после обеда?",
            "tags": ["slot_constraint"],
            "expect": {
                "reply_type": "time",
                "meta_any": {
                    "pending_question_act": ["slot_constraint"],
                    "pending_question_target": ["time"],
                    "expected_reply_type": ["time"],
                },
                "trace_contains": [
                    {
                        "stage": "pending_question_interaction",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    }
                ],
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(68))

    expect = sanitized[1].get("expect") or {}
    assert sanitized[1]["tags"] == ["slot_constraint"]
    assert expect.get("reply_type") == "time"
    assert (expect.get("meta_any") or {}).get("pending_question_act") == ["slot_constraint"]
    assert (expect.get("meta_any") or {}).get("pending_question_target") == ["time"]


def test_sanitize_llm_turns_keeps_generic_booking_service_choice_when_service_missing():
    ctx = _module._build_context(random.Random(47))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        }
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(47))

    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("action") == "collect"
    assert (expect.get("meta") or {}).get("action") == "collect"
    assert (expect.get("meta") or {}).get("expected_reply_type") == "service_choice"
    assert (expect.get("meta_any") or {}).get("action") == ["collect"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert (expect.get("trace_contains") or []) == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]


def test_sanitize_llm_turns_hardens_weekend_booking_service_followup_after_hours_interrupt():
    ctx = _module._build_context(random.Random(148))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "А по выходным вы работаете?",
            "tags": ["hours"],
            "expect": {"info_sections": ["hours"], "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Можно записаться на выходные?",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice", "state": "bot_active", "expected_reply": True},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(148))

    expect = sanitized[2].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("action") == "collect"
    assert expect.get("state") == "bot_active"
    assert (expect.get("meta") or {}) == {
        "action": "collect",
        "source": "llm_policy_core",
        "tool_action": "collect",
        "expected_reply_type": "service_choice",
        "expected_reply_reason": "collect:service",
    }
    assert (expect.get("meta_any") or {}).get("action") == ["collect"]
    assert (expect.get("meta_any") or {}).get("source") == ["llm_policy_core"]
    assert (expect.get("meta_any") or {}).get("tool_action") == ["collect"]
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert (expect.get("meta_any") or {}).get("expected_reply_reason") == ["collect:service"]
    assert (expect.get("trace_contains") or []) == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]


def test_sanitize_llm_turns_retags_booking_tag_mixed_slot_followup_when_time_context_is_active():
    ctx = _module._build_context(random.Random(49))
    turns = [
        {
            "kind": "text",
            "text": "Я хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
        {
            "kind": "text",
            "text": "Есть ли свободные слоты на завтра?",
            "tags": ["booking"],
            "expect": {"reply_type": "service_choice"},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(49))

    first_expect = sanitized[0].get("expect") or {}
    assert first_expect.get("reply_type") == "time"
    assert sanitized[1]["tags"] == ["mixed_fill_plus_question"]
    second_expect = sanitized[1].get("expect") or {}
    assert second_expect.get("reply_type") == "time"
    assert (second_expect.get("meta_any") or {}).get("expected_reply_type") == ["time"]


def test_sanitize_llm_turns_rewrites_master_tag_without_master_cues():
    ctx = _module._build_context(random.Random(17))
    turns = [{"kind": "text", "text": "Что вы можете предложить?", "tags": ["master"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(17))

    assert len(sanitized) == 1
    text = str(sanitized[0].get("text") or "").lower()
    assert "мастер" in text or "специалист" in text
    expect = sanitized[0].get("expect") or {}
    assert sanitized[0]["tags"] == ["booking"]
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("info_sections") == []


def test_sanitize_llm_turns_keeps_master_tag_with_master_cues():
    ctx = _module._build_context(random.Random(19))
    source = f"Можно к мастеру {ctx['master']}?"
    turns = [{"kind": "text", "text": source, "tags": ["master"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(19))

    assert len(sanitized) == 1
    assert sanitized[0]["text"] == source


def test_sanitize_llm_turns_normalizes_standalone_named_specialist_booking_to_service_choice():
    ctx = _module._build_context(random.Random(20))
    source = f"Можно к мастеру {ctx['master']}?"
    turns = [{"kind": "text", "text": source, "tags": ["master"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(20))

    assert len(sanitized) == 1
    assert sanitized[0]["tags"] == ["booking"]
    expect = sanitized[0].get("expect") or {}
    assert expect.get("reply_type") == "service_choice"
    assert expect.get("info_sections") == []
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["service_choice"]
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (expect.get("trace_contains") or [])
    )


def test_generate_llm_dialogs_retries_after_json_error(monkeypatch):
    calls = {"parse": 0, "openai": 0}

    def _fake_openai(
        prompt, *, api_key, model, base_url, request_timeout=40.0, max_tokens=1800
    ):
        calls["openai"] += 1
        return "{}"

    def _fake_parse(_content, *, repair_fn=None):
        calls["parse"] += 1
        if calls["parse"] == 1:
            raise json.JSONDecodeError("bad", "{", 0)
        return {
            "dialogs": [
                {
                    "goal": "booking",
                    "turns": [
                        {
                            "kind": "text",
                            "text": "Хочу записаться",
                            "tags": ["booking"],
                            "expect": {
                                "action": None,
                                "info_sections": [],
                                "reply_type": "service_choice",
                                "state": "bot_active",
                                "expected_reply": True,
                                "allow_booking_stall": False,
                            },
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(_module, "_call_openai", _fake_openai)
    monkeypatch.setattr(_module, "_parse_llm_json", _fake_parse)
    monkeypatch.setattr(
        _module,
        "_infer_context_from_dialog",
        lambda _dialog, _rng, scenario_context=None: {"service": "Стрижка"},
    )
    monkeypatch.setattr(
        _module,
        "_ensure_required_tags",
        lambda turns, _ctx, *, max_turns, coverage=None: turns,
    )
    monkeypatch.setattr(_module, "_sanitize_llm_turns", lambda turns, _ctx, _rng: turns)
    monkeypatch.setattr(_module, "_prune_turns", lambda turns, _max_turns, _required: turns)
    monkeypatch.setattr(
        _module,
        "_media_turn",
        lambda _ctx, *, mode, kind: {"kind": mode, "text": kind, "tags": ["media"], "expect": {}},
    )

    dialogs = _module._generate_llm_dialogs(
        random.Random(7),
        count=1,
        min_turns=10,
        max_turns=15,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        model="gpt-5.4-nano-2026-03-17",
        base_url="https://api.openai.com",
        api_key="test-key",
        coverage=["booking", "info", "interrupt", "handoff"],
        seed=7,
        llm_batch_size=1,
        llm_max_attempts=2,
        llm_request_timeout=15.0,
        llm_attempt_backoff=0.0,
        progress_stderr=False,
    )

    assert len(dialogs) == 1
    assert calls["openai"] == 2
    assert calls["parse"] == 2


def test_ensure_required_tags_no_longer_adds_check_booking_and_confirm_per_dialog():
    ctx = _module._build_context(random.Random(3))
    turns = [
        {"kind": "text", "text": "Хочу записаться", "tags": ["booking"], "expect": {}},
        {"kind": "text", "text": "Можно на 19:00?", "tags": ["time"], "expect": {}},
        {"kind": "text", "text": "Меня зовут Лена", "tags": ["name"], "expect": {}},
    ]

    enriched = _module._ensure_required_tags(
        turns,
        ctx,
        max_turns=12,
        coverage=["booking", "info", "interrupt"],
    )
    tags = {tag for turn in enriched for tag in (turn.get("tags") or [])}

    assert "check_booking" not in tags
    assert "confirm" not in tags


def test_ensure_booking_management_coverage_adds_check_booking_and_confirm_across_batch():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {"kind": "text", "text": "Хочу записаться", "tags": ["booking"], "expect": {}},
                {"kind": "text", "text": "Можно на 19:00?", "tags": ["time"], "expect": {}},
                {"kind": "text", "text": "Меня зовут Лена", "tags": ["name"], "expect": {}},
            ],
        },
        {
            "dialog_id": 2,
            "turns": [
                {"kind": "text", "text": "Хочу записаться на педикюр", "tags": ["booking"], "expect": {}},
                {"kind": "text", "text": "Можно завтра?", "tags": ["time"], "expect": {}},
            ],
        },
    ]

    enriched = _module._ensure_booking_management_coverage(
        dialogs,
        coverage=["booking", "info", "interrupt"],
        max_turns=12,
        rng=random.Random(11),
        scenario_context=None,
    )
    tag_sets = [
        {tag for turn in dialog.get("turns") or [] for tag in (turn.get("tags") or [])}
        for dialog in enriched
    ]

    assert any("check_booking" in tags for tags in tag_sets)
    assert any("confirm" in tags for tags in tag_sets)
    assert not any({"check_booking", "confirm"} <= tags for tags in tag_sets)


def test_repair_post_coverage_orphan_pending_question_turns_rewrites_orphan_turn():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Можно на 19:00?",
                    "tags": ["time"],
                    "expect": {"reply_type": "name", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Меня зовут Лена",
                    "tags": ["name"],
                    "expect": {"reply_type": None, "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "На какое время лучше записаться?",
                    "tags": ["ask_about_requested_slot"],
                    "expect": {},
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(
        dialogs
    )

    repaired_turn = repaired[0]["turns"][3]
    assert repaired_turn["tags"] == ["booking"]
    assert repaired_turn["expect"]["reply_type"] == "service_choice"
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["service_choice"]
    assert repaired_turn["expect"]["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]


def test_repair_post_coverage_orphan_pending_question_turns_rewrites_reschedule_followup():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Мне нужно перенести запись на маникюр.",
                    "tags": ["reschedule"],
                    "expect": {"state": "pending", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Могу я перенести запись на послезавтра?",
                    "tags": ["slot_compare"],
                    "expect": {},
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["tags"] == ["reschedule"]
    assert repaired_turn["expect"]["action"] == "handoff"
    assert repaired_turn["expect"]["state"] == "pending"
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_act") is None
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_target") is None


def test_advance_booking_scenario_management_context_clears_reschedule_after_non_pending_turn():
    assert (
        advance_booking_scenario_management_context(
            "reschedule",
            tags=["confirm"],
            expect={"action": None, "state": "bot_active", "expected_reply": True},
        )
        is None
    )


def test_reschedule_management_context_does_not_rewrite_time_fill_after_bot_active_confirm():
    ctx = _module._build_context(random.Random(71))
    turns = [
        {
            "kind": "text",
            "text": "Хочу записаться на маникюр.",
            "tags": ["booking"],
            "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Не могу в это время, можно перенести на субботу?",
            "tags": ["reschedule"],
            "expect": {"action": "collect", "reply_type": "time", "state": "pending", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Подтвердите мою запись на субботу.",
            "tags": ["confirm"],
            "expect": {"action": None, "state": "bot_active", "expected_reply": True},
        },
        {
            "kind": "text",
            "text": "Можно на 19:00?",
            "tags": ["booking"],
            "expect": {},
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(71))
    repaired = _module._repair_post_coverage_orphan_pending_question_turns(
        [{"dialog_id": 1, "turns": sanitized}]
    )

    repaired_turn = repaired[0]["turns"][3]
    assert repaired_turn["tags"] == ["booking"]
    assert repaired_turn["expect"]["action"] == "collect"
    assert repaired_turn["expect"]["reply_type"] == "time"
    assert repaired_turn["expect"]["state"] == "bot_active"


def test_repair_post_coverage_orphan_pending_question_turns_rewrites_check_booking_followup():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Проверьте, пожалуйста, мою запись на завтра на 18:30.",
                    "tags": ["check_booking"],
                    "expect": {"expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Когда у меня назначена встреча?",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                        "trace_contains": [
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "service_choice",
                            }
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["tags"] == ["check_booking"]
    assert repaired_turn["expect"]["expected_reply"] is True
    assert repaired_turn["expect"].get("reply_type") is None
    assert (repaired_turn["expect"].get("meta_any") or {}).get("expected_reply_type") is None
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_marks_check_booking_entry_as_reply_required():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Проверьте мою запись на четверг.",
                    "tags": ["check_booking"],
                    "expect": {"expected_reply": False},
                }
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    expect = repaired[0]["turns"][0].get("expect") or {}
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None


def test_sanitize_llm_turns_relaxes_confirm_after_active_check_booking():
    ctx = _module._build_context(random.Random(531))
    turns = [
        {
            "kind": "text",
            "text": "Проверьте мою запись на четверг.",
            "tags": ["check_booking"],
            "expect": {"expected_reply": False},
        },
        {
            "kind": "text",
            "text": "Подтвердите, пожалуйста, мою запись на четверг.",
            "tags": ["confirm"],
            "expect": {
                "action": "booking_prompt",
                "reply_type": "time",
                "expected_reply": True,
                "meta_any": {"expected_reply_type": ["time"]},
            },
        },
    ]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(531))

    expect = sanitized[1]["expect"]
    assert sanitized[1]["tags"] == ["confirm"]
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name", "time"]


def test_repair_post_coverage_orphan_pending_question_turns_relaxes_confirm_after_active_check_booking():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Проверьте мою запись на четверг.",
                    "tags": ["check_booking"],
                    "expect": {"expected_reply": False},
                },
                {
                    "kind": "text",
                    "text": "Подтвердите, пожалуйста, мою запись на четверг.",
                    "tags": ["confirm"],
                    "expect": {
                        "action": "booking_prompt",
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["time"]},
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    assert repaired[0]["turns"][1]["tags"] == ["confirm"]
    expect = repaired[0]["turns"][1]["expect"]
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") == ["name", "time"]


def test_repair_post_coverage_orphan_pending_question_turns_marks_active_name_answer_as_reply_required():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться на маникюр.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Завтра в 15:00",
                    "tags": ["time"],
                    "expect": {
                        "reply_type": "name",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["name"]},
                        "trace_contains": [
                            {"stage": "question_contract", "expected_reply_type": "name"}
                        ],
                    },
                },
                {
                    "kind": "text",
                    "text": "Алина",
                    "tags": ["name"],
                    "expect": {
                        "expected_reply": False,
                        "meta_any": {"expected_reply_type": ["name"]},
                        "trace_contains": [
                            {"stage": "question_contract", "expected_reply_type": "name"}
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    expect = repaired[0]["turns"][2].get("expect") or {}
    assert expect.get("expected_reply") is True
    assert expect.get("reply_type") is None
    assert (expect.get("meta_any") or {}).get("expected_reply_type") is None
    assert not any(
        entry.get("stage") in {"question_contract", "pending_question_interaction"}
        for entry in (expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_restores_slot_question_after_malformed_check_booking():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Мне нужно записаться на маникюр на завтра.",
                    "tags": ["check_booking"],
                    "expect": {"expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "На какое время у вас есть свободные слоты?",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                        "trace_contains": [
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "service_choice",
                            }
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    first_turn = repaired[0]["turns"][0]
    first_expect = first_turn["expect"]
    assert first_turn["tags"] == ["booking"]
    assert first_expect["reply_type"] == "time"

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["ask_about_requested_slot"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["pending_question_act"] == ["ask_about_requested_slot"]
    assert repaired_expect["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_slot_constraint_requested_slot_overclaim():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Какое время доступно?",
                    "tags": ["slot_constraint"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_constraint"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_constraint",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["ask_about_requested_slot"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["pending_question_act"] == ["ask_about_requested_slot"]
    assert repaired_expect["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_slot_compare_requested_slot_overclaim():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Какое время доступно?",
                    "tags": ["slot_compare"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_compare"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_compare",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["ask_about_requested_slot"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["pending_question_act"] == ["ask_about_requested_slot"]
    assert repaired_expect["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_slot_compare_days_availability():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Какие дни у вас доступны?",
                    "tags": ["slot_compare"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_compare"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_compare",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["ask_about_requested_slot"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["pending_question_act"] == ["ask_about_requested_slot"]
    assert repaired_expect["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


@pytest.mark.parametrize(
    "text",
    [
        "Есть ли у вас время на завтра?",
        "У вас есть время на завтра?",
    ],
)
def test_repair_post_coverage_orphan_pending_question_turns_normalizes_slot_compare_partial_date_availability(
    text,
):
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": text,
                    "tags": ["slot_compare"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_compare"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_compare",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["slot_constraint"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["pending_question_act"] == ["slot_constraint"]
    assert repaired_expect["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        and entry.get("pending_question_target") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


@pytest.mark.parametrize(
    "text",
    [
        "Есть ли у вас время на завтра утром или вечером?",
        "У вас есть время на завтра утром или вечером?",
    ],
)
def test_repair_post_coverage_orphan_pending_question_turns_keeps_slot_compare_partial_date_with_explicit_alternatives(
    text,
):
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": text,
                    "tags": ["slot_compare"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_compare"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_compare",
                                "pending_question_target": "time",
                            }
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["slot_compare"]
    assert repaired_expect["meta_any"]["pending_question_act"] == ["slot_compare"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_compare"
        and entry.get("pending_question_target") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_grounded_partial_date_daypart_fill():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться на маникюр.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Я хочу записаться на завтра.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Мне нужна информация о свободных слотах на утро.",
                    "tags": ["mixed_fill_plus_question"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["time"]},
                        "trace_contains": [
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            }
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][2]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["time"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert repaired_expect["meta_any"].get("pending_question_act") is None
    assert repaired_expect["meta_any"].get("pending_question_target") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_partial_date_fill():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться на маникюр.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Могу прийти в пятницу.",
                    "tags": ["time"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["ask_about_requested_slot"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "ask_about_requested_slot",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["time"]
    assert repaired_expect["reply_type"] == "time"
    assert repaired_expect["meta_any"]["expected_reply_type"] == ["time"]
    assert repaired_expect["meta_any"].get("pending_question_act") is None
    assert repaired_expect["meta_any"].get("pending_question_target") is None
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        for entry in (repaired_expect.get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_rewrites_reschedule_date_followup():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Мне нужно перенести запись на маникюр.",
                    "tags": ["reschedule"],
                    "expect": {"state": "pending", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Нужно на следующую неделю.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "service_choice"},
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["tags"] == ["reschedule"]
    assert repaired_turn["expect"]["action"] == "handoff"
    assert repaired_turn["expect"]["state"] == "pending"
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_act") is None
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_target") is None


def test_repair_post_coverage_orphan_pending_question_turns_preserves_time_after_price_interrupt():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться на маникюр.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Сколько стоит маникюр?",
                    "tags": ["price"],
                    "expect": {"reply_type": "service_choice"},
                },
                {
                    "kind": "text",
                    "text": "Можно к Айгерим?",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    interrupt_turn = repaired[0]["turns"][1]
    assert interrupt_turn["expect"]["reply_type"] == "time"
    assert interrupt_turn["expect"]["meta_any"]["expected_reply_type"] == ["time"]

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["expect"]["reply_type"] == "time"
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["time"]


def test_repair_post_coverage_orphan_pending_question_turns_advances_service_choice_price_interrupt():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "service_choice", "state": "bot_active", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Сколько стоит маникюр?",
                    "tags": ["price"],
                    "expect": {"reply_type": "service_choice"},
                },
                {
                    "kind": "text",
                    "text": "Когда есть свободные слоты?",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    interrupt_turn = repaired[0]["turns"][1]
    assert interrupt_turn["expect"]["reply_type"] == "time"
    assert interrupt_turn["expect"]["meta_any"]["expected_reply_type"] == ["time"]
    assert interrupt_turn["expect"]["meta_any"]["expected_reply_contract_reason"] == [
        "catalog_service_booking_progress"
    ]

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["expect"]["reply_type"] == "time"
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["time"]


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_slot_compare_explicit_time_fill():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Хочу записаться на маникюр.",
                    "tags": ["booking"],
                    "expect": {"reply_type": "time", "expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": "Сколько стоит маникюр?",
                    "tags": ["price"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {"expected_reply_type": ["time"]},
                        "trace_contains": [
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            }
                        ],
                    },
                },
                {
                    "kind": "text",
                    "text": "Можно записаться на 15:00?",
                    "tags": ["slot_compare"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "pending_question_act": ["slot_compare"],
                            "pending_question_target": ["time"],
                            "expected_reply_type": ["time"],
                        },
                        "trace_contains": [
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "slot_compare",
                                "pending_question_target": "time",
                            },
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][2]
    assert repaired_turn["tags"] == ["time"]
    assert repaired_turn["expect"]["reply_type"] == "name"
    assert repaired_turn["expect"]["expected_reply"] is True
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_act") is None
    assert (repaired_turn["expect"].get("meta_any") or {}).get("pending_question_target") is None
    assert (repaired_turn["expect"].get("meta_any") or {}).get("expected_reply_type") == ["name"]
    assert not any(
        entry.get("stage") == "pending_question_interaction"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_normalizes_standalone_named_specialist_booking():
    ctx = _module._build_context(random.Random(91))
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Каковы ваши часы работы?",
                    "tags": ["hours"],
                    "expect": {"expected_reply": True},
                },
                {
                    "kind": "text",
                    "text": f"Можно к мастеру {ctx['master']}?",
                    "tags": ["master"],
                    "expect": {},
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][1]
    assert repaired_turn["tags"] == ["booking"]
    assert repaired_turn["expect"]["reply_type"] == "service_choice"
    assert repaired_turn["expect"]["info_sections"] == []
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["service_choice"]


def test_repair_post_coverage_orphan_pending_question_turns_keeps_active_name_specialist_followup_after_cancel():
    ctx = _module._build_context(random.Random(231))
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": f"Я хочу записаться на {ctx['service']}.",
                    "tags": ["booking"],
                    "expect": {},
                },
                {
                    "kind": "text",
                    "text": "Мне подходит 15:00.",
                    "tags": ["time"],
                    "expect": {"reply_type": "name"},
                },
                {
                    "kind": "text",
                    "text": "А если не получится, то как отменить запись?",
                    "tags": ["cancel"],
                    "expect": {},
                },
                {
                    "kind": "text",
                    "text": f"Я хотел бы записаться к {ctx['master']}.",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][3]
    assert repaired_turn["expect"]["reply_type"] == "name"
    assert repaired_turn["expect"]["meta_any"]["pending_question_target"] == ["specialist"]
    assert repaired_turn["expect"]["meta_any"]["active_question_relation"] == [
        "referent_followup"
    ]
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["name"]


def test_repair_post_coverage_orphan_pending_question_turns_keeps_active_name_choose_named_specialist_followup():
    ctx = _module._build_context(random.Random(233))
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": f"Я хочу записаться на {ctx['service']}.",
                    "tags": ["booking"],
                    "expect": {},
                },
                {
                    "kind": "text",
                    "text": "Можно записаться на завтра в 15:00?",
                    "tags": ["time"],
                    "expect": {"reply_type": "name"},
                },
                {
                    "kind": "text",
                    "text": f"А кто будет делать {ctx['service']}?",
                    "tags": ["consult"],
                    "expect": {
                        "reply_type": "name",
                        "meta_any": {"expected_reply_type": ["name"]},
                    },
                },
                {
                    "kind": "text",
                    "text": f"Могу выбрать {ctx['master']}?",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "service_choice",
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][3]
    assert repaired_turn["expect"]["reply_type"] == "name"
    assert repaired_turn["expect"]["meta_any"]["pending_question_target"] == ["specialist"]
    assert repaired_turn["expect"]["meta_any"]["active_question_relation"] == [
        "referent_followup"
    ]
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("expected_reply_type") == "name"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_keeps_active_name_specialist_time_followup():
    ctx = _module._build_context(random.Random(234))
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": f"Я хочу записаться на {ctx['service']}.",
                    "tags": ["booking"],
                    "expect": {},
                },
                {
                    "kind": "text",
                    "text": "Можно записаться на завтра в 15:00?",
                    "tags": ["time"],
                    "expect": {"reply_type": "name"},
                },
                {
                    "kind": "text",
                    "text": f"Как насчет специалиста {ctx['master']}?",
                    "tags": ["booking", "master"],
                    "expect": {
                        "reply_type": "name",
                        "meta_any": {"expected_reply_type": ["name"]},
                    },
                },
                {
                    "kind": "text",
                    "text": "Могу я записаться к ней на 14:00?",
                    "tags": ["ask_about_requested_slot"],
                    "expect": {
                        "reply_type": "service_choice",
                        "meta_any": {"expected_reply_type": ["service_choice"]},
                        "trace_contains": [
                            {
                                "stage": "question_contract",
                                "expected_reply_type": "service_choice",
                            }
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    repaired_turn = repaired[0]["turns"][3]
    assert repaired_turn["tags"] == ["booking"]
    assert repaired_turn["expect"]["reply_type"] == "name"
    assert repaired_turn["expect"]["meta_any"]["pending_question_act"] == [
        "ask_about_requested_slot"
    ]
    assert repaired_turn["expect"]["meta_any"]["pending_question_target"] == ["time"]
    assert repaired_turn["expect"]["meta_any"]["pending_question_interaction"] == [
        "ask_about_requested_slot"
    ]
    assert repaired_turn["expect"]["meta_any"]["pending_question_owner"] == [
        "booking_time_availability_followup"
    ]
    assert repaired_turn["expect"]["meta_any"]["active_question_relation"] == [
        "ask_about_requested_slot"
    ]
    assert repaired_turn["expect"]["meta_any"]["expected_reply_type"] == ["name"]
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_time_availability_followup"
        and entry.get("pending_question_act") == "ask_about_requested_slot"
        and entry.get("pending_question_target") == "time"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("expected_reply_type") == "name"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "name"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "service_choice"
        for entry in (repaired_turn["expect"].get("trace_contains") or [])
    )


def test_repair_post_coverage_orphan_pending_question_turns_clears_multi_service_hours_followup():
    dialogs = [
        {
            "dialog_id": 1,
            "turns": [
                {
                    "kind": "text",
                    "text": "Мне нужен маникюр и педикюр.",
                    "tags": ["booking"],
                    "expect": {
                        "reply_type": "time",
                        "meta_any": {"expected_reply_type": ["time"]},
                    },
                },
                {
                    "kind": "text",
                    "text": "Какой у вас график работы?",
                    "tags": ["hours"],
                    "expect": {
                        "reply_type": "time",
                        "expected_reply": True,
                        "meta_any": {
                            "expected_reply_type": ["time"],
                            "pending_question_act": ["ask_about_requested_slot"],
                            "pending_question_target": ["time"],
                        },
                        "trace_contains": [
                            {"stage": "question_contract", "expected_reply_type": "time"},
                            {
                                "stage": "pending_question_interaction",
                                "pending_question_act": "ask_about_requested_slot",
                                "pending_question_target": "time",
                            },
                        ],
                    },
                },
            ],
        }
    ]

    repaired = _module._repair_post_coverage_orphan_pending_question_turns(dialogs)

    first_turn_expect = repaired[0]["turns"][0]["expect"]
    assert first_turn_expect["reply_type"] == "service_choice"
    assert first_turn_expect["meta_any"]["expected_reply_type"] == ["service_choice"]
    assert first_turn_expect["meta_any"]["expected_reply_contract_reason"] == [
        "multi_service_booking_clarify"
    ]

    repaired_turn = repaired[0]["turns"][1]
    repaired_expect = repaired_turn["expect"]
    assert repaired_turn["tags"] == ["hours"]
    assert repaired_expect.get("reply_type") is None
    assert repaired_expect.get("expected_reply") is True
    assert (repaired_expect.get("meta_any") or {}).get("expected_reply_type") is None
    assert (repaired_expect.get("meta_any") or {}).get("pending_question_act") is None
    assert (repaired_expect.get("meta_any") or {}).get("pending_question_target") is None
    assert not any(
        entry.get("stage") in {"question_contract", "pending_question_interaction"}
        for entry in (repaired_expect.get("trace_contains") or [])
    )


def test_required_llm_tags_include_handoff_for_handoff_coverage():
    required = _module._required_llm_tags(["booking", "info", "interrupt", "handoff"])

    assert "handoff" in required
    assert "check_booking" not in required
    assert "confirm" not in required


def test_apply_language_profile_kk_preserves_expect_and_tags():
    ctx = _module._build_context(random.Random(5))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Меня зовут {name}.", "tags": ["name"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    mutated = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="kk",
        rng=random.Random(5),
    )

    assert mutated[0]["tags"] == turns[0]["tags"]
    assert mutated[1]["expect"] == turns[1]["expect"]
    assert "керек" in mutated[0]["text"].lower()
    assert "атым" in mutated[1]["text"].lower()
    assert "растаймын" in mutated[2]["text"].lower()


def test_apply_language_profile_mixed_is_seed_stable_and_keeps_ru_kk_surface():
    ctx = _module._build_context(random.Random(7))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Меня зовут {name}.", "tags": ["name"]}, ctx),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    first = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="mixed",
        rng=random.Random(11),
    )
    second = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="mixed",
        rng=random.Random(11),
    )

    assert [turn["text"] for turn in first] == [turn["text"] for turn in second]
    joined = " ".join(turn["text"].lower() for turn in first)
    assert any(token in joined for token in ("керек", "атым", "растаймын", "сөйлесуге"))
    assert any(token in joined for token in ("хочу", "телефон", "подтверждаю", "номер"))


def test_generate_template_dialog_reports_language_profile_metadata():
    dialog = _module._generate_template_dialog(
        random.Random(13),
        template=_module.SCENARIOS[0],
        min_turns=10,
        max_turns=10,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        language_profile="kk",
        semantic_variation_profile="canonical",
        slot_format_profile="canonical",
        surface_noise_profile="clean",
    )

    assert dialog["language_profile"] == "kk"
    assert dialog["metamorphic_family"] == "kk_surface"
    assert dialog["turns"]


def test_apply_slot_format_variation_preserves_expect_and_tags():
    ctx = _module._build_context(random.Random(51))
    turns = [
        _module._format_turn(
            {
                "text": "{greet}, хочу записаться на {service} {day} {time_range}.",
                "tags": ["booking"],
            },
            ctx,
        ),
        _module._format_turn({"text": "Можно {time_exact}?", "tags": ["time"]}, ctx),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
    ]

    mutated = _module._apply_slot_format_variation(
        turns,
        ctx,
        slot_format_profile="variant",
        language_profile="ru",
    )

    joined = " ".join(turn["text"].lower() for turn in mutated)
    assert any(token in joined for token in ("на пятницу", "на субботу", "на воскресенье", "на завтра", "в выходные"))
    assert any(
        token in joined
        for token in (
            "после шести",
            "после семи",
            "ближе к вечеру",
            "примерно 5 30 вечера",
            "вечера",
        )
    )
    assert "+7" not in joined
    assert "(" not in joined
    assert any(token in joined for token in ("870", "701", "702", "707", "778"))
    assert mutated[0]["tags"] == turns[0]["tags"]
    assert mutated[1]["expect"] == turns[1]["expect"]


def test_apply_slot_format_variation_updates_transliterated_surface():
    ctx = _module._build_context(random.Random(53))
    turns = [
        _module._format_turn(
            {
                "text": "{greet}, хочу записаться на {service} {day} {time_range}.",
                "tags": ["booking"],
            },
            ctx,
        ),
        _module._format_turn({"text": "Можно {time_exact}?", "tags": ["time"]}, ctx),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
    ]
    translit_turns = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="mixed_translit",
        rng=random.Random(59),
    )

    mutated = _module._apply_slot_format_variation(
        translit_turns,
        ctx,
        slot_format_profile="variant",
        language_profile="mixed_translit",
    )

    joined = " ".join(turn["text"].lower() for turn in mutated)
    assert any(token in joined for token in ("na pyatnitsu", "na subbotu", "na zavtra", "v vyhodnye"))
    assert any(token in joined for token in ("posle shesti", "posle semi", "blizhe k vecheru", "5 30 vechera", "vechera"))
    assert "+7" not in joined
    assert "(" not in joined
    assert any(token in joined for token in ("870", "701", "702", "707", "778"))
    assert mutated[0]["tags"] == translit_turns[0]["tags"]


def test_apply_semantic_variation_synonym_preserves_expect_and_tags():
    ctx = _module._build_context(random.Random(31))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    mutated = _module._apply_semantic_variation(
        turns,
        ctx,
        semantic_variation_profile="synonym",
        language_profile="ru",
        rng=random.Random(37),
    )

    joined = " ".join(turn["text"].lower() for turn in mutated)
    assert any(token in joined for token in ("хочу к вам", "мой контакт", "все устраивает"))
    assert mutated[0]["tags"] == turns[0]["tags"]
    assert mutated[1]["expect"] == turns[1]["expect"]


def test_apply_semantic_variation_synonym_mixed_translit_is_seed_stable():
    ctx = _module._build_context(random.Random(41))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    first = _module._apply_semantic_variation(
        turns,
        ctx,
        semantic_variation_profile="synonym",
        language_profile="mixed_translit",
        rng=random.Random(43),
    )
    second = _module._apply_semantic_variation(
        turns,
        ctx,
        semantic_variation_profile="synonym",
        language_profile="mixed_translit",
        rng=random.Random(43),
    )

    assert [turn["text"] for turn in first] == [turn["text"] for turn in second]
    joined = " ".join(turn["text"] for turn in first)
    assert any(token in joined for token in ("hochu", "kontakt", "tandaidy", "managerge"))
    assert first[0]["tags"] == turns[0]["tags"]


def test_apply_language_profile_mixed_translit_emits_latin_script_seed_stably():
    ctx = _module._build_context(random.Random(17))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Меня зовут {name}.", "tags": ["name"]}, ctx),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    first = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="mixed_translit",
        rng=random.Random(19),
    )
    second = _module._apply_language_profile(
        turns,
        ctx,
        language_profile="mixed_translit",
        rng=random.Random(19),
    )

    assert [turn["text"] for turn in first] == [turn["text"] for turn in second]
    joined = " ".join(turn["text"] for turn in first)
    assert any(token in joined for token in ("kerek", "nomer", "ratyn", "podtverzhdayu", "Menin"))
    assert any(char.isalpha() and "A" <= char <= "z" for char in joined)
    assert first[0]["tags"] == turns[0]["tags"]
    assert first[1]["expect"] == turns[1]["expect"]


def test_apply_surface_noise_typo_preserves_expect_and_tags():
    ctx = _module._build_context(random.Random(21))
    turns = [
        _module._format_turn(
            {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
            ctx,
        ),
        _module._format_turn({"text": "Телефон {phone}.", "tags": ["phone"]}, ctx),
        _module._format_turn({"text": "Да, подтверждаю.", "tags": ["confirm"]}, ctx),
    ]

    mutated = _module._apply_surface_noise(
        turns,
        ctx,
        surface_noise_profile="typo",
        rng=random.Random(23),
    )

    joined = " ".join(turn["text"].lower() for turn in mutated)
    assert any(token in joined for token in ("хачу", "телифон", "потверждаю"))
    assert mutated[0]["tags"] == turns[0]["tags"]
    assert mutated[1]["expect"] == turns[1]["expect"]


def test_generate_template_dialog_reports_surface_noise_metadata():
    dialog = _module._generate_template_dialog(
        random.Random(29),
        template=_module.SCENARIOS[1],
        min_turns=10,
        max_turns=10,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        language_profile="ru",
        semantic_variation_profile="canonical",
        slot_format_profile="canonical",
        surface_noise_profile="typo",
    )

    assert dialog["surface_noise_profile"] == "typo"
    assert dialog["surface_mutation_family"] == "typo_surface"
    assert dialog["turns"]


def test_generate_template_dialog_reports_slot_format_metadata():
    dialog = _module._generate_template_dialog(
        random.Random(61),
        template=_module.SCENARIOS[0],
        min_turns=10,
        max_turns=10,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        language_profile="ru",
        semantic_variation_profile="canonical",
        slot_format_profile="variant",
        surface_noise_profile="clean",
    )

    assert dialog["slot_format_profile"] == "variant"
    assert dialog["slot_format_family"] == "slot_format_variant"
    assert dialog["turns"]


def test_generate_template_dialog_reports_semantic_variation_metadata():
    dialog = _module._generate_template_dialog(
        random.Random(47),
        template=_module.SCENARIOS[2],
        min_turns=10,
        max_turns=10,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        language_profile="ru",
        semantic_variation_profile="synonym",
        slot_format_profile="canonical",
        surface_noise_profile="clean",
    )

    assert dialog["semantic_variation_profile"] == "synonym"
    assert dialog["semantic_mutation_family"] == "synonym_surface"
    assert dialog["turns"]


def test_select_templates_prefers_unique_templates_before_repeats():
    selected, missing = _module._select_templates(
        random.Random(73),
        count=len(_module.SCENARIOS),
        coverage=[],
    )

    assert missing == []
    assert len({dialog["id"] for dialog in selected}) == len(_module.SCENARIOS)


def test_select_templates_acceptance_batch_includes_weekend_service_followup_template():
    selected, missing = _module._select_templates(
        random.Random(79),
        count=len(_module.SCENARIOS),
        coverage=["booking", "info", "interrupt", "handoff"],
    )

    assert missing == []
    assert "booking_weekend_service_followup" in {dialog["id"] for dialog in selected}


def test_generate_template_dialog_weekend_service_followup_keeps_strong_service_choice_contract():
    template = next(
        item for item in _module.SCENARIOS if item["id"] == "booking_weekend_service_followup"
    )
    dialog = _module._generate_template_dialog(
        random.Random(83),
        template=template,
        min_turns=12,
        max_turns=12,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        language_profile="ru",
        semantic_variation_profile="canonical",
        slot_format_profile="canonical",
        surface_noise_profile="clean",
    )

    target_turn = next(
        turn for turn in dialog["turns"] if turn.get("text") == "Можно записаться на выходные?"
    )
    expect = target_turn.get("expect") or {}

    assert expect.get("reply_type") == "service_choice"
    assert expect.get("action") == "collect"
    assert (expect.get("meta") or {}) == {
        "action": "collect",
        "source": "llm_policy_core",
        "tool_action": "collect",
        "expected_reply_type": "service_choice",
        "expected_reply_reason": "collect:service",
    }
    assert (expect.get("trace_contains") or []) == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]


def test_media_turn_text_mode_uses_offer_phrase_without_fake_attachment_claim():
    turn = _module._media_turn({}, mode="text", kind="photo")

    assert turn["kind"] == "text"
    assert turn["text"] == "Могу прислать фото."
    assert turn["tags"] == ["media", "photo"]
    assert (turn.get("expect") or {}).get("state") == "bot_active"
    assert (turn.get("expect") or {}).get("expected_reply") is None


def test_ensure_required_tags_adds_handoff_for_handoff_coverage():
    ctx = _module._build_context(random.Random(23))
    turns = [
        {"kind": "text", "text": "Хочу записаться", "tags": ["booking"], "expect": {}},
        {"kind": "text", "text": "Можно на 19:00?", "tags": ["time"], "expect": {}},
        {"kind": "text", "text": "Меня зовут Лена", "tags": ["name"], "expect": {}},
        {"kind": "text", "text": "Да, подтверждаю.", "tags": ["confirm"], "expect": {}},
    ]

    enriched = _module._ensure_required_tags(
        turns,
        ctx,
        max_turns=12,
        coverage=["booking", "info", "interrupt", "handoff"],
    )
    tags = {tag for turn in enriched for tag in (turn.get("tags") or [])}

    assert "handoff" in tags


def test_call_openai_classifies_quota_error(monkeypatch):
    error_payload = json.dumps(
        {
            "error": {
                "code": "insufficient_quota",
                "message": "quota exceeded for this project",
            }
        }
    ).encode("utf-8")
    http_error = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(error_payload),
    )

    def _raise_http_error(*_args, **_kwargs):
        raise http_error

    monkeypatch.setattr(_module.urllib.request, "urlopen", _raise_http_error)

    with pytest.raises(RuntimeError) as exc_info:
        _module._call_openai(
            "test prompt",
            api_key="test-key",
            model="gpt-5.4-nano-2026-03-17",
            base_url="https://api.openai.com",
            max_tokens=256,
        )

    message = str(exc_info.value)
    assert "openai_rate_or_quota_limited" in message
    assert "insufficient_quota" in message


def test_call_openai_uses_gpt5_compatible_token_field(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "{\"dialogs\": []}"
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def _fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(_module.urllib.request, "urlopen", _fake_urlopen)

    content = _module._call_openai(
        "test prompt",
        api_key="test-key",
        model="gpt-5.4-nano-2026-03-17",
        base_url="https://api.openai.com",
        max_tokens=256,
    )

    assert content == "{\"dialogs\": []}"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["timeout"] == 40.0
    assert captured["body"]["max_completion_tokens"] == 256
    assert "max_tokens" not in captured["body"]


def test_resolve_scenario_context_loads_pack_truth_for_non_salon_pack():
    context = _module._resolve_scenario_context(
        client_slug="dental_pack",
        branch_slug="downtown",
        scenario_context_file=None,
    )

    assert context["client_slug"] == "dental_pack"
    assert context["branch_slug"] == "downtown"
    assert "Профессиональная чистка зубов" in (context.get("services") or [])
    assert context.get("business", {}).get("summary") == "Стоматология: лечение, гигиена, профилактика."


def test_build_context_prefers_explicit_scenario_context_services_and_specialists():
    context = {
        "services": ["Консультация терапевта"],
        "specialists": ["Данияр"],
    }

    ctx = _module._build_context(random.Random(73), scenario_context=context)

    assert ctx["service"] == "Консультация терапевта"
    assert ctx["master"] == "Данияр"
    assert "Консультация терапевта" in ctx["interrupt_price"]


def test_build_llm_generation_prompt_uses_context_contract_and_avoids_salon_default():
    scenario_context = {
        "client_slug": "clinic_pack",
        "branch_slug": "branch-a",
        "business": {
            "display_name": "MedCare",
            "summary": "Диагностика и базовые обследования.",
            "languages": ["ru", "kk"],
        },
        "services": ["УЗИ брюшной полости", "ЭКГ"],
        "specialists": ["Др. Айгерим"],
        "capabilities": {
            "domain_slug": "clinic",
            "tools": {"allow": ["calendar.*"], "deny": ["consult.*"]},
            "allowed_fact_scopes": ["info.*"],
            "handoff_policy": "manager_request_only",
        },
    }

    prompt = _module._build_llm_generation_prompt(
        batch_count=2,
        min_turns=10,
        max_turns=15,
        coverage=["booking", "info"],
        media_mode="text",
        media_kind="photo",
        seed=42,
        scenario_context=scenario_context,
    )

    assert "Beauty salon domain, Russian language" not in prompt
    assert "client_slug=clinic_pack" in prompt
    assert "known_services=УЗИ брюшной полости, ЭКГ" in prompt
    assert "domain_slug=clinic" in prompt
    assert "tool_allow=calendar.*" in prompt
