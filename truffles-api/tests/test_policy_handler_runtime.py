from __future__ import annotations

from types import SimpleNamespace

from app.routers.webhook import _legacy as legacy
from app.routers.webhook import policy


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
