# TP-2026-03-15-consultant-core-proof-helper-extraction-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-HELPER-EXTRACTION-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-INTENT-QUEUE-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-intent-queue-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-PATH-EXCISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded proof-path excision slice без изменения runtime поведения: вынести scenario-contract / expectation-sanitizer helper logic из proof-only `ops/diagnose.py` в shared helper module и перестать использовать AST/spec loading `ops/diagnose.py` в targeted proof tests.

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
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_expectation_sanitizer.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/app/services/scenario_contract_compiler.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_expectation_sanitizer.py`
  - `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
  - `truffles-api/tests/test_booking_quality_response_guard.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "ops/diagnose.py|ast.parse\(|spec_from_file_location\(|exec\(compile\(" truffles-api/tests/test_booking_quality_expectation_sanitizer.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py`
  - `rg -n "def _llm_quality_extract_expectations|def _llm_quality_parse_coverage_tokens|def _llm_quality_build_scenario_contract_status" ops/diagnose.py`
- `FACT findings`:
  - `truffles-api/tests/test_booking_quality_expectation_sanitizer.py` still AST-loads `ops/diagnose.py` to test expectation sanitation logic.
  - `truffles-api/tests/test_booking_quality_scenario_contract_gate.py` still AST/spec-loads `ops/diagnose.py` to test scenario-contract and expectation extraction helpers.
  - this keeps proof-only `ops/diagnose.py` acting as direct test authority instead of a black-box observer or thin wrapper.
  - a natural shared home already exists in `truffles-api/app/services/` because `truffles-api/app/services/scenario_contract_compiler.py` already holds runtime-independent expectation compiler helpers.
- `Detected drift (docs vs code)`: proof/eval is supposed to be read-only observer infrastructure, but targeted proof tests still import or AST-load proof-only helpers directly from `ops/diagnose.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python importlib import_module documentation`
- **Date/time (local):** `2026-03-15 20:51 Asia/Almaty`
- **Why this query is precise:** this slice needs lazy shared-helper loading from `ops/diagnose.py` without keeping tests coupled to proof-only script internals.
- **Sources opened (from this query):**
  - `importlib — The implementation of import` — `https://docs.python.org/3/library/importlib.html#importlib.import_module`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `importlib.import_module(...)` is the standard-library way to lazily import a shared helper module at runtime instead of loading script source via AST/spec tricks.
- **Decision:** `reuse + integrate` — extract shared helpers to a normal Python module and use lazy `import_module(...)` from `ops/diagnose.py` wrappers rather than keeping tests tied to proof-only script source.
- **Rejected options:**
  - leaving AST/spec loading in tests
  - touching frozen legacy runtime files
  - broad proof-lane rewrite across all diagnose helpers in one block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** targeted proof tests still AST/spec-load `ops/diagnose.py` directly.
- **Minimal reproduction:**
  1. Open `truffles-api/tests/test_booking_quality_expectation_sanitizer.py`.
  2. Open `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`.
  3. Observe direct `read_text + ast.parse + exec(compile(...))` and `spec_from_file_location(...)` against `ops/diagnose.py`.
- **Evidence to capture:**
  - targeted proof tests import a shared helper module instead of reading `ops/diagnose.py` source.
  - `ops/diagnose.py` becomes a thin delegator for the extracted helper functions.
  - existing expectation-sanitizer and scenario-contract behavior stays green.
- **Five Whys (or equivalent):**
  1. Why is proof/eval still too authoritative? Because tests still depend on proof-only script internals directly.
  2. Why is that wrong? Because proof-only files should not be the direct truth source for tests.
  3. Why did it happen? Because helper logic lived only inside `ops/diagnose.py`, so tests used AST/spec loading as the cheapest access path.
  4. Why is extraction safe? Because the targeted helper logic is runtime-independent and already conceptually separate from CLI/orchestration behavior.
  5. Why does this reduce drift? Because another test-facing semantic helper stops living only inside a proof-only script.
