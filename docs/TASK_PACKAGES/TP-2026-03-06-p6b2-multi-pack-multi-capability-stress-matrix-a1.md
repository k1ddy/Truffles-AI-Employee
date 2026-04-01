# TP-2026-03-06-p6b2-multi-pack-multi-capability-stress-matrix-a1

- Название/цель: выполнить следующий обязательный блок `P6B`: гонять один и тот же LLM stress synthesizer contract через несколько pack/capability envelope, чтобы бизнес-agnostic утверждение проверялось не на одном `demo_salon`.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `TECH.md`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`

## One web search (mandatory before implementation)

- Query: `site:docs.pytest.org pytest parametrize ids multiple cases`
- Time (UTC): `2026-03-06T14:14:00Z`
- Sources:
  - `pytest docs: parametrize`
- Ready solutions found:
  - stable matrix checks should be expressed as explicit parametrized cases, not ad-hoc shell duplication
  - matrix identity must stay deterministic per row to keep artifacts comparable
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse existing `llm-quality-matrix`
  - integrate branch/capability row alignment and deterministic scenario-context contract on top
- Rejected options:
  - separate custom matrix runner outside `llm-quality-matrix`
  - manual per-pack shell scripts without row-level contract validation

## Root cause (mandatory)

- Symptom:
  - `P6B.1` now makes one LLM generator context-aware, but there is still no proof that the same contract stays valid across multiple pack/capability envelopes.
- Minimal reproduction:
  1. run current generator only for `demo_salon`
  2. observe that no deterministic/contract check proves context alignment for `clinic_pack`, `dental_pack`, or capability-restricted branches
- Evidence:
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6b1-llm-open-world-stress-synthesizer-context-a1.md`
  - `ops/diagnose.py`
  - `scripts/booking_dialog_scenarios.py`
- Five Whys:
  1. Why is business-agnostic still unproven: only one context contract is wired.
  2. Why is that insufficient: one pack can hide domain coupling.
  3. Why can deterministic mutations not replace this: they mutate surface, not capability/business envelope.
  4. Why is matrix execution required: the same generator must obey different service/tool/fact envelopes without code changes.
  5. Why is this the next block: it is the first direct proof that the new `scenario_context` contract generalizes.
- Root cause statement:
  - context-aware generation exists, but no multi-pack/multi-capability matrix yet proves that it behaves consistently outside one canary pack.
- Fix mechanism:
  - add deterministic matrix checks and dev-forensic harness coverage across several packs/capability payloads using the same generator path.

## Invariant

1. The same generator path must be reused across packs.
2. Pack/capability differences must stay in data/context, not in new core branching.
3. Matrix execution must validate scenario-context alignment, not just produce more text.

## Scope

- `ops/diagnose.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/tests/test_diagnose_run_command.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Out of scope

- expensive acceptance `lock/replay/full`
- failure clustering/oracle redesign (`P6C.1`)
- final P6 closure decision (`P6C.2`)

## Plan (1..N)

1. Define the multi-pack test matrix (`demo_salon`, `clinic_pack`, `dental_pack`, plus capability variants).
2. Add deterministic checks that generated scenarios stay aligned with each matrix envelope.
3. Add one `dev/forensic` command path for matrix execution without declaring acceptance evidence.
4. Sync docs and next-stage evidence contract.

## DoD

1. At least three distinct packs are covered by the same generator contract.
2. Deterministic checks fail if scenario output violates pack/capability envelope.
3. No new business-specific core branching is introduced.

## Checks

- `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "matrix or multi_pack"`
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k "multi_pack or capability_matrix"`
- `git diff --check`

## Execution status

- `done`

## Evidence

1. `ops/diagnose.py`
   - `llm-quality-matrix` now supports `--branch-slugs`
   - child rows validate generated `scenario_context` and in-context service hits
2. Tests:
   - `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "matrix or scenario_context_contract or branch_slug"`
   - `pytest -q truffles-api/tests/test_diagnose_run_command.py`
   - `ruff check ops/diagnose.py truffles-api/tests/test_diagnose_run_command.py`
   - `python3 -m py_compile ops/diagnose.py`
   - `git diff --check`

## Rollback

1. revert matrix harness additions
2. rerun deterministic generator/diagnose tests

## No-go

- no per-pack prompt templates as a substitute for context
- no acceptance claims based on one matrix row

## Risks/Blockers

1. some packs may have sparse truth data and require explicit degraded expectations
2. capability payloads may vary by branch and need deterministic normalization

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - failure clustering and semantic family reporting remain deferred
- Why not in this block:
  - first we need cross-pack evidence generation, then we can cluster failures meaningfully
- Risk if deferred:
  - failures will still be analyzed one-by-one instead of by reusable root-cause family
- Linked follow-up Task Package(s):
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6c1-failure-clustering-root-cause-families-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6c2-p6-acceptance-closure-a1.md`
- Expiry/trigger to stop deferral:
  - before any claim that open-world stress is pack-neutral in practice

## Next-block contract (mandatory)

- Next block objective:
  - group future matrix failures by invariant/root-cause family instead of isolated bad turns
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "failure_cluster or root_cause_family"`
- Blocked-by conditions:
  - multi-pack matrix not yet implemented
  - no comparable cross-pack evidence exists
- Owner role for closure:
  - `Top Architect + Brain`
