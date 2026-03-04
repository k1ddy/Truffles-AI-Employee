from collections.abc import Iterable

from app.schemas.console import (
    ConsoleOnboardingReadinessDimension,
    ConsoleOnboardingReadinessHardGate,
    ConsoleOnboardingReadinessKernel,
    ConsoleOnboardingReadinessQuestion,
)


def _dedupe_non_empty(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def resolve_readiness_hard_gate_blockers(
    readiness_kernel,
    *,
    hard_gate_codes: set[str],
) -> list[str]:
    if readiness_kernel is None:
        return []
    candidates = list(getattr(readiness_kernel, "shadow_hard_gate_blockers", []) or [])
    selected = [
        code
        for code in candidates
        if isinstance(code, str) and (code.startswith("go_no_go:") or code in hard_gate_codes)
    ]
    return _dedupe_non_empty(selected)


def is_readiness_hard_gate_enforced_for_branch(
    branch,
    *,
    hard_gate_enabled: bool,
    canary_branch_ids: set[str],
) -> bool:
    if hard_gate_enabled:
        return True
    branch_id = getattr(branch, "id", None)
    if branch_id is None:
        return False
    normalized_branch_id = str(branch_id).strip().lower()
    return normalized_branch_id in canary_branch_ids


def serialize_onboarding_readiness_kernel(
    readiness_kernel,
    *,
    hard_gate_enforced: bool,
    hard_gate_codes: set[str],
) -> ConsoleOnboardingReadinessKernel | None:
    if readiness_kernel is None:
        return None

    hard_gate_blockers = resolve_readiness_hard_gate_blockers(
        readiness_kernel,
        hard_gate_codes=hard_gate_codes,
    )

    return ConsoleOnboardingReadinessKernel(
        status=readiness_kernel.status,
        blocker_codes=list(readiness_kernel.blocker_codes),
        next_action_codes=list(readiness_kernel.next_action_codes),
        auto_questions=[
            ConsoleOnboardingReadinessQuestion(
                code=item.code,
                question=item.question,
                blocking_go_live=item.blocking_go_live,
            )
            for item in getattr(readiness_kernel, "auto_questions", []) or []
        ],
        dimensions=[
            ConsoleOnboardingReadinessDimension(
                id=item.id,
                status=item.status,
                blocker_codes=list(item.blocker_codes),
                next_action_codes=list(item.next_action_codes),
            )
            for item in getattr(readiness_kernel, "dimensions", []) or []
        ],
        shadow_hard_gate=ConsoleOnboardingReadinessHardGate(
            enforced=hard_gate_enforced,
            status="fail" if hard_gate_blockers else "pass",
            blocker_codes=hard_gate_blockers,
        ),
    )
