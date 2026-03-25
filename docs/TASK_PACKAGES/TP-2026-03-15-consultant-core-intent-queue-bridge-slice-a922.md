# TP-2026-03-15-consultant-core-intent-queue-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-INTENT-QUEUE-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CLARIFY-ATTEMPT-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-clarify-attempt-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения multi-intent behavior: `intent_queue` перестаёт держать собственные read/write shaping rules в `truffles-api/app/routers/webhook/guards.py` и начинает проходить через `DialogStateService`, при сохранении existing queue payload shape, prompt wording, and frozen-reader compatibility.

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
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "_get_intent_queue|_set_intent_queue|_format_intent_queue_prompt|intent_queue" truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
  - `rg -n "intent_queue" truffles-api/app/core/dialog_state_service.py truffles-api/tests/test_dialog_state_service.py`
- `FACT findings`:
  - `intent_queue` read/write shaping still lives only in `truffles-api/app/routers/webhook/guards.py`.
  - the live writer is consumed by frozen `truffles-api/app/routers/webhook/decision.py`, so this block must preserve the stored queue contract exactly.
  - the stored payload shape is bounded: `context["intent_queue"] = list[str]` with casefolded, de-duplicated values preserving first-match order.
  - existing integration coverage already pins prompt, queue choice, queue clearing, and booking expected-reply interaction in `truffles-api/tests/test_message_endpoint.py`, but there is no deterministic bridge coverage for the queue shaping itself.
- `Detected drift (docs vs code)`: continuity canon says live context carriers should converge on `DialogStateService`, but `intent_queue` still authors its own queue normalization outside that bridge.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy.deepcopy documentation`
- **Date/time (local):** `2026-03-15 20:39 Asia/Almaty`
- **Why this query is precise:** this slice rewrites one list-backed context carrier, so the bridge needs one authoritative reference for detached mutable updates instead of helper-local aliasing assumptions.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard-library mechanism for recursively copying mutable structures before bridge updates so nested context writes do not alias caller-owned payloads.
- **Decision:** `reuse + integrate` — keep queue normalization and write-shaping in `DialogStateService`; use detached copies on bridge writes instead of widening router helper ownership.
- **Rejected options:**
  - widening into queue-choice semantic resolver changes
  - touching frozen legacy semantic router files
  - moving prompt wording or intent matching into the bridge in this block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `intent_queue` still retains helper-local read/write shaping in `guards.py`.
- **Minimal reproduction:**
  1. Inspect `_get_intent_queue(...)` and `_set_intent_queue(...)` in `truffles-api/app/routers/webhook/guards.py`.
  2. Inspect frozen `truffles-api/app/routers/webhook/decision.py` and note that it consumes those helpers but does not need to own queue normalization itself.
  3. Inspect `truffles-api/tests/test_message_endpoint.py` and note that integration coverage exists for runtime behavior, but not for the bridge shaping itself.
- **Evidence to capture:**
  - `DialogStateService` owns bounded `intent_queue` normalization plus get/set shaping.
  - `guards.py` delegates queue shaping to that bridge while keeping prompt formatting and choice semantics unchanged.
  - existing intent-queue integration remains green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because `intent_queue` normalization still lives in router helper code.
  2. Why is that wrong? Because live continuity carriers should converge on `DialogStateService`.
  3. Why not move full queue behavior? Because prompt wording, choice matching, and downstream semantic branching belong to runtime orchestration and frozen readers, not this bounded continuity seam.
  4. Why is this block safe? Because it centralizes only queue payload shaping while preserving the existing stored list contract and runtime behavior.
  5. Why does this reduce drift? Because another live context carrier stops defining its own normalization rules outside the bridge.
- **Root cause statement:** continuity ownership is still split because `intent_queue` keeps helper-local read/write shaping in `guards.py` instead of flowing through `DialogStateService`.
- **Fix mechanism:**
  - add bounded `intent_queue` normalize/get/set helpers to `DialogStateService`
  - route `_get_intent_queue(...)` and `_set_intent_queue(...)` in `guards.py` through that bridge
  - keep `_format_intent_queue_prompt(...)`, selection logic, and frozen-reader behavior unchanged
  - add deterministic bridge coverage plus keep multi-intent integration green

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - existing bridge pattern from `clarify_attempts`, `compact_summary`, and other continuity slices
  - existing intent-queue integration tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation
- **Why not reinvent the wheel:** the repo already has the continuity bridge and the standard nested-copy primitive; this block should only remove duplicated queue shaping.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `14`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for one list-backed carrier with deterministic verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to intent-queue prompt wording, queue-choice semantics, or booking-interrupt behavior.
- No widening into generic queue refactors.

## Scope
- Add bounded `intent_queue` normalize/get/set helpers to `DialogStateService`.
- Route `guards.py` intent-queue payload shaping through that bridge.
- Add deterministic bridge coverage and keep intent-queue integration green.
- Sync source-of-truth/state/session docs.

## Out of scope
- intent-choice matching changes
- prompt wording changes
- semantic router changes in frozen files
- debounce/buffer
- pending-resume queue refactor

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-intent-queue-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this intent-queue TP with RCA and one web search.
2. Add bounded `intent_queue` normalize/get/set helpers to `DialogStateService`.
3. Route `guards.py` intent-queue payload shaping through that bridge without touching frozen semantic router files.
4. Add deterministic bridge coverage and run existing intent-queue compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded get/set behavior for `intent_queue`.
- `guards.py` no longer authors intent-queue payload shaping directly.
- Existing intent-queue integration remains green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_intent_queue_sets_context_and_prompt or test_intent_queue_info_limit_skips_booking or test_intent_queue_choice_pricing_replies_and_updates_queue or test_intent_queue_choice_booking_starts_prompt_and_clears_queue or test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` intent-queue bridge helpers
- updated `guards.py` delegating intent-queue shaping
- deterministic bridge coverage plus intent-queue integration tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or changes prompt/choice semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** dialog-state tests + intent-queue compatibility tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next block should either take another safe non-carryover writer or switch back to proof/semantic cutover if no safe continuity seam remains

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual intent-queue bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `guards.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No changes to prompt wording or queue-choice semantics.

## Risks/Blockers
- any change to the stored queue shape would silently affect frozen `decision.py` readers.
- this slice must not pull `_format_intent_queue_prompt(...)` or `_select_intent_from_queue(...)` into the bridge.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader context/state writer ownership, pending-resume queue handling, and proof-path excision still remain outside the bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has helper-owned writers after this cut.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new queue-carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: take the next safe bounded non-carryover continuity slice after `intent_queue`, or switch back to proof/semantic cutover if no safe writer remains.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: intent-queue payload shaping still authored in `guards.py`; source-of-truth not synced; deterministic bridge coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files; prompt wording; queue-choice logic
- `Open risks`: accidentally changing queue ordering/dedup semantics or widening into semantic behavior
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_intent_queue_sets_context_and_prompt'`
