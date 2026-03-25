# TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-POST-COVERAGE-REWRITE-EXCISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-SLOT-NORMALIZATION-HELPER-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-slot-normalization-helper-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Снять еще один proof-only authority seam: вынести post-coverage orphan-repair orchestration из `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, оставив script thin wrapper без новых runtime изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-slot-normalization-helper-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '3783,4125p' scripts/booking_dialog_scenarios.py`
  - `rg -n 'repair_post_coverage_orphan_pending_question_turns|orphan_pending_question' scripts/booking_dialog_scenarios.py truffles-api/tests/test_booking_dialog_scenarios_script.py truffles-api/app/services/llm_quality_contracts.py`
  - `sed -n '1,90p' truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - `_repair_post_coverage_orphan_pending_question_turns(...)` still lives only in `scripts/booking_dialog_scenarios.py` and remains the last large proof-only orchestration pass for retagging and expectation repair after coverage expansion.
  - the function already depends heavily on helper families previously extracted into `truffles-api/app/services/llm_quality_contracts.py`, but the orchestration itself still lives in the proof-only script.
  - deterministic coverage already exists in `truffles-api/tests/test_booking_dialog_scenarios_script.py` for orphan/check-booking/reschedule/partial-date/exact-time repair branches, so this block can stay code-first and local.
  - `_LazyModule` now forwards monkeypatch writes to the real loaded script module, so test-time callback injection stays reliable after extraction.
- `Detected drift (docs vs code)`: proof-only files are still not just observers/thin wrappers because post-coverage repair orchestration remains script-owned.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html Python dataclasses documentation default_factory frozen`
- **Date/time (local):** `2026-03-16 10:40 +05`
- **Why this query is precise:** this block needs a compact, explicit container for repair state and callback wiring while avoiding mutable-default pitfalls during extraction.
- **Sources opened (from this query):**
  - `Python Standard Library — dataclasses` — `https://docs.python.org/3.10/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `dataclasses` directly support frozen state carriers and `field(default_factory=...)` for mutable defaults; this matches the need for a bounded repair-state/callback bundle during extraction.
- **Decision:** `reuse + integrate` — use small dataclass carriers in shared code for post-coverage repair state/callback wiring instead of inventing ad-hoc mutable dict protocols.
- **Rejected options:**
  - keeping a giant script-local function and only extracting another helper fragment
  - passing unstructured nested dicts/tuples through the shared seam
  - widening the block into runtime or frozen-router work
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** proof-only booking-scenario generation still owns the post-coverage repair orchestration that rewrites tags/expectations after dialogs are generated.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` and inspect `_repair_post_coverage_orphan_pending_question_turns(...)`.
  2. Observe that the function performs semantic retagging and expectation repair after coverage expansion, not just formatting.
  3. Note that many of its helper families are already shared, but the orchestration itself still lives only in the proof script.
- **Evidence to capture:**
  - shared post-coverage repair orchestration exists in `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py` delegates to shared orchestration instead of owning the loop body
  - deterministic repair tests remain green
- **Five Whys (or equivalent):**
  1. Why does proof still author semantics? Because the post-coverage repair loop still lives only in the proof script.
  2. Why is that a problem? Because the script remains the sole owner of semantic retagging after scenario generation.
  3. Why not stop at helper extraction? Because the orchestration still chooses when and how those helpers rewrite turns.
  4. Why is shared extraction safe? Because the logic is deterministic, already covered by focused tests, and does not change runtime behavior.
  5. Why does this reduce drift? Because one more large proof-only decision loop stops living in the file that should become a thin wrapper.
- **Root cause statement:** post-coverage orphan-repair orchestration still lives only in `scripts/booking_dialog_scenarios.py`, so proof-only code remains the exclusive owner of a large semantic rewrite pass even after prior helper extractions.
- **Fix mechanism:**
  - move the post-coverage repair orchestration into `truffles-api/app/services/llm_quality_contracts.py`
  - keep script-specific wiring as a thin wrapper/callback assembly only
  - preserve current deterministic behavior through existing repair tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared `truffles-api/app/services/llm_quality_contracts.py` extraction pattern
  - existing repair helper families already moved there
  - existing deterministic repair tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** the repo already has the target shared module; this block extends it and reuses existing test coverage.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `18`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** one bounded proof-excision slice with deterministic tests and no runtime/frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No runtime behavior changes.
- No new proof-only semantic helper families added to `scripts/booking_dialog_scenarios.py`.
- Existing post-coverage repair outputs for covered cases stay intact.

## Scope
- Move post-coverage orphan-repair orchestration into `truffles-api/app/services/llm_quality_contracts.py`.
- Reduce `scripts/booking_dialog_scenarios.py` to a thin wrapper for that flow.
- Keep or add deterministic test coverage in `truffles-api/tests/test_booking_dialog_scenarios_script.py`.
- Sync required canon/session artifacts.

## Out of scope
- runtime semantic cutover
- continuity collapse
- neutral runtime work
- multi-pack acceptance
- frozen router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922.md`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and one web search.
2. Add shared post-coverage repair orchestration/state carriers in `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to delegate `_repair_post_coverage_orphan_pending_question_turns(...)` into shared code.
4. Revalidate deterministic repair tests and add focused coverage if the new shared seam needs it.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- shared post-coverage repair orchestration exists in `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` no longer owns the main loop body for post-coverage repair
- deterministic booking-scenario tests remain green
- proof-path architecture checks remain green

## Checks
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- shared post-coverage repair orchestration in `truffles-api/app/services/llm_quality_contracts.py`
- proof script delegating to shared orchestration
- deterministic repair coverage in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- synced source-of-truth/session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires runtime behavior changes or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic proof-path extraction only; no runtime code-path changes
- **Go/no-go signals:** booking-scenario tests + quality-response-guard + runtime-contract tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's shared-helper/script/test/doc changes only
- **Post-release monitoring window:** next block should either remove the remaining proof-only repair seam or return to richer runtime cutover, not add new proof-only orchestration

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the post-coverage rewrite excision actually implemented.

## Rollback
- Revert this TP's shared-orchestration, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate post-coverage orchestration logic left in both the script and shared module.

## Risks/Blockers
- shared orchestration may need many callback dependencies; if that starts widening beyond the bounded seam, split again.
- extraction may accidentally alter state progression (`active_reply_type`, `partial_date_anchor_active`, `multi_service_clarify_active`).
- if deterministic repair outputs drift, this block is not done.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: some proof-only repair/apply helpers will still remain script-owned after this slice; runtime semantic ownership, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice removes one large orchestration seam only and keeps the block bounded.
- `Risk if deferred`: proof-only script remains the sole owner of the largest remaining post-coverage semantic rewrite loop.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming proof path is black-box for booking scenarios or before adding any new post-coverage semantic repair branch in the script.

## Next-block contract (mandatory)
- `Next block objective`: either remove the next remaining proof-only repair seam or switch back to richer semantic cutover in `reasoning_core` if proof-path ROI drops.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: post-coverage repair outputs drift; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
