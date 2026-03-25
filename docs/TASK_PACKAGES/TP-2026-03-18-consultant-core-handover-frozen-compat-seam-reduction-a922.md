# TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-FROZEN-COMPAT-SEAM-REDUCTION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-STATE-SERVICE-HANDOVER-HELPER-COLLAPSE-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-HANDOVER-ESCALATION-SUPPORTING-HELPER-CLOSURE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Reduce the remaining external frozen compatibility seam for the handover family by making `_legacy` route handover lifecycle symbols directly to the owner surface instead of inheriting them from frozen `decision.py`. This block counts only if the old external runtime path `_legacy -> decision.py handover wrappers` becomes deleted or unreachable.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`

## FACT pre-check (before implementation)
- `Baseline commands`:
  - `sed -n '1,220p' truffles-api/app/routers/webhook/_legacy.py`
  - `sed -n '8398,8455p;23598,23630p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "legacy\._reuse_active_handover|legacy\.escalate_to_pending|legacy\.manager_resolve|decision\._reuse_active_handover|decision\.escalate_to_pending|decision\.manager_resolve" truffles-api/app truffles-api/tests`
- `FACT findings`:
  - `_legacy.py` currently copies all exports from frozen `decision.py`, so frozen and non-frozen callers that use `_legacy._reuse_active_handover`, `_legacy.escalate_to_pending`, and `_legacy.manager_resolve` still traverse the decision compatibility layer.
  - Frozen callers remain on `_legacy` in `truffles-api/app/routers/webhook/booking.py` and `truffles-api/app/routers/webhook/pending.py`.
  - Direct runtime app callers outside `decision.py` no longer import handover lifecycle entrypoints from `state_service.py`; the surviving external compatibility path is the `_legacy -> decision.py` seam.
  - `decision.py` still needs its local wrappers for internal frozen runtime callsites, so this block targets external reachability, not wholesale deletion of internal wrapper bodies.

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Remove Middle Man" "Move Function"`
- **Date/time (local):** `2026-03-18 09:09 +0500`
- **Why this query is precise:** the block is specifically about removing an unnecessary compatibility middle layer for callers while moving ownership to the module that already owns the behavior.
- **Sources opened (from this query):**
  - `Catalog of Refactorings` — `https://refactoring.com/catalog/`
  - `Remove Middle Man` — `https://refactoring.com/catalog/removeMiddleMan.html`
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** remove an unnecessary delegation layer once the real owner exists, and move callers to the module that owns the behavior instead of keeping them chained through a compatibility surface.
- **Decision:** `reuse/integrate` — keep frozen `decision.py` wrappers for its internal runtime only, but make `_legacy` publish the handover owner-surface symbols directly so external callers bypass the frozen wrapper seam.
- **Rejected options:**
  - editing frozen `booking.py` or `pending.py`
  - broad rewrite of internal `decision.py` handover callsites in this block
  - leaving `_legacy` as a full mirror of `decision.py` for the moved handover family

## Root cause (mandatory)
- **Symptom:** even after owner convergence and helper collapse, the external compatibility path for frozen callers still runs through `decision.py` handover wrappers because `_legacy.py` mirrors all decision exports.
- **Minimal reproduction:**
  1. inspect `_legacy.py` and confirm it bulk-copies `decision.__dict__`.
  2. inspect frozen callers in `booking.py` / `pending.py` and confirm they call `legacy._reuse_active_handover`, `legacy.escalate_to_pending`, and `legacy.manager_resolve`.
  3. inspect `decision.py` and confirm those symbols are compatibility wrappers to owner-surface functions.
- **Evidence:** external callers still depend on a frozen compatibility layer even though the live owner exists outside frozen files.
- **Five Whys:**
  1. Why does the old seam survive? Because `_legacy.py` still mirrors `decision.py` wholesale.
  2. Why is that a problem? Because frozen callers reach handover authority through frozen wrappers instead of the owner surface.
  3. Why wasn’t this fixed in the previous block? Because the previous block targeted `state_service.py` helper ownership, not the external compatibility path.
  4. Why is `_legacy.py` the right place to cut? Because frozen callers already depend on `_legacy`, and `_legacy.py` is non-frozen.
  5. Why is this admissible progress? Because it makes the old external runtime seam unreachable without touching frozen caller files.
- **Root cause statement:** `_legacy.py` remains a blanket re-export of frozen `decision.py`, so the moved handover family still leaks through the old frozen compatibility seam for external callers.
- **Fix mechanism:** override the moved handover symbols in `_legacy.py` with direct exports from `handover_owner_service.py`, add proof tests for the reroute, and leave internal `decision.py` wrappers untouched for frozen self-use only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse `handover_owner_service.py` as the single owner surface for `_reuse_active_handover`, `_create_pending_escalation_with_notification`, `escalate_to_pending`, `manager_take`, `manager_reassign`, `manager_resolve`, `manager_return`, `manager_reopen`, and `resolve_active_handover_rejection`
  - keep `_legacy.py` as the compatibility adapter, but override only the moved handover family instead of mirroring those names from `decision.py`
  - reuse existing targeted endpoint tests and add one explicit adapter-routing proof test
