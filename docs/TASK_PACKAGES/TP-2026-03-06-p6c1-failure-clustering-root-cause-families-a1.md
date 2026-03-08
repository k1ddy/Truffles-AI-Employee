# TP-2026-03-06-p6c1-failure-clustering-root-cause-families-a1

- Название/цель: перевести `P6` forensic layer с по-turn bad cases на root-cause family clustering по invariant/reason/trace signatures.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`

## One web search (mandatory before implementation)

- Query: `site:docs.python.org collections Counter defaultdict python docs`
- Time (UTC): `2026-03-06T14:39:00Z`
- Sources:
  - `Python docs: collections`
- Ready solutions found:
  - stable clustered summaries should be built from deterministic counting/grouping structures, not ad-hoc narrative inspection
  - repeated events should collapse into comparable buckets before higher-level decisions
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse existing `failure_counts`, `taxonomy`, `top_failure_turns`
  - integrate deterministic `failure_families` on top of current run/matrix summaries
- Rejected options:
  - LLM-only forensic clustering without deterministic signatures
  - manual analyst-only clustering after each run

## Root cause (mandatory)

- Symptom:
  - quality loop still surfaces many failures as isolated turns instead of a smaller set of reusable root-cause families.
- Root cause statement:
  - there is no explicit clustering layer over invariant failures, semantic traces, and tool/state outcomes.
- Fix mechanism:
  - add deterministic failure-family clustering and reporting artifacts before the final acceptance decision.

## Invariant

1. Clustering must rely on trace/meta/outcome signals, not only surface text.
2. Failure families must be stable enough to drive root-cause work, not just reporting cosmetics.

## Scope

- `ops/diagnose.py`
- `scripts/quality_artifact_report.py`
- related deterministic tests/docs

## Out of scope

- acceptance closure itself
- new runtime behavior changes

## Plan (1..N)

1. Define family keys from invariant reasons + trace/meta signatures.
2. Add clustered reporting artifact.
3. Add deterministic tests for family stability.

## DoD

1. repeated failures collapse into root-cause families
2. top failures in quality evidence are reported by family, not only by turn

## Checks

- `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "failure_cluster or root_cause_family"`
- `git diff --check`

## Execution status

- `done`

## Evidence

1. `ops/diagnose.py`
   - added deterministic `failure_families` clustering for run summaries
   - added `failure_families.json`
   - aggregated family totals in `llm-quality-matrix`
2. `AGENTS.md`
   - added durable gates for open-world proof layering and failure-family-based acceptance reasoning
3. Tests:
   - `pytest -q truffles-api/tests/test_diagnose_run_command.py`
   - `ruff check ops/diagnose.py truffles-api/tests/test_diagnose_run_command.py`
   - `python3 -m py_compile ops/diagnose.py`
   - `git diff --check`

## Rollback

1. revert clustering code/docs

## No-go

- no LLM-only opaque clustering without deterministic evidence keys

## Risks/Blockers

1. weak trace normalization can create noisy families

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - final P6 acceptance decision remains deferred
- Why not in this block:
  - closure needs matrix evidence plus clustering output
- Risk if deferred:
  - program may still overreact to individual failures
- Linked follow-up Task Package(s):
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6c2-p6-acceptance-closure-a1.md`
- Expiry/trigger to stop deferral:
  - before marking `P6` done

## Next-block contract (mandatory)

- Next block objective:
  - perform final P6 acceptance closure on top of deterministic expansion + LLM stress matrix + failure clustering
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "open_world or invariant_gate"`
- Blocked-by conditions:
  - matrix evidence incomplete
  - clustering not implemented
- Owner role for closure:
  - `Top Architect + Brain`
