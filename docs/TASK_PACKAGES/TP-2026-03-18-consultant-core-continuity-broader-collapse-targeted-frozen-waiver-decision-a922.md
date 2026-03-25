# TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTINUITY-BROADER-COLLAPSE-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTINUITY-BROADER-COLLAPSE-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTINUITY-BROADER-COLLAPSE-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one exact frozen-waiver decision for `continuity_broader_collapse`. This block must prove that truthful package closure is blocked by frozen callsites, define the narrowest admissible waiver scope, and reject any fallback that would restart seam farming or create a new continuity hotspot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "_handle_pending_gate|_handle_handover_confirmation_gate|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply|_restore_pending_resume_payload|pending_resume" truffles-api/app/routers/webhook truffles-api/app/services/state_service.py truffles-api/app/core/dialog_state_service.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '10490,10580p;11050,11080p;11470,11485p;18390,18410p'`
  - `nl -ba truffles-api/app/routers/webhook/pending.py | sed -n '112,242p;399,586p;678,842p'`
  - `rg -n "project_expected_reply_projections|clear_session_memory_expected_reply|touch_session_memory_payload|sync_context_manager_expected_reply_state|build_expected_reply_context_sync_result|capture_pending_resume_payload|restore_pending_resume_payload|derive_pending_resume_reason|derive_pending_booking_resume_boundary_payload|set_context_handover_confirmation|set_context_re_entry_required|clear_context_re_entry_required|clear_context_manager_carryover_family" truffles-api/app/core/dialog_state_service.py`
- `FACT findings`:
  - frozen `truffles-api/app/routers/webhook/decision.py` still directly invokes the residual pending continuity owners at `truffles-api/app/routers/webhook/decision.py:11062` and `truffles-api/app/routers/webhook/decision.py:11472`.
  - the residual family recorded in the master ledger is still live inside frozen `truffles-api/app/routers/webhook/pending.py`:
    - `truffles-api/app/routers/webhook/pending.py:112` handover-confirmation continuity cleanup / trace / commit
    - `truffles-api/app/routers/webhook/pending.py:421` no-handover reset
    - `truffles-api/app/routers/webhook/pending.py:482` pending close
    - `truffles-api/app/routers/webhook/pending.py:510` pending ack restore / re-entry trace
    - `truffles-api/app/routers/webhook/pending.py:678` pending SLA state mutation / trace/meta
  - non-frozen `truffles-api/app/routers/webhook/session_memory.py` still owns live continuity mutation helpers at `truffles-api/app/routers/webhook/session_memory.py:72`, `truffles-api/app/routers/webhook/session_memory.py:150`, and `truffles-api/app/routers/webhook/session_memory.py:227`.
  - `truffles-api/app/services/state_service.py` already owns part of the same continuity family for pending-resume capture / restore / boundary activation / session-memory preserve policy.
  - `truffles-api/app/core/dialog_state_service.py` already owns the canonical payload/projection primitives for pending-resume restore, re-entry payloads, session-memory expected-reply clearing, handover-confirmation payloads, and carryover reset semantics.
- `Detected drift (docs vs code)`:
  - the package TP correctly chose `DialogStateService` plus one bounded coordinator as the truthful destination, but the remaining old live authority cannot die without touching a narrow frozen surface in `decision.py` and `pending.py`.
  - moving only `session_memory.py` would be another micro-cut and would not close the package-level old mixed continuity family.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Branch by Abstraction" "StranglerFigApplication"`
- **Date/time (local):** `2026-03-18 14:46:24 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/BranchByAbstraction.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary-style architecture guidance from Martin Fowler
- **Existing solutions found:**
  - `Branch by Abstraction`: transitional architecture is valid only while it is retiring an old implementation rather than preserving two live authorities forever
  - `Strangler Fig`: legacy modernization should move one bounded behavior family at a time, but only when the old behavior actually becomes replaceable and dies
- **Decision:** `reuse/integrate`
  - keep the current `DialogStateService` + bounded `state_service.py` target
  - use a narrow frozen waiver only where the live old continuity authority still blocks package closure
- **Rejected options:**
  - move only `session_memory.py` and count it as package progress
  - invent a new `continuity_service.py`
  - grow `state_service.py` into a transport-plus-continuity hotspot to avoid the waiver
  - claim the package can close without touching the frozen pending callsites

## Root cause (mandatory)
- **Symptom:** the `continuity_broader_collapse` package is still blocked even though the truthful non-frozen destination is already known.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/decision.py:11062` and `truffles-api/app/routers/webhook/decision.py:11472` and confirm they still call frozen pending continuity gates directly.
  2. Inspect `truffles-api/app/routers/webhook/pending.py:112`, `truffles-api/app/routers/webhook/pending.py:421`, `truffles-api/app/routers/webhook/pending.py:482`, `truffles-api/app/routers/webhook/pending.py:510`, and `truffles-api/app/routers/webhook/pending.py:678` and confirm the old continuity authority is still live there.
  3. Inspect `truffles-api/app/routers/webhook/session_memory.py:72`, `truffles-api/app/routers/webhook/session_memory.py:150`, and `truffles-api/app/routers/webhook/session_memory.py:227` and confirm that only moving these helpers would leave the frozen pending continuity family alive.
  4. Inspect `truffles-api/app/core/dialog_state_service.py` and `truffles-api/app/services/state_service.py` and confirm the canonical destination already exists outside the frozen files.
