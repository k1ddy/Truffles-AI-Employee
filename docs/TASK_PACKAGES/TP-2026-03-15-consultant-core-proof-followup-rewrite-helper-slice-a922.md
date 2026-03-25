# TP-2026-03-15-consultant-core-proof-followup-rewrite-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-FOLLOWUP-REWRITE-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOOKING-SCENARIO-EXPECTATION-HELPER-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-booking-scenario-expectation-helper-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-PATH-SANITIZE-REPAIR-EXCISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий code-first proof-path excision slice без изменения runtime поведения: вынести orphan/check-booking/reschedule followup rewrite helper family из proof-only `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы post-hoc followup rewrite semantics больше не жили только в scenario generator script.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-booking-scenario-expectation-helper-slice-a922.md`
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
  - `scripts/booking_dialog_scenarios.py`
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - `truffles-api/tests/test_booking_quality_response_guard.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "def _has_orphan_pending_question_tags|def _rewrite_orphan_pending_question_tags|def _rewrite_reschedule_followup_tags|def _rewrite_check_booking_followup_tags|def _time_collect_expect_override" scripts/booking_dialog_scenarios.py`
  - `rg -n "rewrites_orphan|rewrites_reschedule|rewrites_check_booking|service_choice" truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - `scripts/booking_dialog_scenarios.py` still owns a pure helper family that rewrites followup tags/expectations for orphan pending-question turns, reschedule followups, check-booking followups, and time-collect fallback expectations.
  - the shared helper module `truffles-api/app/services/llm_quality_contracts.py` already owns the booking-scenario expectation merge layer, so the remaining rewrite helper family is the next bounded proof-only authority.
  - sanitize/repair tests prove this family is behaviorally important but still local to the proof-only script.
- `Detected drift (docs vs code)`: proof/eval should be observer/generator infrastructure, but a post-hoc followup rewrite helper family still lives only inside `scripts/booking_dialog_scenarios.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy documentation`
- **Date/time (local):** `2026-03-15 21:21 Asia/Almaty`
- **Why this query is precise:** this slice moves nested expectation/tag rewrite helpers into a shared module and must preserve detached dict/list payloads instead of aliasing caller-owned structures across sanitize/repair passes.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html#copy.deepcopy`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard-library mechanism for preserving detached nested copies when helper extraction returns structured expectations.
- **Decision:** `reuse + integrate` — reuse `copy.deepcopy(...)` in the shared helper module anywhere extracted expectation payloads need detached nested structures.
- **Rejected options:**
  - leaving the followup rewrite helper family inside `scripts/booking_dialog_scenarios.py`
  - broad rewrite of `_sanitize_llm_turns(...)` in one block
  - touching frozen legacy runtime files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** post-hoc followup rewrite semantics for orphan pending-question turns, reschedule followups, check-booking followups, and time-collect fallback still live only inside `scripts/booking_dialog_scenarios.py`.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py`.
  2. Find `_has_orphan_pending_question_tags(...)`, `_rewrite_orphan_pending_question_tags(...)`, `_orphan_pending_question_expect_override(...)`, `_rewrite_reschedule_followup_tags(...)`, `_reschedule_followup_expect_override(...)`, `_rewrite_check_booking_followup_tags(...)`, `_check_booking_followup_expect_override(...)`, and `_time_collect_expect_override(...)`.
  3. Open `truffles-api/tests/test_booking_dialog_scenarios_script.py` and observe sanitize/repair tests depending on these behaviors through the proof-only script.
- **Evidence to capture:**
  - extracted followup rewrite helper family lives in `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py` delegates the touched helper family to the shared module
  - targeted sanitize/repair tests stay green
  - proof/runtime/architecture/session checks stay green
- **Five Whys (or equivalent):**
  1. Why is proof/eval still too authoritative? Because another pure semantic helper family still exists only in the proof-only scenario generator.
  2. Why is that wrong? Because proof-only files should not be the only owner of reusable rewrite/expectation logic.
  3. Why did it happen? Because sanitize/repair heuristics accreted locally inside the generator script as scenario debt.
  4. Why is extraction safe? Because this helper family is pure tag/expectation shaping and does not require runtime-router edits.
  5. Why does this reduce drift? Because one more proof-only semantic family moves into a shared non-proof helper module.
- **Root cause statement:** proof-path authority remains too high because followup rewrite semantics are still implemented only in `scripts/booking_dialog_scenarios.py` instead of a shared helper module.
- **Fix mechanism:**
  - extract the followup rewrite helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - delegate the touched helpers from `scripts/booking_dialog_scenarios.py` to the shared module through neutral aliases
  - add regression checks proving shared ownership and preserved behavior

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/llm_quality_contracts.py`
  - existing booking-scenario expectation helper family already extracted there
  - existing sanitize/repair tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - existing proof response guard tests
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation
- **Why not reinvent the wheel:** the repo already has a shared llm-quality helper module and Python already ships safe nested-copy primitives; this block only moves the next bounded helper family out of the proof-only script.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded shared-helper extraction with direct sanitize/repair regression tests and no runtime-router edits.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to runtime decision semantics.
- No change to scenario wording beyond existing helper behavior.

