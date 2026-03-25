# TP-2026-03-15-consultant-core-proof-path-ast-blackbox-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-PATH-AST-BLACKBOX-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MISSING-TENANT-CONTEXT-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-missing-tenant-context-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-PATH-NEXT-EXCISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Начать реальный Block E без изменения runtime-поведения: убрать AST-derived semantic authority из `truffles-api/tests/test_booking_quality_response_guard.py` и усилить `scripts/proof_path_guard.py`, чтобы tests больше не использовали `ops/diagnose.py` как truth source через AST/exec path.

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
- `scripts/proof_path_guard.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `ops/diagnose.py`
- `scripts/booking_dialog_scenarios.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/proof_path_guard.py`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/tests/test_booking_quality_response_guard.py`
  - `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,220p' scripts/proof_path_guard.py`
  - `sed -n '1,260p' truffles-api/tests/test_booking_quality_response_guard.py`
  - `sed -n '1,220p' truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `FACT findings`:
  - `truffles-api/tests/test_booking_quality_response_guard.py` currently reads `ops/diagnose.py`, parses it with `ast.parse`, compiles selected nodes, and asserts semantic results from `_llm_quality_evaluate_turn` and related helpers.
  - that makes a test file semantic-authoritative over proof-only evaluator logic, which violates the current canon.
  - `scripts/proof_path_guard.py` currently blocks direct imports from proof-only modules but does not block AST/exec loading from proof-only file paths.
  - `ops/diagnose.py` and `scripts/booking_dialog_scenarios.py` remain proof-only files and should stay observational, not act as imported truth sources for tests.
- `Detected drift (docs vs code)`: proof-path governance claims black-box/read-only proof, but one large test file still executes evaluator logic directly from `ops/diagnose.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python ast parse module doc`
- **Date/time (local):** `2026-03-15 18:12 Asia/Almaty`
- **Why this query is precise:** this block strengthens the guard against AST-derived proof authority, so the only technical question is the exact AST-exec pattern we are prohibiting.
- **Sources opened (from this query):**
  - `Python ast — Abstract Syntax Trees` — `https://docs.python.org/3/library/ast.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ast.parse(...)` plus `compile/exec` is the exact dynamic-code path being used by the current test anti-pattern, so a proof guard can target this shape directly without touching runtime behavior.
- **Decision:** `reuse + integrate` — strengthen the existing `proof_path_guard.py` and convert the affected test file to black-box governance checks instead of semantic evaluator assertions.
- **Rejected options:**
  - changing `ops/diagnose.py` runtime behavior in this block
  - widening the block into scenario-script semantic rewrite removal
  - keeping AST execution but renaming it as “helper loading”
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** proof/eval is still partially semantic-authoritative because tests execute evaluator logic from `ops/diagnose.py` and assert semantic outcomes as truth.
- **Minimal reproduction:**
  1. Inspect `truffles-api/tests/test_booking_quality_response_guard.py` and find `_load_evaluate_turn()` plus other AST loader helpers.
  2. Inspect `scripts/proof_path_guard.py` and confirm it blocks direct imports from proof-only modules but not AST/exec loading from proof-only file paths.
  3. Compare with canon in `docs/ACTIVE_CANON.md`: proof/eval should be read-only observers.
- **Evidence to capture:**
  - `test_booking_quality_response_guard.py` no longer AST-loads proof-only code
  - `proof_path_guard.py` now fails when tests add AST/exec loading of `ops/diagnose.py` or `scripts/booking_dialog_scenarios.py`
  - runtime behavior remains unchanged because only tests/guard/config move
- **Five Whys (or equivalent):**
  1. Why is proof-path still authoritative? Because tests execute evaluator code directly and treat it as oracle logic.
  2. Why is that wrong? Because proof-only files must observe runtime artifacts, not author semantics.
  3. Why hasn’t the existing guard stopped it? Because it only covers direct imports, not AST/exec loading.
  4. Why is this the safest first excision? Because it changes tests/governance only, not runtime behavior.
  5. Why does this reduce future drift? Because one large path for reintroducing evaluator-as-truth becomes impossible after merge.
