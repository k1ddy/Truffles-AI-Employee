from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

_DEFAULT_RECENT_INBOUND_DAYS = 30


@dataclass(frozen=True)
class ReferenceBranchSignal:
    branch_id: UUID
    client_id: UUID
    is_active: bool
    slug: Optional[str]
    created_at: Optional[datetime]
    has_instance_id: bool
    has_phone: bool
    has_recent_inbound: bool
    go_live_allowed: bool
    onboarding_go_no_go: bool
    integration_ok: bool


@dataclass(frozen=True)
class ReferenceBranchDecision:
    branch_ids: tuple[UUID, ...]
    reason: str


def _coerce_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def has_recent_inbound(
    last_inbound_at: Optional[datetime],
    *,
    now: Optional[datetime] = None,
    window_days: int = _DEFAULT_RECENT_INBOUND_DAYS,
) -> bool:
    observed_at = _coerce_utc(last_inbound_at)
    if observed_at is None:
        return False
    current = _coerce_utc(now) or datetime.now(timezone.utc)
    safe_window_days = max(1, int(window_days or _DEFAULT_RECENT_INBOUND_DAYS))
    return observed_at >= current - timedelta(days=safe_window_days)


def _branch_rank_score(signal: ReferenceBranchSignal) -> int:
    score = 0
    if signal.go_live_allowed:
        score += 100
    if signal.has_recent_inbound:
        score += 70
    if signal.has_instance_id and signal.has_phone:
        score += 60
    elif signal.has_instance_id:
        score += 25
    elif signal.has_phone:
        score += 15
    if signal.onboarding_go_no_go:
        score += 20
    if signal.integration_ok:
        score += 5
    return score


def _branch_sort_key(signal: ReferenceBranchSignal) -> tuple[int, datetime, str, str]:
    # Sort by descending rank score; then by oldest created_at for deterministic stability.
    created_at = _coerce_utc(signal.created_at) or datetime.max.replace(tzinfo=timezone.utc)
    slug = (signal.slug or "").strip().lower()
    return (-_branch_rank_score(signal), created_at, slug, str(signal.branch_id))


def _is_production_like(signal: ReferenceBranchSignal) -> bool:
    if not signal.is_active:
        return False
    if signal.go_live_allowed:
        return True
    if signal.has_recent_inbound:
        return True
    return signal.has_instance_id and signal.has_phone


def select_reference_branch_ids(
    signals: list[ReferenceBranchSignal],
) -> dict[UUID, ReferenceBranchDecision]:
    grouped: dict[UUID, list[ReferenceBranchSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.client_id, []).append(signal)

    decisions: dict[UUID, ReferenceBranchDecision] = {}
    for client_id, client_signals in grouped.items():
        active_signals = [item for item in client_signals if item.is_active]
        if not active_signals:
            decisions[client_id] = ReferenceBranchDecision(
                branch_ids=tuple(),
                reason="no_active_branches",
            )
            continue

        production_like = [item for item in active_signals if _is_production_like(item)]
        if production_like:
            ordered = sorted(production_like, key=_branch_sort_key)
            decisions[client_id] = ReferenceBranchDecision(
                branch_ids=tuple(item.branch_id for item in ordered),
                reason="active_live_signals",
            )
            continue

        fallback = sorted(active_signals, key=_branch_sort_key)[0]
        decisions[client_id] = ReferenceBranchDecision(
            branch_ids=(fallback.branch_id,),
            reason="active_fallback_best_candidate",
        )

    return decisions
