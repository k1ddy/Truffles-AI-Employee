from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Optional

from app.models import Branch
from app.schemas.console import (
    ConsoleOnboardingReadinessDimension,
    ConsoleOnboardingReadinessHardGate,
    ConsoleOnboardingReadinessKernel,
    ConsoleOnboardingReadinessQuestion,
)
from app.services.console_errors import ConsoleAPIError

BRANCH_GO_LIVE_STATES = {"pending", "approved", "rejected"}
BRANCH_GO_LIVE_DEFAULT_STATE = "pending"
GO_LIVE_WAIVER_MIN_HOURS = 1
GO_LIVE_WAIVER_MAX_HOURS = 24 * 30


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


def normalize_branch_go_live_state(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in BRANCH_GO_LIVE_STATES:
        return normalized
    return BRANCH_GO_LIVE_DEFAULT_STATE


def normalize_go_live_waiver_ttl_hours(value: int) -> int:
    if value < GO_LIVE_WAIVER_MIN_HOURS or value > GO_LIVE_WAIVER_MAX_HOURS:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"ttl_hours must be between {GO_LIVE_WAIVER_MIN_HOURS} and {GO_LIVE_WAIVER_MAX_HOURS}",
        )
    return value


def coerce_utc_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def is_branch_go_live_waiver_active(
    branch: Branch,
    *,
    now: Optional[datetime] = None,
) -> bool:
    waiver_until = coerce_utc_datetime(getattr(branch, "go_live_waiver_until", None))
    if waiver_until is None:
        return False
    current = now or datetime.now(timezone.utc)
    return waiver_until > current


def is_branch_go_live_allowed(
    branch: Branch,
    *,
    now: Optional[datetime] = None,
) -> bool:
    go_live_state = normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
    if go_live_state == "approved":
        return True
    return is_branch_go_live_waiver_active(branch, now=now)


def ensure_branch_go_live_gate(branch: Branch, *, operation: str) -> None:
    now = datetime.now(timezone.utc)
    go_live_state = normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
    waiver_active = is_branch_go_live_waiver_active(branch, now=now)
    if go_live_state == "approved" or waiver_active:
        return
    waiver_until = coerce_utc_datetime(getattr(branch, "go_live_waiver_until", None))
    raise ConsoleAPIError(
        409,
        "GO_LIVE_GATE_REQUIRED",
        "Go-live approval required before branch activation",
        {
            "operation": operation,
            "go_live_state": go_live_state,
            "go_live_reason": getattr(branch, "go_live_reason", None),
            "go_live_waiver_active": waiver_active,
            "go_live_waiver_until": waiver_until.isoformat() if waiver_until else None,
        },
    )


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
