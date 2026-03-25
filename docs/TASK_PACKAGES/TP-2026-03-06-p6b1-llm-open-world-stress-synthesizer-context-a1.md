# TP-2026-03-06-p6b1-llm-open-world-stress-synthesizer-context-a1

- Название/цель: начать missing `P6B LLM open-world stress synthesis` с первого атомарного блока: убрать salon-hardcode из LLM scenario generation и сделать synthesizer pack-aware, branch-aware, capability-aware через явный scenario context contract.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `TECH.md`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`

## One web search (mandatory before implementation)

- Query: `site:platform.openai.com structured outputs json schema OpenAI`
- Time (UTC): `2026-03-06T13:26:29Z`
- Sources:
  - `OpenAI platform docs: Structured Outputs / JSON schema`
- Ready solutions found:
  - LLM generators should be driven by explicit structured contracts instead of loose prose-only prompts
  - schema/context separation improves reliability and reduces hidden prompt coupling
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse existing `booking_dialog_scenarios.py` LLM mode and `ops/diagnose.py llm-quality` executor
  - integrate an explicit `scenario_context` contract into that path instead of inventing a separate runner
- Rejected options:
  - keep salon-specific prompt text and hope deterministic mutations make it business-agnostic
  - create a second unrelated LLM scenario runner outside current `llm-quality` path

## Root cause (mandatory)

- Symptom:
  - the current expensive LLM scenario generation path still hardcodes `Beauty salon domain, Russian language` and does not receive tenant/branch/capability context, so it cannot serve as a true business-agnostic stress synthesizer.

- Minimal reproduction:
  1. inspect `_generate_llm_dialogs(...)` in `scripts/booking_dialog_scenarios.py`
  2. inspect `_llm_quality_generate_batch(...)` in `ops/diagnose.py`
  3. observe:
     - generator prompt hardcodes salon + Russian assumptions
     - `client_slug`/`branch_slug` are not passed into the generator subprocess
     - no scenario context file/contract is provided for tools/fact scopes/handoff policy

- Evidence:
  - `scripts/booking_dialog_scenarios.py`
    - prompt contains `Beauty salon domain, Russian language`
    - fallback/context extraction still depends on fixed salon service lists
  - `ops/diagnose.py`
    - already knows `client_slug`, `branch_slug`, pack files, and DB client meta, but does not pass that context into scenario synthesis
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
    - `P6` now explicitly requires LLM stress synthesis beyond deterministic expansion

- Five Whys:
  1. Why is P6 not truly closed: the LLM generator still imagines one default business.
  2. Why is that unsafe: generated scenarios may not match tools, services, or language surface of the actual tenant/branch.
  3. Why can deterministic mutations not fix it: they mutate surface form, but they do not invent the missing business/tool envelope.
  4. Why is `ops/diagnose.py` the right integration point: it already resolves client/branch DB context and controls the real `llm-quality` loop.
  5. Why is this the first atomic block: without a context contract, every later multi-pack/multi-capability stress run will be semantically suspect.

- Root cause statement:
  - the current LLM stress path lacks an explicit scenario context contract and therefore remains salon-coupled instead of business-agnostic.

- Fix mechanism:
  - add a scenario-context contract passed from `ops/diagnose.py` to `booking_dialog_scenarios.py`
  - derive context from local pack truth + client/branch capability envelope
  - remove salon-specific default prompt assumptions from the LLM generator and make prompt/fallback logic context-aware

## Invariant

1. LLM scenario synthesis must not assume one default business when tenant/branch context is available.
2. Context lives in data/manifest payloads, not in new core hardcode.
3. The existing `llm-quality` execution path remains the single runner; we are upgrading its input contract, not creating a parallel harness.

## Scope

- `scripts/booking_dialog_scenarios.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_diagnose_run_command.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-p6b1-llm-open-world-stress-synthesizer-context-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## Out of scope

- expensive acceptance `lock/replay/full`
- failure clustering (`P6C`)
- broader multi-pack matrix execution (`P6B.2`)

## Plan (1..N)

1. Define a `scenario_context` payload for business/branch/capability envelope.
2. Pass `client_slug`, `branch_slug`, and scenario context from `ops/diagnose.py` into `booking_dialog_scenarios.py`.
3. Make LLM prompt and fallback/context extraction consume that payload instead of salon-hardcoded assumptions.
4. Add deterministic tests for context loading/prompt content and subprocess command wiring.
5. Sync docs/evidence.

## DoD

1. LLM generator accepts explicit tenant/branch scenario context.
2. Prompt no longer hardcodes `Beauty salon domain, Russian language` as universal default when context exists.
3. `ops/diagnose.py llm-quality` passes scenario context into generation.
4. Deterministic tests are green.
5. `git diff --check` is clean.

## Checks

- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k "scenario_context or llm_prompt"`
- `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "scenario_context or client_slug"`
- `git diff --check`

## Execution status

- `done`

## Evidence

1. `scripts/booking_dialog_scenarios.py`
   - added `scenario_context` contract (`--client-slug`, `--branch-slug`, `--scenario-context-file`)
   - removed universal `Beauty salon domain, Russian language` prompt assumption
   - made context/fallback selection pack-aware
2. `ops/diagnose.py`
   - builds compact pack/branch/capability `scenario_context.json`
   - passes scenario context into `booking_dialog_scenarios.py`
   - records `llm_quality_scenario_context_preflight`
3. Tests:
   - `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py`
   - `pytest -q truffles-api/tests/test_diagnose_run_command.py`
   - `ruff check scripts/booking_dialog_scenarios.py ops/diagnose.py truffles-api/tests/test_booking_dialog_scenarios_script.py truffles-api/tests/test_diagnose_run_command.py`
   - `git diff --check`

## Rollback

1. revert scenario-context contract additions
2. rerun generator/diagnose deterministic tests

## No-go

- no new salon-only hardcode as a substitute for context
- no parallel ad-hoc runner outside `llm-quality`
- no weakening of existing invariant gates

## Risks/Blockers

1. pack truth formats differ across client packs and require tolerant extraction
2. capability data may be absent for some clients and must degrade predictably without reviving salon defaults

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - multi-pack matrix execution and failure clustering remain deferred
- Why not in this block:
  - this block only fixes the missing context contract for one generator path
- Risk if deferred:
  - later stress runs would still be semantically suspect across packs/branches
- Linked follow-up Task Package(s):
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6b2-multi-pack-multi-capability-stress-matrix-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-06-p6c1-failure-clustering-root-cause-families-a1.md`
- Expiry/trigger to stop deferral:
  - before any claim that LLM stress generation is business-agnostic

## Next-block contract (mandatory)

- Next block objective:
  - execute the same LLM stress synthesizer contract across multiple packs/capability envelopes and validate that scenarios stay aligned to each envelope
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_diagnose_run_command.py -k "matrix or multi_pack"`
- Blocked-by conditions:
  - generator still ignores explicit scenario context
  - no test proves multi-pack context wiring
- Owner role for closure:
  - `Top Architect + Brain`