- **Root cause statement:** proof-path governance is incomplete because tests can still AST/exec-load proof-only modules and assert semantic evaluator outcomes, bypassing the current import-only guard.
- **Fix mechanism:**
  - replace `truffles-api/tests/test_booking_quality_response_guard.py` with black-box governance tests that do not execute evaluator logic from proof-only files
  - extend `scripts/proof_path_guard.py` to detect AST/exec loading patterns against proof-only file paths in tests
  - codify the new detection tokens in `docs/LEGACY_SUNSET.yaml`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `scripts/proof_path_guard.py`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- **External reuse:**
  - official Python `ast` docs for identifying the exact anti-pattern shape
- **Why not reinvent the wheel:** the repo already has a proof-path guard and architecture tests; this block should extend that mechanism, not invent a second governance path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded proof governance excision with no runtime behavior change and explicit black-box acceptance focus.

## Invariant
- No runtime behavior changes in `ops/diagnose.py`, `scripts/booking_dialog_scenarios.py`, or consultant runtime.
- No changes in frozen legacy semantic router files.
- Proof-only modules remain proof-only; tests must not execute them as semantic truth.

## Scope
- Extend `scripts/proof_path_guard.py` to block AST/exec loading of proof-only file paths from tests.
- Update `docs/LEGACY_SUNSET.yaml` proof guard config for the new detection rule.
- Convert `truffles-api/tests/test_booking_quality_response_guard.py` from AST/evaluator-oracle tests into black-box governance tests.
- Add/adjust deterministic architecture coverage.
- Sync source-of-truth/state/session docs.

## Out of scope
- editing `ops/diagnose.py` evaluator logic
- removing semantic rewrite logic from `scripts/booking_dialog_scenarios.py`
- changing llm-quality product/runtime behavior
- broader continuity migration

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-path-ast-blackbox-slice-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/proof_path_guard.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this proof-path excision TP with RCA and one web search.
2. Extend `proof_path_guard.py` to detect AST/exec loading of proof-only file paths from tests.
3. Replace `test_booking_quality_response_guard.py` with black-box governance tests that do not execute evaluator logic.
4. Add/adjust architecture tests for the new guard rule.
5. Re-run consultant-core/proof checks and sync docs/session state.

## DoD
- `truffles-api/tests/test_booking_quality_response_guard.py` no longer parses or executes proof-only files.
- `scripts/proof_path_guard.py` fails when new test code adds AST/exec loading of `ops/diagnose.py` or `scripts/booking_dialog_scenarios.py`.
- No runtime/product behavior changes are introduced.
- Deterministic tests and guards are green.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- smaller black-box `test_booking_quality_response_guard.py`
- updated `proof_path_guard.py` + architecture tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires runtime changes in `ops/diagnose.py` or changes in consultant runtime behavior, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** proof-path governance excision only
- **Go/no-go signals:** targeted proof tests + architecture tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s test/guard/doc changes only
- **Post-release monitoring window:** next proof-path excision should target scenario-script semantic rewrite authority separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/LEGACY_SUNSET.yaml`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual proof-path excision block being executed.

## Rollback
- Revert this TP’s guard/test/doc changes; keep all already-landed governance/runtime-slice blocks intact.

## No-go
- No runtime edits in `ops/diagnose.py` or `scripts/booking_dialog_scenarios.py`.
- No new AST/exec proof loaders in tests.
- No changes in frozen legacy semantic router files.

## Risks/Blockers
- other tests still parse proof-only files in narrower ways; this block intentionally targets the largest semantic-authoritative offender first.
- black-box replacement coverage must stay meaningful enough to guard against regressions in proof governance.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: scenario-script semantic rewrite logic and other narrower proof-path AST tests remain for later excision blocks.
- `Why not in this block`: this is the safest first proof excision with no runtime behavior change.
- `Risk if deferred`: evaluator-as-truth continues to leak back into tests and evidence.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-proof-path-next-excision-a922`
- `Expiry/trigger to stop deferral`: before any new proof-only semantic helper growth is added.

## Next-block contract (mandatory)
- `Next block objective`: remove the next proof-only semantic authority after AST/exec loading is blocked, likely scenario-contract rewrite authority.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `Blocked-by conditions`: AST/exec proof loading still possible; black-box response-guard test not in place; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: consultant runtime files and frozen legacy router files
- `Open risks`: overbroad proof guard that blocks legitimate CLI black-box tests; weakening proof coverage too far
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
