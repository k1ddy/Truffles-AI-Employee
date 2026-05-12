"""Fire-and-forget dispatcher for the Policy-Core v3 shadow-run.

Spec: SPECS/SHADOW_RUN_V3.md (Phase B.2.b — minimum hot-path touch).

The dispatcher is the only function the hot path ever calls. It is
non-blocking, never raises, and is silent when the wiring is incomplete.

Hard rules (must hold under every code path):
- Never propagate any exception to the caller (rule §1: shadow never affects
  the customer reply).
- Never block the event loop. The actual shadow-run is scheduled via
  `asyncio.create_task`. If no event loop is running, the dispatcher is a
  no-op.
- Never assume wiring; missing pack/sink/invoker → silent return.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.policy_core_v3_shadow import (
    LegacyTurnContext,
    project_legacy_decision,
    run_shadow,
)

from . import wiring


logger = logging.getLogger(__name__)


def dispatch_fire_and_forget(
    *,
    tenant_id: str,
    conversation_id: str,
    current_message: str,
    legacy_decision: Any,
    turn_index: int = 0,
) -> None:
    """Schedule a shadow-run for the current turn.

    Returns immediately. If anything fails, the failure is logged at debug
    level and dropped — the customer reply path is never disturbed.
    """
    try:
        pack = wiring.get_shadow_pack()
        if pack is None:
            return
        sink = wiring.get_shadow_sink()
        if sink is None:
            return
        invoker = wiring.get_shadow_invoker()
        if invoker is None:
            return

        legacy_summary = project_legacy_decision(legacy_decision)

        ctx = LegacyTurnContext(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            current_message=current_message or "",
            pack=pack,
            now=datetime.now(timezone.utc),
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not running inside an event loop; we cannot fire-and-forget
            # safely. Drop. Phase B.3 may add a sync drainer for tests.
            return

        loop.create_task(
            run_shadow(
                ctx=ctx,
                legacy_summary=legacy_summary,
                invoker=invoker,
                sink=sink,
                turn_index=turn_index,
                notes="consultant_runtime_shadow_hook",
            )
        )
    except Exception:  # pragma: no cover - defensive blanket
        # Hot path must never see an exception from here.
        logger.debug("policy_core_v3 shadow dispatcher swallowed exception", exc_info=True)
