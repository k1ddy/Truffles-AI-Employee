import io
import json
import random
import urllib.error
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


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


_module = _load_module()
_merge_expectations = _module._merge_expectations


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


def test_sanitize_llm_turns_rewrites_master_tag_without_master_cues():
    ctx = _module._build_context(random.Random(17))
    turns = [{"kind": "text", "text": "Что вы можете предложить?", "tags": ["master"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(17))

    assert len(sanitized) == 1
    text = str(sanitized[0].get("text") or "").lower()
    assert "мастер" in text or "специалист" in text
    info_sections = (sanitized[0].get("expect") or {}).get("info_sections") or []
    assert "master" in info_sections
    assert "specialist" in info_sections


def test_sanitize_llm_turns_keeps_master_tag_with_master_cues():
    ctx = _module._build_context(random.Random(19))
    source = f"Можно к мастеру {ctx['master']}?"
    turns = [{"kind": "text", "text": source, "tags": ["master"], "expect": {}}]

    sanitized = _module._sanitize_llm_turns(turns, ctx, random.Random(19))

    assert len(sanitized) == 1
    assert sanitized[0]["text"] == source


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
        model="gpt-4o-mini",
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


def test_ensure_required_tags_adds_check_booking_and_confirm_for_booking_coverage():
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

    assert "check_booking" in tags
    assert "confirm" in tags


def test_ensure_required_tags_reorders_check_before_confirm():
    ctx = _module._build_context(random.Random(11))
    turns = [
        {"kind": "text", "text": "Да, подтверждаю.", "tags": ["confirm"], "expect": {}},
        {"kind": "text", "text": "Проверьте мою запись.", "tags": ["check_booking"], "expect": {}},
    ]

    enriched = _module._ensure_required_tags(
        turns,
        ctx,
        max_turns=12,
        coverage=["booking", "interrupt"],
    )
    check_idx = next(
        idx for idx, turn in enumerate(enriched) if "check_booking" in (turn.get("tags") or [])
    )
    confirm_idx = next(
        idx for idx, turn in enumerate(enriched) if "confirm" in (turn.get("tags") or [])
    )

    assert check_idx < confirm_idx


def test_required_llm_tags_include_handoff_for_handoff_coverage():
    required = _module._required_llm_tags(["booking", "info", "interrupt", "handoff"])

    assert "handoff" in required


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
    assert any(token in joined for token in ("после 18:00", "после 19:00", "ближе к вечеру", "примерно к 17.30", "к "))
    assert any(token in joined for token in ("8 (",))
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
    assert any(token in joined for token in ("18:00", "19:00", "17.30", "8 ("))
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
            model="gpt-5-mini",
            base_url="https://api.openai.com",
            max_tokens=256,
        )

    message = str(exc_info.value)
    assert "openai_rate_or_quota_limited" in message
    assert "insufficient_quota" in message


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
