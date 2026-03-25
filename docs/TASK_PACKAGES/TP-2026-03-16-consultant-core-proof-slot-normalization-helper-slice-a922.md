# TP-2026-03-16-consultant-core-proof-slot-normalization-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-SLOT-NORMALIZATION-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-INGRESS-CONVERSATION-SNAPSHOT-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ingress-conversation-snapshot-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-POST-COVERAGE-REWRITE-EXCISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Вынести slot/time/partial-date normalization helper family из proof-only `scripts/booking_dialog_scenarios.py` в `truffles-api/app/services/llm_quality_contracts.py`, чтобы script перестал быть единственным semantic owner для этих repair/normalize правил.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ingress-conversation-snapshot-bridge-a922.md`
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
  - `sed -n '1650,2605p' scripts/booking_dialog_scenarios.py`
  - `sed -n '3940,4525p' scripts/booking_dialog_scenarios.py`
  - `sed -n '1,260p' truffles-api/app/services/llm_quality_contracts.py`
  - `sed -n '1700,2060p' truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - slot/time/partial-date normalization predicates and rewrites still live only in `scripts/booking_dialog_scenarios.py`.
  - the same helper family drives both `_sanitize_llm_turns(...)` and `_repair_post_coverage_orphan_pending_question_turns(...)`, so proof-only code still authors semantic normalization after coverage expansion.
  - existing shared module `truffles-api/app/services/llm_quality_contracts.py` already owns earlier booking-scenario expectation helpers and is the right reuse target for another bounded extraction.
  - tests already cover the affected family through sanitize/repair flows, so the block can stay deterministic and code-first.
- `Detected drift (docs vs code)`: `docs/SOURCE_OF_TRUTH.yaml` says proof-only files must be observers, but slot/time normalization authority still lives inside proof-only scenario script.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/re.html Python re module regular expression patterns documentation alternation`
- **Date/time (local):** `2026-03-16 10:05 +05`
- **Why this query is precise:** this block extracts a regex-heavy helper family and must keep the existing pattern strategy on supported stdlib `re` semantics instead of inventing a new parsing layer.
- **Sources opened (from this query):**
  - `Python Standard Library — re: Regular expression operations` — `https://docs.python.org/3/library/re.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `re` supports composing regex helpers from compiled raw-string patterns and module-level search operations; this matches the repo's current helper style and does not justify a parser rewrite.
- **Decision:** `reuse + integrate` — keep compiled regex helpers, move the semantic helper family into `llm_quality_contracts.py`, and let the proof script consume shared helpers instead of owning them.
- **Rejected options:**
  - rewriting the family into ad-hoc string parsing
  - keeping duplicate regex/predicate logic in both the script and shared module
  - widening the block into runtime semantic cutover or frozen-router edits
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** proof-only booking scenario generation still rewrites slot/time/partial-date semantics inside `scripts/booking_dialog_scenarios.py`.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` and locate the slot/time/partial-date predicate + normalization family around `_looks_like_explicit_time_fill(...)` and `_normalize_*slot*` helpers.
  2. Observe that `_sanitize_llm_turns(...)` and `_repair_post_coverage_orphan_pending_question_turns(...)` both depend on those proof-local helpers.
  3. Open `truffles-api/app/services/llm_quality_contracts.py` and note that earlier expectation/rewrite helpers were already extracted there, but this family still remains proof-only.
- **Evidence to capture:**
  - shared helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py` consumes shared helpers instead of owning function bodies for this family
  - sanitize/repair deterministic tests stay green
- **Five Whys (or equivalent):**
  1. Why does proof still author semantics? Because script-local normalize helpers still decide how slot/time/partial-date turns are retagged.
  2. Why is that a problem? Because proof-only logic remains an authority for semantic repair after runtime execution.
  3. Why not leave it as-is? Because the program explicitly requires proof-only files to become observers or thin orchestration layers.
  4. Why is shared extraction safe? Because the logic is deterministic, already well-covered by tests, and can move without changing runtime code paths.
  5. Why does this reduce drift? Because one more proof-only semantic family stops living in a file that is supposed to observe, not decide.
- **Root cause statement:** slot/time/partial-date normalization still lives only in the proof scenario script, so proof-only code remains the sole owner of a nontrivial semantic rewrite family.
- **Fix mechanism:**
  - extract the regex/predicate/normalize helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - switch the script to import and reuse those helpers
  - preserve existing sanitize/repair outputs with deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `truffles-api/app/services/llm_quality_contracts.py` helper extraction pattern
  - existing sanitize/repair tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - existing proof blackbox guardrails
- **External reuse:**
  - official Python `re` documentation
- **Why not reinvent the wheel:** the repo already has the shared contract-helper module; this block extends it instead of creating another helper surface.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `18`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is a code-first proof excision slice with deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No change to runtime behavior.
- No new proof-only semantic helpers added in `scripts/booking_dialog_scenarios.py`.
- Existing sanitize/repair outputs for covered cases stay intact.

## Scope
- Move the slot/time/partial-date normalization helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Update `scripts/booking_dialog_scenarios.py` to consume shared helpers.
- Add or adjust deterministic tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`.
- Sync required canon/session artifacts.

## Out of scope
- frozen router edits
- runtime semantic cutover
- continuity writer collapse
- multi-pack acceptance
- large proof-path rewrite beyond this helper family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-slot-normalization-helper-slice-a922.md`
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
2. Extract the regex/predicate/normalize helper family from `scripts/booking_dialog_scenarios.py` into `truffles-api/app/services/llm_quality_contracts.py`.
3. Switch sanitize/repair flows in the script to consume shared helpers or imported aliases instead of local function bodies.
4. Add deterministic tests covering both direct helper import behavior and existing sanitize/repair flows.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- slot/time/partial-date helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` no longer owns function bodies for that family
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
- shared helper family in `truffles-api/app/services/llm_quality_contracts.py`
- proof script consuming shared helpers
- deterministic sanitize/repair coverage in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- synced source-of-truth/session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or widens into runtime behavior changes, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic helper extraction only; no runtime code path changes
- **Go/no-go signals:** booking-scenario tests + quality-response-guard + runtime-contract tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's helper extraction and doc sync only
- **Post-release monitoring window:** next proof block should keep shrinking script-local semantic authority rather than add new helper families there

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the proof slot-normalization helper extraction actually implemented.

## Rollback
- Revert this TP's shared-helper, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate helper logic left in both script and shared module for the moved family.

## Risks/Blockers
- helper extraction may miss a predicate dependency and subtly change sanitize/repair outputs.
- shared module exports may accidentally grow wider than this bounded family.
- if the block starts requiring unrelated proof rewrite helpers, it exceeds scope and must split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: post-coverage orphan repair orchestration still remains in the proof script; runtime semantic ownership, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice only removes one coherent proof-local helper family and keeps the change bounded.
- `Risk if deferred`: proof-only script remains the sole owner of slot/time/partial-date normalization semantics.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922`
- `Expiry/trigger to stop deferral`: before claiming proof path is black-box for booking scenarios or before expanding scenario repair logic again.

## Next-block contract (mandatory)
- `Next block objective`: remove the next proof-only rewrite seam from `scripts/booking_dialog_scenarios.py`, preferably post-coverage orphan repair orchestration, without touching runtime or frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: helper extraction changes sanitize/repair outputs; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
