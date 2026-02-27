from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.routers.webhook import _legacy as legacy
from app.routers.webhook import policy
from app.schemas.capabilities import CapabilitiesPayload, CapabilityPolicyOverrides


def _noop_truth_gate(*_args, **_kwargs):
    return None


def _exact_truth_gate(*_args, **_kwargs):
    return "exact"


def test_get_policy_handler_uses_default_for_unknown_policy_type(monkeypatch):
    default_truth_gate = _noop_truth_gate

    monkeypatch.setattr(
        legacy,
        "_POLICY_HANDLERS",
        {
            "default": {"truth_gate": default_truth_gate},
            "demo_salon": {"truth_gate": lambda *_args, **_kwargs: "demo"},
        },
        raising=False,
    )

    client = SimpleNamespace(config={"policy_type": "beauty_clinic"})
    handler = policy._get_policy_handler(client, client_slug="beauty_clinic")

    assert handler is not None
    assert handler.get("policy_type") == "beauty_clinic"
    assert handler.get("truth_gate") is default_truth_gate


def test_get_policy_handler_prefers_exact_mapping_over_default(monkeypatch):
    default_truth_gate = _noop_truth_gate
    exact_truth_gate = _exact_truth_gate

    monkeypatch.setattr(
        legacy,
        "_POLICY_HANDLERS",
        {
            "default": {"truth_gate": default_truth_gate},
            "beauty_clinic": {"truth_gate": exact_truth_gate},
        },
        raising=False,
    )

    client = SimpleNamespace(config={"policy_type": "beauty_clinic"})
    handler = policy._get_policy_handler(client, client_slug="beauty_clinic")

    assert handler is not None
    assert handler.get("truth_gate") is exact_truth_gate


def test_matches_policy_keywords_avoids_inner_substring_false_positive():
    normalized = legacy._normalize_text("А как насчет парковки?")

    assert not policy._matches_policy_keywords(normalized, ["счет", "счёт"])


def test_matches_policy_keywords_keeps_word_prefix_match_for_payment_terms():
    normalized = legacy._normalize_text("Можно выставить счет на оплату?")

    assert policy._matches_policy_keywords(normalized, ["счет"])


def test_detect_hard_law_match_does_not_use_hint_only_false_positive():
    policy_pack = {
        "hard_law": {"sections": ["payment_info"]},
        "payment_info": {"intent": "payment", "keywords": ["счет"]},
    }

    match = policy._detect_hard_law_match(
        "А как насчет парковки?",
        policy_pack=policy_pack,
        intent_hints=["payment"],
    )

    assert match is None


def test_detect_hard_law_match_uses_hint_when_keywords_confirmed():
    policy_pack = {
        "hard_law": {"sections": ["payment_info"]},
        "payment_info": {"intent": "payment", "keywords": ["счет"]},
    }

    match = policy._detect_hard_law_match(
        "Нужен счет на оплату.",
        policy_pack=policy_pack,
        intent_hints=["payment"],
    )

    assert match is not None
    assert match[0] == "payment_info"


def test_resolve_hard_law_sections_fallback_excludes_payment_info():
    policy_pack = {
        "hard_law": {},
        "payment_info": {"risk_level": "medium"},
        "medical": {"risk_level": "high"},
        "legal": {"risk_level": "high"},
    }

    sections = policy._resolve_hard_law_sections(policy_pack)

    assert "payment_info" not in sections
    assert "medical" in sections
    assert "legal" in sections


def test_get_policy_pack_applies_runtime_operational_overrides(monkeypatch):
    runtime = SimpleNamespace(
        payload=CapabilitiesPayload.model_validate(
            {"policy_overrides": {"payment_info": {"response": "Оплата по счету"}}}
        )
    )
    monkeypatch.setattr(policy, "get_runtime_capabilities", lambda: runtime)
    client = SimpleNamespace(
        config={
            "policy_pack": {
                "hard_law": {"sections": ["medical"]},
                "payment_info": {
                    "intent": "payment",
                    "keywords": ["счет"],
                    "response": "Старый ответ",
                },
            }
        }
    )

    resolved = policy._get_policy_pack(client, client_slug="demo_salon")

    assert resolved is not None
    assert resolved["payment_info"]["response"] == "Оплата по счету"


def test_get_policy_pack_ignores_runtime_override_for_hard_law_section(monkeypatch):
    runtime = SimpleNamespace(
        payload=CapabilitiesPayload.model_validate(
            {"policy_overrides": {"payment_info": {"response": "Новый ответ"}}}
        )
    )
    monkeypatch.setattr(policy, "get_runtime_capabilities", lambda: runtime)
    client = SimpleNamespace(
        config={
            "policy_pack": {
                "hard_law": {"sections": ["payment_info"]},
                "payment_info": {
                    "intent": "payment",
                    "keywords": ["счет"],
                    "response": "Старый ответ",
                },
            }
        }
    )

    resolved = policy._get_policy_pack(client, client_slug="demo_salon")

    assert resolved is not None
    assert resolved["payment_info"]["response"] == "Старый ответ"


def test_get_policy_pack_applies_registry_operational_overrides(monkeypatch):
    runtime = SimpleNamespace(
        client_id=uuid4(),
        branch_id=uuid4(),
        payload=CapabilitiesPayload(),
    )
    monkeypatch.setattr(policy, "get_runtime_capabilities", lambda: runtime)
    monkeypatch.setattr(
        policy,
        "resolve_effective_policy_overrides",
        lambda *_args, **_kwargs: CapabilityPolicyOverrides.model_validate(
            {"payment_info": {"response": "Оплата через кассу"}}
        ),
    )
    client = SimpleNamespace(
        config={
            "policy_pack": {
                "hard_law": {"sections": ["medical"]},
                "payment_info": {
                    "intent": "payment",
                    "keywords": ["счет"],
                    "response": "Базовый ответ",
                },
            }
        }
    )

    resolved = policy._get_policy_pack(
        client,
        client_slug="demo_salon",
        db=SimpleNamespace(),
    )

    assert resolved is not None
    assert resolved["payment_info"]["response"] == "Оплата через кассу"


def test_get_policy_pack_ignores_registry_override_for_hard_law_section(monkeypatch):
    runtime = SimpleNamespace(
        client_id=uuid4(),
        branch_id=uuid4(),
        payload=CapabilitiesPayload(),
    )
    monkeypatch.setattr(policy, "get_runtime_capabilities", lambda: runtime)
    monkeypatch.setattr(
        policy,
        "resolve_effective_policy_overrides",
        lambda *_args, **_kwargs: CapabilityPolicyOverrides.model_validate(
            {"payment_info": {"response": "Новый ответ"}}
        ),
    )
    client = SimpleNamespace(
        config={
            "policy_pack": {
                "hard_law": {"sections": ["payment_info"]},
                "payment_info": {
                    "intent": "payment",
                    "keywords": ["счет"],
                    "response": "Старый ответ",
                },
            }
        }
    )

    resolved = policy._get_policy_pack(
        client,
        client_slug="demo_salon",
        db=SimpleNamespace(),
    )

    assert resolved is not None
    assert resolved["payment_info"]["response"] == "Старый ответ"
