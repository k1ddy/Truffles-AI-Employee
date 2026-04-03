# TP-2026-04-01-consultant-core-block-h1b-file-replay-scenario-contract-materialization-a922

## Название / цель
Переоткрыть oracle-only family после full `Block H` acceptance и закрыть её на shared full-replay path: `--scenarios-file` должен материализовать booking scenario contract через тот же canonical sanitizer/repair pipeline, что и generated scenarios. Блок меняет только replay harness/oracle path, затем доказывает это одним focused replay на stale dialogs `2` и `9`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h1-oracle-scenario-contract-alignment-a922.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/summary.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/responses.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/manual_audit.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/manual_audit.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401c/family_registry.json`
- `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`

## Invariant
- no runtime/product behavior changes in this block
- no evaluator weakening or oracle gate relaxation
- no hand-edited stale replay expectations as the mechanism
- no docs/state/packet sync until code + focused tests + minimal replay proof are complete

## One web search (mandatory before implementation)
- Query: `site:developers.openai.com/api/docs/guides/evaluation-best-practices golden set production traces eval drift`
- Date/time: `2026-04-01T19:36:00+05:00`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- Source quality:
  - official vendor documentation / primary source
- Found reusable ideas:
  - evaluation sets should stay aligned with production-like traces and contracts instead of drifting into stale golden labels
  - shared evaluation logic should normalize contract inputs before scoring, rather than forcing runtime wording or behavior to match stale expectations
- Decision:
  - `reuse -> integrate`
  - reuse the existing booking scenario sanitizer/repair pipeline from `truffles-api/app/services/llm_quality_contracts.py` and integrate it into the file-replay load path in `ops/diagnose.py`
- Rejected options:
  - editing `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json` directly
  - broadening the evaluator to ignore stale `expected_*` mismatches
  - patching runtime/business behavior to satisfy stale replay rows

## Root cause (mandatory)
- Symptom:
  - full `Block H` replay `/tmp/booking_quality/a922-block-h-replay-20260401c` is `infra_valid=true`, `semantic_valid=false`, `human_semantic_valid=true`
  - first surfaced red turns are:
    - `LLM-QUAL-a922-block-h-replay-20260401c-002-05-d8cb0e`
    - `LLM-QUAL-a922-block-h-replay-20260401c-009-01-d1b065`
    - `LLM-QUAL-a922-block-h-replay-20260401c-009-02-9fbb3a`
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json` dialogs `2` and `9`
  2. confirm stale expectations remain in the raw file:
     - dialog `2` turn `5` keeps `expected_reply=false`
     - dialog `9` turn `1` keeps `expected_reply=false`
     - dialog `9` turn `2` keeps stale `action=booking_prompt`, `reply_type=time`
  3. inspect `/tmp/booking_quality/a922-block-h-replay-20260401c/responses.jsonl`
  4. confirm current runtime/meta behavior is correct:
     - dialog `2` turn `5` -> `action=booking_confirm`, `tool_action=calendar.book_slot`, `tool_decision=ok`
     - dialog `9` turns `1-2` -> `tool_action=calendar.get_booking`, `tool_decision=not_found`, `expected_reply_type=name`
  5. inspect `ops/diagnose.py::_llm_quality_load_dialogs_from_file(...)` and confirm it returns raw dialogs without running the shared booking sanitizer/repair pipeline
- Evidence:
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/summary.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/responses.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/manual_audit.md`
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/manual_audit.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401c/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
  - `ops/diagnose.py`
  - `truffles-api/app/services/llm_quality_contracts.py`
- Exact path map:
  - input: `--scenarios-file /tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
  - owner output: `_llm_quality_load_dialogs_from_file(...)` reads the raw dialogs from file
  - validator/interrupt arbitration: strict evaluator compares runtime `decision_meta/trace` against loaded `expect`
  - continuity preservation: runtime path is already correct; evidence is in `responses.jsonl` and `manual_audit.json`
  - fallback/degrade: none on the product path; stale expectations survive because replay load bypasses shared sanitizer/repair
  - final response: runtime gives correct booking confirmation and booking-manage missing-name prompts
  - trace/meta evidence: replay copies stale rows into output `scenarios.json`, then evaluator/judge fail against those stale rows
  - layer classification: `oracle_or_evaluator_error`
