# TP-2026-03-15-consultant-core-service-and-consult-carryover-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SERVICE-AND-CONSULT-CARRYOVER-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CLASS-CARRYOVER-CANONICAL-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-class-carryover-canonical-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `service_carryover` и `consult_context` перестают держать собственные normalize/get/set fallback rules в `truffles-api/app/routers/webhook/context_manager.py` и начинают проходить через `DialogStateService`, при сохранении canonical projection priority и legacy fallback.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `truffles-api/tests/test_consult_followup_guard.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "_prune_service_carryover|_get_service_carryover|_set_service_carryover|_prune_consult_context|_get_consult_context|_set_consult_context" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/response.py`
  - `rg -n "service_carryover|consult_context|consult_return" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_demo_salon_eval.py truffles-api/tests/test_consult_followup_guard.py`
- `FACT findings`:
  - `service_carryover` already mirrors canonical referent state, but legacy fallback payload normalization and read/write shaping still live in `context_manager.py`.
  - `consult_context` already mirrors canonical consult state, but legacy fallback payload normalization and read/write shaping still live in `context_manager.py`.
  - existing tests already pin canonical service carryover reads and consult-followup guard behavior.
  - these carriers are already mostly canonicalized, so the remaining authority to remove is helper-local fallback shaping.
- `Detected drift (docs vs code)`: canonical dialog state is already preferred for these carriers, but the fallback carrier rules still bypass `DialogStateService`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy.deepcopy documentation`
- **Date/time (local):** `2026-03-15 19:51 Asia/Almaty`
- **Why this query is precise:** both carriers still store mutable nested payloads/lists (`questions`, referent payloads, trace-facing metadata), and the bridge must avoid aliasing between canonical and legacy fallback shapes.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard library mechanism for recursively copying nested mutable structures so bridge writes/reads do not share later mutations.
- **Decision:** `reuse + integrate` — keep the carryover bridge in `DialogStateService` and use `deepcopy(...)` for detached fallback payloads instead of inventing a custom copier.
- **Rejected options:**
  - widening into full consult-return response refactor
  - touching frozen legacy semantic router files
  - creating another helper module just for carryovers
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `service_carryover` and `consult_context` still retain helper-local fallback shaping in `context_manager.py`.
- **Minimal reproduction:**
  1. Inspect `_get/_set/_prune_service_carryover(...)` and `_get/_set/_prune_consult_context(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Note that canonical projection is already preferred, but the legacy fallback payload still has its own local normalization/read logic.
  3. Compare with the architectural goal that continuity shaping converges on `DialogStateService`.
- **Evidence to capture:**
  - `DialogStateService` owns bounded build/get helpers for both carryovers.
  - `context_manager.py` delegates fallback shaping to that bridge while preserving canonical-priority semantics.
  - existing service carryover and consult-followup tests stay green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because these two carryovers still have helper-local fallback shaping.
  2. Why is that wrong? Because canonical dialog state should be the continuity seam, not duplicated helper rules.
  3. Why handle both together? Because both are message-count carryovers already mirrored canonically and share the same bounded helper pattern.
  4. Why not widen into prompt rendering? Because consult-return wording is response behavior, not the remaining continuity-authority seam.
  5. Why does this reduce drift? Because another pair of live carryovers stops authoring fallback semantics outside `DialogStateService`.
- **Root cause statement:** continuity ownership is still split because `service_carryover` and `consult_context` keep their legacy fallback shaping inside `context_manager.py` instead of flowing fully through `DialogStateService`.
- **Fix mechanism:**
  - add bounded carryover build/get helpers for both fallback payload shapes to `DialogStateService`
  - route `context_manager.py` set/get fallback branches through those helpers while keeping canonical projection priority
  - add deterministic service coverage and targeted compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - canonical projection helpers already in `context_manager.py`
  - existing carryover tests in `truffles-api/tests/test_message_endpoint.py` and `truffles-api/tests/test_demo_salon_eval.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` docs for detached payload handling
- **Why not reinvent the wheel:** the repo already has canonical carryover projections and the standard deep-copy primitive; this block should only remove duplicated fallback shaping.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `14`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for two already-canonicalized carryovers with deterministic verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible service carryover / consult followup behavior for valid flows.
- No widening into consult-return response formatting or semantic router edits.

## Scope
- Add bounded `service_carryover` and `consult_context` fallback build/get helpers to `DialogStateService`.
- Route `context_manager.py` fallback read/write shaping through those helpers while preserving canonical projection priority.
- Add deterministic service coverage and reuse existing runtime compatibility tests.
- Sync source-of-truth/state/session docs.

## Out of scope
- consult-return wording changes
- `compact_summary`
- `low_confidence_retry_count`
- frozen router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-service-and-consult-carryover-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this carryover TP with RCA and one web search.
2. Add bounded `service_carryover` and `consult_context` fallback build/get helpers to `DialogStateService`.
3. Route `context_manager.py` fallback shaping through that bridge without touching frozen semantic router files.
4. Add deterministic service coverage and run targeted compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded fallback build/get behavior for `service_carryover` and `consult_context`.
- `context_manager.py` no longer authors those fallback shapes directly.
- Existing service carryover and consult-followup tests remain green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'service_carryover or consult'`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py -k 'test_demo_salon_eval_records_canonical_service_projection or test_info_carryover_preserves_parking_for_short_followup'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` carryover bridge helpers
- updated `context_manager.py` delegating `service_carryover` and `consult_context` fallback shaping
- deterministic service coverage plus targeted carryover compatibility tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or widening into broader response refactors, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** carryover tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the remaining non-carryover state writers separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual service+consult carryover bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No consult-return wording changes.

## Risks/Blockers
- over-normalizing `consult_context.questions` could change followup wording or replay trace shape.
- service carryover must keep canonical-priority semantics and fallback metadata shape (`projection_source`, `canonical_state_owner`).

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `compact_summary`, `low_confidence_retry_count`, and broader context/state writer ownership still remain outside the bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has several helper-owned non-carryover state writers after this cut.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new context/state carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the remaining non-carryover context/state writer ownership after these carryover bridges.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: service/consult carryover fallback shaping still authored in `context_manager.py`; source-of-truth not synced; deterministic bridge coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and consult-return response wording
- `Open risks`: changing `consult_context.questions` normalization in a way that alters followup text
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'service_carryover or consult'`
