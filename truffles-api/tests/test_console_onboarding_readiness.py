from types import SimpleNamespace
from uuid import uuid4

from app.services.console_onboarding_readiness import (
    is_readiness_hard_gate_enforced_for_branch,
    resolve_readiness_hard_gate_blockers,
    serialize_onboarding_readiness_kernel,
)


def _build_readiness_kernel() -> SimpleNamespace:
    return SimpleNamespace(
        status="warn",
        blocker_codes=["provider_binding_rebind_required"],
        next_action_codes=["sync_provider"],
        shadow_hard_gate_blockers=[
            "go_no_go:payment_confirmed",
            "provider_binding_rebind_required",
            "go_no_go:payment_confirmed",
            "noise",
        ],
        auto_questions=[
            SimpleNamespace(
                code="payment_confirmed",
                question="Оплата подтверждена?",
                blocking_go_live=True,
            )
        ],
        dimensions=[
            SimpleNamespace(
                id="delivery_health",
                status="warn",
                blocker_codes=["provider_binding_rebind_required"],
                next_action_codes=["sync_provider"],
            )
        ],
    )


def test_resolve_readiness_hard_gate_blockers_filters_and_dedupes() -> None:
    readiness_kernel = _build_readiness_kernel()

    blockers = resolve_readiness_hard_gate_blockers(
        readiness_kernel,
        hard_gate_codes={"provider_binding_rebind_required"},
    )

    assert blockers == [
        "go_no_go:payment_confirmed",
        "provider_binding_rebind_required",
    ]


def test_is_readiness_hard_gate_enforced_for_branch_supports_flag_and_canary() -> None:
    branch = SimpleNamespace(id=str(uuid4()).upper())

    assert is_readiness_hard_gate_enforced_for_branch(
        branch,
        hard_gate_enabled=True,
        canary_branch_ids=set(),
    )
    assert is_readiness_hard_gate_enforced_for_branch(
        branch,
        hard_gate_enabled=False,
        canary_branch_ids={str(branch.id).strip().lower()},
    )
    assert not is_readiness_hard_gate_enforced_for_branch(
        SimpleNamespace(id=None),
        hard_gate_enabled=False,
        canary_branch_ids=set(),
    )


def test_serialize_onboarding_readiness_kernel_returns_none_for_empty_input() -> None:
    assert (
        serialize_onboarding_readiness_kernel(
            None,
            hard_gate_enforced=True,
            hard_gate_codes={"provider_binding_rebind_required"},
        )
        is None
    )


def test_serialize_onboarding_readiness_kernel_builds_shadow_hard_gate() -> None:
    readiness_kernel = _build_readiness_kernel()

    payload = serialize_onboarding_readiness_kernel(
        readiness_kernel,
        hard_gate_enforced=True,
        hard_gate_codes={"provider_binding_rebind_required"},
    )

    assert payload is not None
    assert payload.status == "warn"
    assert payload.shadow_hard_gate.enforced is True
    assert payload.shadow_hard_gate.status == "fail"
    assert payload.shadow_hard_gate.blocker_codes == [
        "go_no_go:payment_confirmed",
        "provider_binding_rebind_required",
    ]
    assert payload.auto_questions[0].code == "payment_confirmed"
    assert payload.dimensions[0].id == "delivery_health"
