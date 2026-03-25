# TP-2026-03-15-consultant-core-compact-summary-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-COMPACT-SUMMARY-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-LOW-CONFIDENCE-RETRY-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-low-confidence-retry-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения memory-summary behavior: `compact_summary` перестаёт держать собственные text/payload shaping rules в `truffles-api/app/routers/webhook/context_manager.py` и начинает проходить через `DialogStateService`, при сохранении legacy payload shape и existing `decision.py` reads.

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
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

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
  - `rg -n "compact_summary|_build_compact_summary_text|_update_compact_summary|summary_updated" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/decision.py`
  - `rg -n "compact_summary|memory_summary|summary_updated" truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - `_build_compact_summary_text(...)` and `_update_compact_summary(...)` still live only in `context_manager.py`.
  - the only active write path is helper-owned and is triggered from clarify-limit escalation code in `guards.py`.
  - frozen `decision.py` still reads `context_manager.compact_summary.text` directly to seed `memory_summary`.
  - current tests pin memory-summary consumption, but there is no deterministic bridge coverage for compact-summary shaping itself.
- `Detected drift (docs vs code)`: continuity canon says shaping should converge on `DialogStateService`, but `compact_summary` still authors its text assembly and payload shape in helper-local code.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/stdtypes.html python str join documentation`
- **Date/time (local):** `2026-03-15 20:19 Asia/Almaty`
- **Why this query is precise:** this slice keeps the compact summary as a joined string assembled from optional fragments, so the bridge needs one authoritative reference for deterministic string assembly from filtered parts.
- **Sources opened (from this query):**
  - `Built-in Types — str.join()` — `https://docs.python.org/3/library/stdtypes.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `str.join(iterable)` is the standard built-in mechanism for concatenating string fragments with a fixed separator, which matches the current compact-summary shape.
- **Decision:** `reuse + integrate` — keep compact-summary assembly as filtered fragments plus `"; ".join(parts)` inside `DialogStateService` instead of inventing custom concatenation logic.
- **Rejected options:**
  - widening into a broader booking/refusal refactor
  - touching frozen legacy semantic router files
  - changing `decision.py` read-paths in this block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `compact_summary` still retains helper-local text/payload shaping in `context_manager.py`.
- **Minimal reproduction:**
  1. Inspect `_build_compact_summary_text(...)` and `_update_compact_summary(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Inspect `truffles-api/app/routers/webhook/guards.py` and note clarify-limit escalation still writes compact summary through that helper.
  3. Inspect frozen `truffles-api/app/routers/webhook/decision.py` and note it consumes only the stored payload field `compact_summary.text`.
- **Evidence to capture:**
  - `DialogStateService` owns bounded compact-summary text and payload shaping.
  - `context_manager.py` delegates helper behavior to that bridge while keeping the stored payload shape unchanged.
  - existing memory-summary integration remains green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because compact-summary text assembly still lives in helper-local router code.
  2. Why is that wrong? Because continuity carriers should converge on one shaping seam in `DialogStateService`.
  3. Why not move the read path too? Because the read path is inside frozen `decision.py` and this block must not widen into frozen semantic files.
  4. Why is this block safe? Because it centralizes only the write-side shaping while preserving the exact stored payload contract that legacy readers already use.
  5. Why does this reduce drift? Because one more context carrier stops defining its own text/payload rules outside the bridge.
- **Root cause statement:** continuity ownership is still split because `compact_summary` keeps helper-local text and payload shaping in `context_manager.py` instead of flowing through `DialogStateService`.
- **Fix mechanism:**
  - add bounded compact-summary text/payload helpers to `DialogStateService`
  - route `_build_compact_summary_text(...)` and `_update_compact_summary(...)` in `context_manager.py` through that bridge
  - keep the stored payload shape as `{"text", "updated_at", "reason"}`
  - add deterministic bridge coverage plus keep memory-summary compatibility green

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - existing `_canonical_int(...)`/projection helpers pattern
  - existing memory-summary integration test in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `str.join()` documentation
- **Why not reinvent the wheel:** the repo already uses filtered fragment assembly and Python already provides the correct join primitive; this block should only remove duplicated helper-local shaping.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `14`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for one text carrier with deterministic verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to stored compact-summary payload shape consumed by `decision.py`.
- No widening into broader booking/refusal or memory-summary policy refactors.

## Scope
- Add bounded compact-summary text/payload helpers to `DialogStateService`.
- Route `context_manager.py` compact-summary helper shaping through that bridge.
- Add deterministic bridge coverage and keep existing memory-summary integration green.
- Sync source-of-truth/state/session docs.

## Out of scope
- `decision.py` read-path changes
- booking/refusal semantics changes
- debounce/buffer
- frozen router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-compact-summary-bridge-slice-a922.md`
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
1. Publish this compact-summary TP with RCA and one web search.
2. Add bounded compact-summary text/payload helpers to `DialogStateService`.
3. Route `context_manager.py` compact-summary helper shaping through that bridge without touching frozen semantic router files.
4. Add deterministic bridge coverage and run memory-summary compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded compact-summary text/payload shaping.
- `context_manager.py` no longer authors compact-summary text/payload directly.
- Existing memory-summary integration remains green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'compact_summary or LowConfidenceRetryGate'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_llm_policy_core_receives_memory_hints_and_writes_meta'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` compact-summary bridge helpers
- updated `context_manager.py` delegating compact-summary shaping
- deterministic bridge coverage plus existing memory-summary compatibility test
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or changing compact-summary read semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** dialog-state tests + compact-summary compatibility test + architecture suite + packet + arch guard + session check all green
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
  - active block metadata must match the actual compact-summary bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No compact-summary read-path changes in frozen files.

## Risks/Blockers
- accidentally changing the joined summary text format would silently affect `memory_summary` seeding in frozen `decision.py`.
- refusal flags still depend on existing legacy flag semantics, so the bridge must preserve current name/phone refusal behavior exactly.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader context/state writer ownership and remaining proof-path excision still remain outside the bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has helper-owned non-carryover writers after this cut.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new context/state carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next remaining non-carryover state writer after compact summary.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: compact-summary shaping still authored in `context_manager.py`; source-of-truth not synced; deterministic bridge coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and compact-summary read paths in `decision.py`
- `Open risks`: changing joined summary format and silently affecting memory-summary seeding
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_llm_policy_core_receives_memory_hints_and_writes_meta'`