- Five Whys:
  1. Why is full acceptance still `semantic_valid=false`? Because evaluator compares current runtime output against stale scenario expectations.
  2. Why are those expectations stale during replay? Because file-based replay loading returns raw dialog rows.
  3. Why do raw rows stay stale? Because the shared booking scenario sanitizer/repair pipeline is only used on generated scenarios, not on `--scenarios-file`.
  4. Why did focused H1 proof pass earlier? Because it used a manually repaired focused scenarios file rather than the raw locked bundle path.
  5. Why is this one shared mechanism? Because every surfaced turn comes from the same bypass: full replay file loading does not materialize canonical scenario contract before evaluation.
- Broken invariant:
  - file-based replay must consume the same canonical scenario-contract materialization path as generated scenarios before evaluation begins
- Shared mechanism:
  - `ops/diagnose.py` bypasses `merge_booking_scenario_expectations(...)`, `sanitize_booking_scenario_llm_turns(...)`, and `repair_booking_scenario_post_coverage_dialogs(...)` when loading `--scenarios-file`
- Why the surfaced family belongs to that mechanism:
  - the failing rows are already repairable by the shared booking scenario contract pipeline; they only remain stale because the file replay loader never applies that pipeline
- Open-world envelope expected to improve:
  - any future acceptance replay that reuses older locked booking/check-booking bundles through `--scenarios-file` will materialize current canonical contract before evaluation
- Root cause statement:
  - full replay consumes raw locked scenario rows because `_llm_quality_load_dialogs_from_file(...)` bypasses the shared booking scenario materialization pipeline, so stale booking completion and booking-manage expectations survive into evaluation even when runtime behavior is correct
- Fix mechanism:
  - add one canonical scenario-contract materialization helper on the file replay path in `ops/diagnose.py`
  - reuse the existing booking contract helpers from `truffles-api/app/services/llm_quality_contracts.py`
  - cover the loader with deterministic tests and prove it with one focused replay on the stale family dialogs only

## Reuse-first decision
- Reuse:
  - `merge_booking_scenario_expectations(...)`
  - `sanitize_booking_scenario_llm_turns(...)`
  - `repair_booking_scenario_post_coverage_dialogs(...)`
  - `BookingScenarioPostCoverageRepairCallbacks`
- Integrate:
  - integrate that shared contract materialization into `ops/diagnose.py` for `--scenarios-file`
- Build:
  - no new evaluator/oracle engine, no runtime/business logic branch

## Scope
- `ops/diagnose.py`
- focused deterministic replay-loader tests
- one focused raw scenarios file containing locked dialogs `2` and `9`
- one focused replay proving the stale oracle family disappears on the shared file path