- **Root cause statement:** proof-path authority is still too high because targeted test suites directly load helper logic from `ops/diagnose.py` instead of consuming a shared non-proof helper module.
- **Fix mechanism:**
  - extract bounded expectation/scenario-contract helpers into a shared module under `truffles-api/app/services/`
  - make `ops/diagnose.py` delegate to that module lazily
  - update targeted proof tests to import the shared helper module directly
  - add regression coverage so these targeted tests do not reintroduce direct proof-only loading

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/scenario_contract_compiler.py`
  - existing expectation and scenario-contract logic in `ops/diagnose.py`
  - existing `proof_path_guard` and response-guard tests
- **External reuse:**
  - official Python `importlib.import_module(...)` documentation
- **Why not reinvent the wheel:** the repo already has the scenario-contract compiler seam and Python already has lazy import primitives; this block should only move test-facing helpers out of proof-only script ownership.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `16`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded helper extraction with direct regression tests and no runtime-router edits.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to runtime decision semantics.
- No change to diagnose CLI outputs for the touched helper behaviors.

## Scope
- Extract shared expectation/scenario-contract helpers from `ops/diagnose.py` into a normal module under `truffles-api/app/services/`.
- Rewire `ops/diagnose.py` to delegate to that shared module.
- Stop direct `ops/diagnose.py` AST/spec loading in the targeted proof tests.
- Add regression coverage and sync source-of-truth/state/session docs.

## Out of scope
- full `ops/diagnose.py` decomposition
- scenario-generator rewrite in `scripts/booking_dialog_scenarios.py`
- frozen runtime file edits
- multi-pack acceptance

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-helper-extraction-slice-a922.md`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_booking_quality_expectation_sanitizer.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
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
1. Publish this proof-helper TP with RCA and one web search.
2. Extract targeted expectation/scenario-contract helpers into `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `ops/diagnose.py` to delegate to that shared helper module without changing runtime-router code.
4. Update targeted proof tests to stop direct AST/spec loading of `ops/diagnose.py`.
5. Add regression coverage, run proof/runtime/architecture checks, and sync docs.

## DoD
- targeted proof tests no longer AST/spec-load `ops/diagnose.py`
- shared helper module owns the extracted expectation/scenario-contract logic
- `ops/diagnose.py` becomes a thin delegator for the touched helper functions
- deterministic proof/runtime/architecture/session checks are green

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_expectation_sanitizer.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- extracted shared helper module for expectation/scenario-contract logic
- updated `ops/diagnose.py` delegating to shared helper module
- targeted proof tests without direct `ops/diagnose.py` AST/spec loading
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or broad diagnose decomposition, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** proof-path helper extraction only
- **Go/no-go signals:** targeted proof tests + response guard + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's helper extraction/test/doc changes only
- **Post-release monitoring window:** next proof block should either continue helper extraction for another proof test family or switch to richer semantic cutover if proof ROI drops

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `Drift closeout rule`:
  - active block metadata must match the actual proof-helper extraction slice being executed.

## Rollback
- Revert this TP's helper extraction, test, and doc changes; keep already-landed governance/runtime/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No changes to runtime policy semantics.

## Risks/Blockers
- extracting too many diagnose helpers in one slice will turn this into a generic refactor.
- wrapper imports in `ops/diagnose.py` must stay deterministic in both CLI runtime and pytest runtime.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader proof-only helper families and scenario rewrite authority in `scripts/booking_dialog_scenarios.py` still remain.
- `Why not in this block`: that would exceed a safe bounded proof excision slice.
- `Risk if deferred`: other proof tests can still load proof-only helpers directly.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-proof-path-excision-followup-a922`
- `Expiry/trigger to stop deferral`: before accepting any new proof-lane helper family that still lives only in proof-only scripts.

## Next-block contract (mandatory)
- `Next block objective`: continue proof-path excision on the next helper family or switch back to richer semantic cutover if proof-helper ROI drops.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_response_guard.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: targeted proof tests still import proof-only script internals; source-of-truth not synced; shared helper module absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and diagnose CLI semantics outside this helper family
- `Open risks`: widening extraction past the expectation/scenario-contract helper family or reintroducing direct proof-only loading in tests
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