- **External reuse:** Martin Fowler `Remove Middle Man` / `Move Function`
- **Why not build from scratch:** the owner surface already exists and passes runtime checks; the remaining work is to delete one obsolete routing layer.

## Invariant
- no `truffles-api/app/routers/webhook/booking.py` edits
- no `truffles-api/app/routers/webhook/pending.py` edits
- no new semantic hardcode
- no new compatibility forest beside `_legacy.py`
- `decision.py` internal wrappers may remain only if external runtime callers stop depending on them

## Scope
- override handover lifecycle exports in `_legacy.py` to point directly to `handover_owner_service.py`
- add/update tests proving `_legacy` now bypasses `decision.py` for the handover family
- keep `decision.py` internal wrappers unchanged unless a minimal non-frozen-safe adjustment is strictly required

## Out of scope
- changing frozen `booking.py`, `decision.py`, or `pending.py` internal logic in bulk
- eliminating every internal wrapper inside `decision.py`
- supporting-helper closure inside `escalation_service.py`
- proof bundle / multi-pack validation

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`

## Plan (1..N)
1. Author this TP and register it in repo docs.
2. Override the moved handover family exports in `_legacy.py` to direct owner-surface symbols.
3. Add/update targeted tests proving `_legacy` routes to the owner surface and existing patched flows stay green.
4. Run targeted runtime checks and the required guards.
5. Record whether the old `_legacy -> decision.py` compat seam is deleted or unreachable.

## DoD
- `_legacy.py` no longer exposes the moved handover family through `decision.py`
- frozen callers that use `_legacy` reach the owner surface directly for the moved handover symbols
- targeted tests/guards remain green
- the old external compat seam `_legacy -> decision.py handover wrappers` is deleted or unreachable

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `python3 -m py_compile truffles-api/app/routers/webhook/_legacy.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_chaos_dialogs.py truffles-api/tests/test_demo_salon_eval.py truffles-api/tests/test_pending_pack_lexicons.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_handover_adapter or test_escalation_reuses_active_handover or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py -k 'reuse_active_handover'`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py -k 'reuse_active_handover or escalate_to_pending'`
- `pytest -q truffles-api/tests/test_pending_pack_lexicons.py -k 'manager_resolve'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner'`

## Evidence
- `_legacy.py` diff showing direct owner-surface export overrides for the moved handover family
- targeted tests proving `_legacy` now points to the owner surface
- guard/session results

## Rollback
1. Restore `_legacy.py` to pure decision-export mirroring.
2. Revert test updates.
3. Regenerate packet and rerun targeted checks.

## No-go
- no fake progress via comments or doc-only claims
- no edits to frozen caller files
- no new wrapper layer that still routes external callers through `decision.py`
- no weakening of existing tests/guards

## Risks / blockers
- some tests intentionally patch `decision.py` symbols for decision-internal behavior; those must stay untouched
- if external callers still reach `decision.py` through another adapter path after `_legacy.py` changes, the block fails
- `_legacy.py` must remain compatible for all non-handover exports

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded local-only compatibility routing change in non-frozen `_legacy.py`
- **Go/no-go signals:** `_legacy` points to owner surface for moved handover symbols; targeted tests and guards green
- **Rollback:** revert `_legacy.py` overrides and rerun checks
- **Post-release monitoring window:** local deterministic/runtime checks only; no product-level correctness claim

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** compile + targeted compat/handover tests + required guards only
- **Stop condition:** if `_legacy` cannot bypass `decision.py` for the moved family without touching frozen callers or breaking runtime compatibility, stop with `GAP`
- **Escalation path:** `Top Architect`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** `decision.py` internal wrappers remain for its own frozen runtime callsites; supporting helper reuse from `escalation_service.py` remains; proof bundle remains open
- **Why not in this block:** this block is strictly about deleting the external frozen compatibility seam, not rewriting internal frozen runtime
- **Risk if deferred:** frozen callers keep traversing an obsolete compatibility layer and the owner-family closure claim stays partial
- **Linked follow-up Task Package(s):** `TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922` (to be authored after this block)
- **Expiry/trigger to stop deferral:** before any next handover-family change or any claim that the frozen compat seam is closed

## Next-block contract (mandatory)
- **Next block objective:** collapse or classify the remaining supporting helper split between `handover_owner_service.py` and `escalation_service.py`
- **First deterministic check command:** `rg -n "_build_handover_meta|_get_latest_user_message|_get_recent_user_messages|_build_simulated_topic_id|resolve_telegram_routing|get_or_create_topic|send_telegram_notification" truffles-api/app/services/handover_owner_service.py truffles-api/app/services/escalation_service.py`
- **Blocked-by conditions:** if `_legacy.py` still routes any moved handover symbol through `decision.py` after this block, or if frozen callers require direct edits
- **Owner role for closure:** `Top Architect`
