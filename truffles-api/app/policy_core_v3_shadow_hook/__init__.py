"""Bridge between legacy `consultant_runtime` and Policy-Core v3 shadow-run.

Status: PoC bridge. Imports both legacy types and the shadow module.
Spec: SPECS/SHADOW_RUN_V3.md (Phase B.2.b).

This package is the ONLY place allowed to import both `app.policy_core_v3_shadow`
(independence guard preserved) and legacy `app.services` / `app.core` types.

The dispatcher is fire-and-forget. It never raises into the caller; any
internal failure is logged once and silently dropped.
"""

from .dispatcher import dispatch_fire_and_forget
from .wiring import reset_singletons

__all__ = ["dispatch_fire_and_forget", "reset_singletons"]