## Out of scope
- runtime/core behavior changes
- full `Block H` rerun before this block is proven
- baseline promotion or lock refresh
- broad docs/state/packet churn before block closeout

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h1b-file-replay-scenario-contract-materialization-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_diagnose_run_command.py`
- `/tmp/booking_quality/a922-block-h1b-scenarios-20260401a.json`
- `/tmp/booking_quality/a922-block-h1b-replay-20260401a/*`
- active docs/state/packet only after honest closeout

## Plan
1. Add a lazy loader in `ops/diagnose.py` for shared booking scenario contract helpers.
2. Materialize file-based dialogs through the shared sanitizer/repair path before replay execution/evaluation.
3. Add deterministic regression tests proving raw stale file rows compile into corrected expectations on load.
4. Build a focused raw scenarios file from locked dialogs `2` and `9` without manual repair.
5. Run one focused replay on that raw file and audit it.
6. Only if that replay is green, sync docs/state/packet and rerun full `Block H`.

## DoD
- `--scenarios-file` load path no longer returns raw booking/check-booking stale expectations
- deterministic tests prove dialog `2` turn `5` and dialog `9` turns `1-2` are materialized into current canonical expectations on load
- focused replay on the raw dialogs `2` and `9` is `infra_valid=true`, `semantic_valid=true`, `human_semantic_valid=true`
- next admissible move becomes full `Block H` rerun

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_diagnose_run_command.py -k "scenarios_file or materialize"`
- `python3 -m py_compile ops/diagnose.py`
- `git diff --check`
- focused replay runtime parity:
  - `curl -fsS http://127.0.0.1:18189/admin/version`
  - `curl -fsS http://127.0.0.1:18189/admin/health`
- focused replay:
  - `scripts/llm_quality_guarded.sh --mode replay --run-id a922-block-h1b-replay-20260401a -- --base-url http://127.0.0.1:18189 --client-slug demo_salon --count 2 --scenarios-file /tmp/booking_quality/a922-block-h1b-scenarios-20260401a.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260330-r35f/summary.json --mode llm --min-turns 2 --max-turns 5 --media-mode text --scenario-coverage booking,interrupt,handoff --batch-size 2 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-block-h1b-replay-20260401a --history-max 20 --max-failures 2 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --quality-lane dev --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-block-h1b-replay-20260401a --analyst a922 --status done --strict-artifacts --human-semantic-valid true --human-semantic-summary '<summary>'`

## Evidence
- updated TP with exact RCA + one web search
- deterministic loader test output
- focused raw scenario subset at `/tmp/booking_quality/a922-block-h1b-scenarios-20260401a.json`
- focused replay bundle at `/tmp/booking_quality/a922-block-h1b-replay-20260401a`
- docs/state/packet sync only after the block is proven

## Rollback
- revert only the file-replay scenario materialization change and matching tests
- delete `/tmp/booking_quality/a922-block-h1b-scenarios-20260401a.json` and `/tmp/booking_quality/a922-block-h1b-replay-20260401a`
- do not edit the locked `r35f` artifacts during rollback

## No-go
- no runtime/business behavior patching
- no new phrase/regex semantic control in runtime
- no direct mutation of the locked canonical bundle as the fix
- no full `Block H` green claim from this focused replay alone

## Риски / блокеры
- over-broad materialization could rewrite legitimate non-booking file scenarios if applied carelessly
- focused replay may surface a different stale oracle row once this family is gone; if so, stop and classify that next family rather than widening this block mid-run
- full `Block H` still remains open after this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- full `Block H` acceptance remains open until rerun on current `HEAD`
- locked bundle governance still lives in `/tmp` acceptance artifacts rather than repo-owned fixtures

### Why not in this block
- this block is only about the shared file-replay materialization mechanism that reintroduced stale oracle rows

### Risk if deferred
- full acceptance remains blocked by stale replay contracts despite product-green runtime behavior

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`

### Expiry / trigger to stop deferral
- before the next full `Block H` replay or any new acceptance claim based on `--scenarios-file`

## Next-block contract (mandatory)
### Next block objective
- rerun full `Block H` on the locked `r35f` surface after the file replay path materializes canonical scenario contract

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_diagnose_run_command.py -k "scenarios_file or materialize" && python3 -m py_compile ops/diagnose.py && git diff --check`

### Blocked-by conditions
- loader tests stay red
- focused replay is still `semantic_valid=false` on dialogs `2` or `9`
- runtime fingerprint on `127.0.0.1:18189` does not match current `HEAD`

### Owner role for closure
- Brain / Top Architect

## Branch / worktree / merge policy
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: current active worktree `HEAD`
- Merge policy: no whole-system closure claim until fresh full `Block H` replay is green
- Cleanup: stop the local runtime after focused replay and keep artifacts under `/tmp/booking_quality/a922-block-h1b-replay-20260401a`