## Scope
- Extract the followup rewrite helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Rewire the touched helpers in `scripts/booking_dialog_scenarios.py` to delegate to the shared helper module.
- Add regression coverage for shared ownership and preserved sanitize/repair behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- `_sanitize_llm_turns(...)` decomposition
- `_repair_post_coverage_orphan_pending_question_turns(...)` removal
- richer runtime semantic cutover
- frozen runtime file edits
- multi-pack acceptance

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-followup-rewrite-helper-slice-a922.md`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/services/llm_quality_contracts.py`
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
2. Extract the bounded followup rewrite helper family into `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to delegate the touched helper family through neutral aliases.
4. Add direct shared-helper regression coverage and rerun sanitize/repair proof tests.
5. Run required proof/runtime/architecture/session checks and sync docs.

## DoD
- followup rewrite helper family no longer lives only inside `scripts/booking_dialog_scenarios.py`
- `scripts/booking_dialog_scenarios.py` delegates the touched helper family to the shared module
- sanitize/repair behavior for the touched scenarios stays green
- deterministic proof/runtime/architecture/session checks are green

## Checks
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'orphan_pending_question or rewrites_reschedule or rewrites_check_booking or partial_date_fill'`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- extracted followup rewrite helper family in `truffles-api/app/services/llm_quality_contracts.py`
- updated `scripts/booking_dialog_scenarios.py` delegating the touched helper family
- targeted sanitize/repair tests and proof guard tests green
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires `_sanitize_llm_turns(...)` decomposition or runtime-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** proof-path helper extraction only
- **Go/no-go signals:** targeted sanitize/repair tests + proof guard + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's helper extraction/test/doc changes only
- **Post-release monitoring window:** next block should either continue extracting a bounded proof-only helper family or switch to richer semantic cutover if proof ROI drops again

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual proof followup-rewrite helper slice being executed.

## Rollback
- Revert this TP's helper extraction, test, and doc changes; keep already-landed governance/runtime/continuity/proof-helper blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No changes to runtime policy semantics.

## Risks/Blockers
- extracting too much of `scripts/booking_dialog_scenarios.py` in one slice will turn this into a generic proof-generator refactor.
- proof guard will fail if new added lines in the proof-only script include forbidden semantic tokens; imports/wrappers must stay neutral.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `_sanitize_llm_turns(...)`, `_repair_post_coverage_orphan_pending_question_turns(...)`, and other scenario rewrite authority still remain in `scripts/booking_dialog_scenarios.py`.
- `Why not in this block`: removing those call-sites entirely would exceed a safe bounded helper extraction slice.
- `Risk if deferred`: the proof generator still owns broader post-hoc normalization orchestration beyond the extracted followup helper family.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-proof-path-sanitize-repair-followup-a922`
- `Expiry/trigger to stop deferral`: before accepting any proof-lane claim that depends on scenario post-processing as semantic truth.

## Next-block contract (mandatory)
- `Next block objective`: continue proof-path excision on sanitize/repair orchestration or switch to richer semantic cutover if proof ROI drops.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'orphan_pending_question or rewrites_reschedule or rewrites_check_booking' && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: touched helper family still lives only in the proof-only script; source-of-truth not synced; shared helper extraction absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- The only intended code move in this block is the bounded followup rewrite helper family.
- Do not touch frozen runtime router files.
- Keep proof-only script imports/wrappers neutral enough to survive `scripts/proof_path_guard.py`.
