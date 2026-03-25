# TP-2026-03-15-consultant-core-low-confidence-retry-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-LOW-CONFIDENCE-RETRY-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SERVICE-AND-CONSULT-CARRYOVER-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-service-and-consult-carryover-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения low-confidence behavior: `low_confidence_retry_count` перестаёт держать собственные normalize/get/set rules в `truffles-api/app/routers/webhook/context_manager.py` и начинает проходить через `DialogStateService`, при сохранении `retry_offered_at` orchestration на тонком legacy helper.

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
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "low_confidence_retry_count|_reset_low_confidence_retry|retry_offered_at|should_offer_low_confidence_retry" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/state_service.py`
  - `rg -n "LowConfidenceRetryGate|retry_offered_at" truffles-api/tests/test_state_service.py truffles-api/tests/test_health_service.py`
- `FACT findings`:
  - `low_confidence_retry_count` read/write normalization still lives only in `context_manager.py`.
  - `_reset_low_confidence_retry(...)` mixes two concerns: context counter reset and `conversation.retry_offered_at = None`.
  - `response.py` consumes the counter through legacy helper calls, while rate-limit window logic remains in `should_offer_low_confidence_retry(...)`.
  - current tests pin only the `retry_offered_at` window gate; there is no deterministic bridge coverage for context counter shaping.
- `Detected drift (docs vs code)`: continuity canon says writer ownership should converge on `DialogStateService`, but this counter still has helper-local shaping outside the bridge.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html python int built-in function docs`
- **Date/time (local):** `2026-03-15 20:11 Asia/Almaty`
- **Why this query is precise:** this slice canonicalizes an integer counter coming from mutable legacy context, so the bridge needs one authoritative reference for Python integer coercion semantics instead of ad-hoc parsing assumptions.
- **Sources opened (from this query):**
  - `Built-in Functions — int()` — `https://docs.python.org/3/library/functions.html#int`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `int(x)` converts a number or string to an integer and raises `TypeError`/`ValueError` for unsupported values, which matches the existing defensive fallback pattern.
- **Decision:** `reuse + integrate` — keep integer normalization inside `DialogStateService` via the existing `_canonical_int(...)` helper rather than inventing a new parser.
- **Rejected options:**
  - widening into a broader retry/handover refactor
  - touching frozen legacy semantic router files
  - moving `retry_offered_at` ownership in the same block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `low_confidence_retry_count` still retains helper-local normalization/read/write logic in `context_manager.py`.
- **Minimal reproduction:**
  1. Inspect `_get_low_confidence_retry_count(...)` and `_set_low_confidence_retry_count(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Inspect `truffles-api/app/routers/webhook/response.py` low-confidence retry lanes and note they depend on those helper-owned rules.
  3. Compare with the continuity goal that counter shaping should converge on `DialogStateService`.
- **Evidence to capture:**
  - `DialogStateService` owns bounded get/set/reset helpers for the counter.
  - `context_manager.py` delegates counter shaping to the bridge while keeping `_reset_low_confidence_retry(...)` as thin orchestration for `retry_offered_at`.
  - window-gate tests and new deterministic bridge tests stay green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because the low-confidence counter is still normalized directly in `context_manager.py`.
  2. Why is that wrong? Because the bridge is supposed to become the single shaping seam for continuity carriers.
  3. Why not move everything at once? Because `retry_offered_at` is a separate DB-backed gate and widening this block would mix continuity collapse with semantic/runtime policy changes.
  4. Why is this block safe? Because it centralizes only counter shaping and keeps the external retry window behavior unchanged.
  5. Why does this reduce drift? Because one more live context carrier stops authoring its own normalization rules outside `DialogStateService`.
- **Root cause statement:** continuity ownership is still split because `low_confidence_retry_count` keeps helper-local integer normalization in `context_manager.py` instead of flowing through `DialogStateService`.
- **Fix mechanism:**
  - add bounded `get/set/reset_low_confidence_retry_count(...)` helpers to `DialogStateService`
  - route `context_manager.py` counter reads/writes through that bridge
  - keep `_reset_low_confidence_retry(...)` as a thin orchestration helper that clears both the bridged counter and `conversation.retry_offered_at`
  - add deterministic bridge coverage plus keep existing retry-window tests green

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - existing `_canonical_int(...)` helper
  - existing low-confidence retry window tests in `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - official Python `int()` documentation
- **Why not reinvent the wheel:** the repo already has a canonical integer normalizer and low-confidence runtime behavior; this block should only remove duplicated counter shaping.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `14`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for one small counter carrier with deterministic verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to low-confidence retry window behavior or handover thresholds.
- No widening into broader retry/handover policy refactors.

## Scope
- Add bounded low-confidence retry count helpers to `DialogStateService`.
- Route `context_manager.py` counter get/set/reset through that bridge.
- Add deterministic bridge coverage and keep retry-window tests green.
- Sync source-of-truth/state/session docs.

## Out of scope
- `retry_offered_at` policy changes
- handover confirmation behavior
- `compact_summary`
- frozen router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-low-confidence-retry-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this retry-counter TP with RCA and one web search.
2. Add bounded low-confidence retry count helpers to `DialogStateService`.
3. Route `context_manager.py` counter reads/writes through that bridge without touching frozen semantic router files.
4. Add deterministic bridge coverage and run retry-window compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded get/set/reset behavior for `low_confidence_retry_count`.
- `context_manager.py` no longer authors counter normalization directly.
- Existing retry-window tests remain green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'LowConfidenceRetryGate'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` retry-counter bridge helpers
- updated `context_manager.py` delegating low-confidence counter shaping
- deterministic bridge coverage plus retry-window compatibility tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires moving `retry_offered_at` policy or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** dialog-state tests + retry-window tests + architecture suite + packet + arch guard + session check all green
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
  - active block metadata must match the actual low-confidence retry bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No retry-policy threshold changes.

## Risks/Blockers
- accidentally widening this slice into `retry_offered_at` policy would mix persistence timing with continuity normalization.
- response paths expect integer semantics for the counter, so the bridge must preserve the current clamp-to-zero behavior.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `compact_summary` and broader context/state writer ownership still remain outside the bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has helper-owned non-carryover writers after this cut.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new context/state carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next remaining non-carryover state writer after the retry counter, with `compact_summary` as the next candidate.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: low-confidence retry counter shaping still authored in `context_manager.py`; source-of-truth not synced; deterministic bridge coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and low-confidence policy thresholds
- `Open risks`: accidentally changing `retry_offered_at` behavior while centralizing only the counter
- `First command to verify`: `pytest -q truffles-api/tests/test_state_service.py -k 'LowConfidenceRetryGate'`