- **Evidence to capture:**
  - frozen callsites in `decision.py`
  - live residual authority in frozen `pending.py`
  - non-frozen continuity primitives already present in `DialogStateService` / `state_service.py`
  - proof that `session_memory.py` alone is not the package-level old authority family
- **Five Whys (or equivalent):**
  1. Why is the package still open? Because the old continuity authority remains live in frozen pending gates.
  2. Why can't non-frozen code alone close it? Because frozen `decision.py` still routes into those pending gates directly.
  3. Why isn't moving only `session_memory.py` enough? Because the master residual ledger defines the continuity problem as the broader mixed family across pending resume, reset, re-entry, SLA, and handover confirmation.
  4. Why not create another coordinator to bypass the freeze? Because that would move the mixed hotspot instead of deleting it.
  5. Why is a targeted waiver now the honest next step? Because the destination owner is already proven, and the only remaining blocker is the narrow frozen legacy surface that still holds the live authority.
- **Root cause statement:** the continuity package is blocked not by missing destination architecture but by narrow frozen legacy callsites in `decision.py` and live residual continuity authority in frozen `pending.py`; without a targeted waiver, the package can only produce another partial seam cut rather than truthful family closure.
- **Fix mechanism:**
  - publish one targeted frozen-waiver decision that names the exact frozen scope
  - allow the next runtime block to reduce the frozen continuity family to bounded owner-surface invocation only
  - reject any fallback that keeps multi-owner continuity alive or restarts seam farming

## FACT vs INFERENCE verdict
- **FACT:** `DialogStateService` plus bounded `state_service.py` is already the truthful destination for continuity payload/projection ownership.
- **FACT:** the old live package-level continuity authority still remains in frozen `pending.py` and is reached through frozen `decision.py` callsites.
- **FACT:** moving only `session_memory.py` would not delete the main old mixed continuity family from the residual ledger.
- **INFERENCE:** a narrow frozen-file waiver is the only honest next move if the goal remains package-level closure rather than another partial seam reduction.
- **Decision:** switch canon from `continuity_broader_collapse package TP` to one targeted frozen-waiver decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - existing pending-resume/runtime tests in `truffles-api/tests/test_state_service.py`, `truffles-api/tests/test_pending_pack_lexicons.py`, and `truffles-api/tests/test_message_endpoint.py`
  - existing architecture/session guard flow
- **External reuse:**
  - Martin Fowler `Branch by Abstraction`
  - Martin Fowler `Strangler Fig`
- **Why not reinvent the wheel:**
  - the new continuity owner already exists
  - the remaining work is deleting a narrow frozen authority seam, not inventing another continuity layer

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `pending-continuity-targeted-freeze-waiver-decision`
- **Why this profile fits:** this is a doc-only decision block that unlocks a narrowly-scoped frozen runtime change next.

## Invariant
- no runtime code edits in this block
- no claim that continuity package closure happened in this block
- no new continuity service, wrapper forest, or `state_service.py` hotspot growth
- the future waiver scope must stay exact and narrow
- FACT vs INFERENCE separation stays explicit

## Scope
- prove that the continuity package is blocked by narrow frozen legacy authority
- define the exact frozen scope required for truthful package closure
- reject the `session_memory.py`-only fallback as fake package progress
- switch canon to the waiver decision block and lock the next runtime move

