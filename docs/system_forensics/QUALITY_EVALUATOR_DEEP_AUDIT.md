# Quality And Evaluator Deep Audit

Status: `open_first_pass`
Purpose: re-derive the actual llm-quality governance stack, distinguish what is already strong from what remains structurally weak, and explain why audit strength still outpaced implementation discipline.

## What this document covers
This is the fresh primary deep audit for quality and evaluator architecture.
It answers:
- how the current quality pipeline actually works,
- which governance improvements are real,
- where evaluator drift and workflow centralization still remain,
- and why the repo could still produce bad implementations after truthful audits.

## Current quality pipeline map
### Step 1. Scenario and contract preparation
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/app/services/scenario_contract_compiler.py`
Meaning:
- scenario generation and expectation normalization are no longer ad hoc shell glue only.
- there is a shared proof-path contract layer for booking/info/interrupt/handoff scenarios.

### Step 2. Guarded run entrypoint
`scripts/llm_quality_guarded.sh`
- enforces run mode, output dir, lane (`dev` vs `acceptance`), fingerprint rules, owner-file deltas, and previous-run audit gates
- standardizes the main entrypoint for expensive quality runs
Meaning:
- run discipline is materially stronger than before.
- expensive quality runs are now wrapped in a proper governance shell.

### Step 3. Chain controller enforces acceptance progression
`scripts/quality_chain_controller.sh`
- enforces `lock -> replay -> canary -> full`
- validates `PG0..PG6`
- manages chain tokens and chain state

`docs/runbooks/EXECUTION_CYCLE.md`
- defines the lane model `L0 -> L1 -> L2 -> L3`
- states that `L3` is a release gate, not a debug loop
Meaning:
- the acceptance lane is now a staged workflow, not just a convention.

### Step 4. Engine and artifact production
`ops/diagnose.py`
- `llm-quality` run mode writes `summary.json`, `brief.md`, `run_manifest.json`, and related artifacts
- maintains `/tmp/booking_quality/_index`
- encodes scenario-contract preflight and invalid-run handling
Meaning:
- run lifecycle, indexing, and summary writing now have one explicit tool owner.

### Step 5. Mandatory post-run human semantic audit layer
`ops/diagnose.py llm-quality-audit`
- generates:
  - `manual_audit_workspace.md`
  - `manual_audit_workspace.json`
  - `family_registry.json`
  - `judge_conflicts.jsonl`
- writes `human_semantic_valid` and product-quality status back into the run metadata
Meaning:
- the repo now separates contract-green from human-semantic green in a machine-readable way.
- this is one of the strongest governance improvements in the consultant-core lane.

### Step 6. Cross-run mechanism comparison
`ops/diagnose.py llm-quality-trends`
- aggregates family registry and manual-audit evidence across runs
Meaning:
- the workflow now has a mechanism/backlog drift view, not only a run-by-run summary view.

### Step 7. Test-gated workflow contracts
Key test files:
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
Meaning:
- many of the workflow rules are now executable, not just described in prose.

### Step 8. Operator runbook and canon integration
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `TECH.md`
Meaning:
- the workflow is backed by written operator discipline, not only helper scripts.

## What is already materially stronger
### Strength 1. Invalid and incomplete runs are now first-class states
The stack distinguishes:
- invalid preflight
- incomplete manual audit
- oracle conflict or forensic SLA violations
- semantic contract status versus human semantic status
Meaning:
- bad runs are less likely to be silently reused as evidence.

### Strength 2. Human semantic audit is no longer optional prose
The workflow now emits dedicated workspace and family artifacts.
That is a real structural improvement over summary-only review.

### Strength 3. Scenario-contract discipline is stronger
`llm_quality_contracts.py` and scenario-contract gate tests now check:
- coverage tokens
- weak expectation ratios
- reply/action/info coverage
- pending-question consistency for booking flows
Meaning:
- the quality stack now protects more of the mechanism-level contract than before.

### Strength 4. Run indexing and manifesting are real
`run_manifest.json` and `/tmp/booking_quality/_index` make replay comparability and audit completeness more explicit.

### Strength 5. Acceptance progression is now explicit
The guarded entrypoint plus the chain controller plus `EXECUTION_CYCLE.md` create a real lane model instead of one undifferentiated script surface.

## Where the quality/evaluator architecture is still weak
### Weakness 1. `ops/diagnose.py` is now a governance monolith
At roughly 29k lines, it centralizes:
- run orchestration
- status decisions
- audit artifact generation
- trend aggregation
- artifact indexing
- summary writing
- multiple unrelated tools
Meaning:
- the workflow is stronger, but the implementation is concentrated enough to become its own patch surface.

### Weakness 2. Proof-only boundaries are not perfectly enforced inside the test stack
`test_booking_quality_response_guard.py` explicitly forbids AST/exec loading of `ops/diagnose.py` and `scripts/booking_dialog_scenarios.py`.
At the same time, `test_booking_quality_status_gate.py` and `test_booking_quality_scenario_contract_gate.py` still use AST extraction against `ops/diagnose.py`.
Meaning:
- the governance intent is ahead of the implementation discipline here too.
- evaluator refactors remain brittle because some tests still depend on source extraction instead of a narrow shared API.

### Weakness 3. Evaluator semantics still live partly in heuristic helper code
`llm_quality_contracts.py` is valuable, but it still contains a large amount of scenario normalization and booking-specific expectation shaping.
Meaning:
- some evaluator policy still lives as Python heuristics rather than a narrow declarative contract.
- this is exactly where taxonomy drift or subtle test-fitting can reappear.

### Weakness 4. Scenario-governance state remains operationally local
The quality stack depends on `/tmp/booking_quality/_index` and related local registry state.
That is useful for one operator workflow, but it is still a portability and clean-environment risk if the state has to be reconstructed.

### Weakness 5. Product debt, oracle debt, and workflow debt are now distinguishable, but not fully separated in code ownership
The docs and artifacts distinguish them better.
The runtime and evaluator implementation still share some large helper/tool surfaces, and operator interpretation is still required.

### Weakness 6. A second verification lane exists with its own inference logic
`truffles-api/app/services/console_consultant_verification.py`
- extracts `decision_meta`
- infers gap/outcome/source refs
- computes verification findings
Meaning:
- console verification is useful,
- but it is another interpretation layer that can drift from the main llm-quality lane if governance does not stay aligned.

### Weakness 7. The process problem was real: audit quality improved faster than implementation governance
This is the key lesson from the recent mistake.
The repo gained stronger audit artifacts before it gained a fully governing outside-research and implementation contract.
That is why packet scaffold work was able to get ahead of fresh primary research.

## Main verdicts
### Verdict 1. The quality stack is much stronger than it was in earlier consultant-core phases
This is real progress, not cosmetic progress.
The current run/audit/trend artifact contract is materially better.

### Verdict 2. The main remaining weakness is architectural concentration and heuristic policy in the governance toolchain
The stack is not failing because it lacks rules.
It is weak because too many rules, transforms, and summaries still live inside a few large modules.

### Verdict 3. The repo now has stronger audit discipline than implementation discipline
This is the core explanatory verdict for the user's complaint.
Good audits existed.
They still did not reliably prevent poor runtime repairs because the implementation side was not forced to start from one governing research layer.

### Verdict 4. The next governance move after the full primary deep audit is not more packet polish
It is:
- contradiction-resolution,
- one final readiness review,
- then implementation gates that force runtime work to cite the relevant deep audit and missing executable contract.

## Main blockers surfaced by this audit
- `ops/diagnose.py` centralizes too much workflow authority
- proof-only policy and test implementation are still inconsistent around AST extraction
- `llm_quality_contracts.py` still encodes a lot of evaluator semantics in code
- scenario-governance state remains operationally local
- console verification is a second interpretation lane that can drift
- earlier governance improvements were not yet packaged into one authoritative research-first execution order

## Evidence anchors
- `scripts/llm_quality_guarded.sh`
- `scripts/quality_chain_controller.sh`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/app/services/scenario_contract_compiler.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `TECH.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