## Out of scope
- runtime implementation
- updating `docs/LEGACY_SUNSET.yaml`
- editing frozen files in this block
- reordering backlog beyond the continuity package
- public entrypoint materialization, debounce, proof path, or multi-pack acceptance

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this targeted frozen-waiver decision TP with exact scope, RCA, and next-block contract.
2. Record the factual blocked state: package closure cannot happen under the current freeze without another fake micro-cut.
3. Lock the exact future waiver scope to the continuity residual family in frozen `decision.py` and `pending.py` only.
4. Switch canon so the next nonnegotiable move is the runtime implementation under that targeted waiver.
5. Regenerate packet and rerun governance/session checks.

## Exact future waiver scope
- `truffles-api/app/routers/webhook/decision.py`
  - the direct invocation of `_handle_pending_gate(...)`
  - the direct invocation of `_handle_handover_confirmation_gate(...)`
- `truffles-api/app/routers/webhook/pending.py`
  - `_handle_handover_confirmation_gate(...)` only for the continuity family at the residual ledger hotspots rooted at `:112`
  - `_handle_pending_gate(...)` only for the continuity family at the residual ledger hotspots rooted at `:421`, `:482`, `:510`, and `:678`
- **Not in waiver scope:**
  - `truffles-api/app/routers/webhook/booking.py`
  - broader `decision.py` semantic/boundary flows
  - unrelated pending transport/media forwarding branches
  - `manager_active` silent-forward path unless the runtime block proves it is inseparable from the continuity family

## DoD
- the targeted frozen-waiver decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
- canon/packet/test all agree that the current block is the targeted continuity frozen-waiver decision
- the exact frozen scope is machine-readable in canon/session artifacts
- the next move is no longer ambiguous or falsely package-nonfrozen
- required checks are green

## Checks
- `rg -n "_handle_pending_gate|_handle_handover_confirmation_gate|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply|_restore_pending_resume_payload|pending_resume" truffles-api/app/routers/webhook truffles-api/app/services/state_service.py truffles-api/app/core/dialog_state_service.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP, canon, packet, session, and state
- frozen callsite scan proving the package is blocked without the waiver
- owner-surface scan proving the destination already exists outside the frozen files
- green governance/session checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the waiver scope cannot stay exact and package-bounded, stop and publish `GAP` instead of widening the freeze
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the targeted frozen-waiver decision and next move
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next runtime block must stay inside the exact future waiver scope defined here

## Rollback
1. Revert this decision TP and the matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime edits hidden inside this decision block
- no `session_memory.py`-only cut counted as package closure
- no new continuity service or wrapper forest
- no blanket frozen-file waiver beyond the exact future scope listed above
- no claim that the old continuity family is already dead

## Risks / blockers
- the runtime implementation may prove that `manager_active` or another pending branch is inseparable from the residual family, which would require stopping and reopening the waiver decision instead of widening silently
- the frozen pending family mixes transport-side reply/commit behavior with continuity mutations, so the next runtime block must keep destination ownership bounded and resist moving transport logic into `state_service.py`
- `docs/LEGACY_SUNSET.yaml` will need exact scoped updates in the runtime block if the waiver is exercised

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - the continuity package is still unimplemented
  - the old continuity family remains live in frozen `decision.py` and `pending.py`
  - `public_entrypoint_materialization_contract`, `debounce_buffer_owner_convergence`, `proof_black_box_completion`, and `multi_pack_acceptance` remain open
- **Why not in this block:**
  - this block only decides the truthful waiver scope and next move; it does not execute runtime changes
- **Risk if deferred:**
  - the team may either stall on the freeze boundary or restart fake micro-cuts that do not kill the old package-level continuity family
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-implementation-a922.md` (to be authored or executed next)
- **Expiry/trigger to stop deferral:**
  - before any next continuity runtime implementation starts
  - immediately if anyone proposes `session_memory.py`-only closure as package progress

## Next-block contract (mandatory)
- **Next block objective:** implement the continuity runtime family convergence under the exact targeted frozen waiver so the old pending-resume / reset / pending-SLA / handover-confirmation continuity family becomes deleted or unreachable as live authority
- **First deterministic check command:** `rg -n "_handle_pending_gate|_handle_handover_confirmation_gate|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/session_memory.py`
- **Blocked-by conditions:**
  - if the runtime plan requires widening the waiver beyond the exact future scope above
  - if the runtime plan cannot keep the destination inside `DialogStateService` plus bounded `state_service.py`
  - if the runtime plan leaves the old frozen continuity family live and merely adds wrappers/delegates
- **Owner role for closure:** `Top Architect`
