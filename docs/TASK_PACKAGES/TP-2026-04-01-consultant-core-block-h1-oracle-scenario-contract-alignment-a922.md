# TP-2026-04-01-consultant-core-block-h1-oracle-scenario-contract-alignment-a922

## Название / цель
Закрыть первый post-`Block H` oracle-only blocker в active worktree: stale scenario contract для booking completion и booking-manage follow-up, из-за которого current-head replay остаётся `semantic_valid=false` при `human_semantic_valid=true`. Блок меняет только scenario/oracle governance path, затем доказывает его одним focused replay на затронутой семье.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/summary.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/responses.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/manual_audit.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/manual_audit.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401b/family_registry.json`
- `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Invariant
- no runtime/product code changes in this block
- no oracle weakening by broad must-include or text-only matching
- no mutation of business meaning; only scenario contract alignment to the already-proven current runtime/meta contract
- no whole-system closure claim until full `Block H` replay is rerun after this block

## One web search (mandatory before implementation)
- Query: `site:developers.openai.com/api/docs/guides/evaluation-best-practices use-case-specific evals production traces intermediate decisions`
- Date/time: `2026-04-01T18:08:00+05:00`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- Source quality:
  - official vendor documentation / primary source
- Found reusable ideas:
  - evals must stay use-case-specific rather than broadening into generic pass conditions
  - production-like traces/intermediate decisions should be part of the evaluation contract when text-only expectations drift
- Decision:
  - `reuse -> integrate`
  - reuse the existing scenario sanitizer/repair pipeline in `truffles-api/app/services/llm_quality_contracts.py` and integrate one bounded contract correction for reply-required turns
- Rejected options:
  - weakening the evaluator to ignore `expected_reply_mismatch`
  - patching runtime text to satisfy stale scenarios
  - editing only `/tmp` lock artifacts without fixing the shared scenario-contract mechanism

## Root cause (mandatory)
- Symptom:
  - fresh `Block H` replay `/tmp/booking_quality/a922-block-h-replay-20260401b` is `infra_valid=true`, `semantic_valid=false`, `human_semantic_valid=true`
  - first remaining red turns are:
    - `LLM-QUAL-a922-block-h-replay-20260401b-002-05-4e8b1b`
    - `LLM-QUAL-a922-block-h-replay-20260401b-009-01-be4c68`
    - `LLM-QUAL-a922-block-h-replay-20260401b-009-02-323577`
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json` for dialog `2` turn `5` and dialog `9` turns `1-2`
  2. confirm stale scenario expectations:
     - dialog `2` turn `5` keeps `expected_reply=false`
     - dialog `9` turn `1` keeps `expected_reply=false`
     - dialog `9` turn `2` keeps stale `action=booking_prompt`, `reply_type=time`, `meta_any.expected_reply_type=["time"]`
  3. inspect `/tmp/booking_quality/a922-block-h-replay-20260401b/responses.jsonl`
  4. confirm current runtime/meta behavior is product-correct:
     - dialog `2` turn `5` -> `action=booking_confirm`, `tool_action=calendar.book_slot`, `tool_decision=ok`
     - dialog `9` turns `1-2` -> `tool_action=calendar.get_booking`, `tool_decision=not_found`, preserved `expected_reply_type=name`
  5. run the current scenario sanitizer/repair locally on those dialogs and confirm it still leaves dialog `2` turn `5` and dialog `9` turn `1` as non-reply-required, while only partially relaxing dialog `9` turn `2`
- Evidence:
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/summary.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/responses.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/manual_audit.md`
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/manual_audit.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401b/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- Exact path map:
  - input: locked scenario turn in `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
  - owner output: scenario-contract compiler in `truffles-api/app/services/llm_quality_contracts.py` via `sanitize_booking_scenario_llm_turns(...)` and `repair_booking_scenario_post_coverage_dialogs(...)`
  - validator/interrupt arbitration: replay strict evaluator compares runtime `decision_meta/trace` against compiled `expect`
  - continuity preservation: runtime already preserves canonical booking and booking-manage continuity in `/tmp/booking_quality/a922-block-h-replay-20260401b/responses.jsonl`
  - fallback/degrade: none on the surfaced family; the red comes from stale scenario expectations, not runtime degrade
  - final response: runtime replies are correct; evaluator stays red because `expect.expected_reply` / `expect.action` / `expect.meta_any.expected_reply_type` lag current contract
  - trace/meta evidence: `calendar.book_slot ok` on dialog `2` turn `5`, `calendar.get_booking not_found` + `expected_reply_type=name` on dialog `9` turns `1-2`
  - layer classification: `oracle_or_evaluator_error`
- Five Whys:
  1. Why is `Block H` still red? Because strict evaluator compares against stale scenario expectations.
  2. Why are the expectations stale? Because the scenario-contract compiler does not mark certain reply-required turns as reply-required after current contract evolution.
  3. Why do those turns drift specifically? Because the compiler still trusts raw LLM scenario expectations for booking-management entry turns and active-name answer turns instead of canonicalizing them through current contract state.
  4. Why is runtime already green? Because runtime/meta contract was fixed by the prior booking-manage and booking-confirm continuity blocks.
  5. Why is this one shared mechanism? Because all surfaced turns are the same contract gap: reply-required turns are left under-specified by the scenario compiler, so the evaluator treats correct runtime replies as mismatches.
- Broken invariant:
  - locked acceptance scenarios must require a reply whenever the current turn consumes or opens a canonical reply-required booking/check-booking contract on the already-proven runtime path
- Shared mechanism:
  - scenario-contract compiler in `llm_quality_contracts.py` lacks canonical reply-required shaping for `check_booking` entry turns and `active_reply_type=name` answer turns
- Why the surfaced family belongs to that mechanism:
  - dialog `2` turn `5` is an active-name answer turn
  - dialog `9` turn `1` is a `check_booking` entry turn
  - dialog `9` turn `2` is the same booking-manage family and already routes through the adjacent confirm relaxation logic
- Open-world envelope expected to improve:
  - any focused booking/check-booking replay where stale scenario rows under-specify reply-required turns after current runtime/meta contract evolution
- Root cause statement:
  - the scenario-contract compiler still leaves booking-manage entry turns and active-name answer turns under-specified (`expected_reply=false` or stale pending-question shape), so fresh replay remains oracle-red even though runtime/meta and human semantic audit are green
- Fix mechanism:
  - add one bounded scenario-contract correction in `truffles-api/app/services/llm_quality_contracts.py` that canonicalizes reply-required expectations for:
    - `check_booking` entry turns
    - `active_reply_type=name` answer turns (`name` / `phone`)
  - cover both sanitizer and post-coverage repair paths with deterministic tests
  - prove the corrected contract with one focused replay on dialogs `2` and `9`

## Reuse-first decision
- Reuse:
  - existing scenario sanitizer and post-coverage repair functions in `truffles-api/app/services/llm_quality_contracts.py`
  - existing generator-facing wrapper in `scripts/booking_dialog_scenarios.py`
  - existing deterministic test harness in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- Integrate:
  - add bounded reply-required contract shaping to the shared compiler instead of patching a single scenario file by hand
- Build:
  - no new evaluator, no new scenario engine, no runtime code

## Scope
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- one focused scenario artifact derived from the locked `r35f` dialogs `2` and `9`
- one focused replay proving the oracle family is gone on those dialogs

## Out of scope
- runtime/core behavior changes
- full `Block H` rerun
- baseline promotion / lock-chain promotion
- docs/state/packet sync before the focused oracle block is fully proven

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h1-oracle-scenario-contract-alignment-a922.md`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `/tmp/booking_quality/a922-block-h1-scenarios-20260401a.json`
- `/tmp/booking_quality/a922-block-h1-replay-20260401a/*`
- active docs/state/packet only after honest closeout

## Plan
1. Freeze fresh replay RCA in this TP and keep the layer classification oracle-only.
2. Implement one bounded shared scenario-contract fix in `llm_quality_contracts.py`.
3. Add targeted deterministic regressions in `truffles-api/tests/test_booking_dialog_scenarios_script.py`.
4. Build a focused scenarios file from locked dialogs `2` and `9` after shared sanitization/repair.
5. Start a fresh local runtime from the active worktree and run one focused replay on that oracle family only.
6. If the focused replay is green, sync docs/state/packet and queue full `Block H` rerun as the next admissible move.

## DoD
- `check_booking` entry turns no longer compile with `expected_reply=false`
- `active_reply_type=name` answer turns no longer compile with silent/no-reply expectations
- deterministic tests cover both sanitizer and post-coverage repair paths
- focused replay on dialogs `2` and `9` is `infra_valid=true`, `semantic_valid=true`, `human_semantic_valid=true`
- first remaining next move is full `Block H` rerun, not another oracle patch inside this family

## Work mode
- `implementation`

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k "check_booking or active_name"`
- `python3 -m py_compile truffles-api/app/services/llm_quality_contracts.py`
- `git diff --check`
- focused replay runtime parity:
  - `curl -fsS http://127.0.0.1:18189/admin/version`
  - `curl -fsS http://127.0.0.1:18189/admin/health`
- focused replay:
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18189 --client-slug demo_salon --count 2 --scenarios-file /tmp/booking_quality/a922-block-h1-scenarios-20260401a.json --mode llm --min-turns 2 --max-turns 5 --media-mode text --scenario-coverage booking,interrupt --batch-size 2 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-block-h1-replay-20260401a --run-id a922-block-h1-replay-20260401a --history-max 20 --max-failures 2 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate warn --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-block-h1-replay-20260401a --analyst a922 --status done --strict-artifacts --human-semantic-valid true --human-semantic-summary '<summary>'`

## Evidence
- updated TP with RCA + one web search
- deterministic test output
- focused scenario file under `/tmp/booking_quality/a922-block-h1-scenarios-20260401a.json`
- focused replay artifact bundle under `/tmp/booking_quality/a922-block-h1-replay-20260401a`
- docs/state sync only if the focused oracle block closes honestly

## Rollback
- revert only the shared scenario-contract shaping changes and matching tests
- delete `/tmp/booking_quality/a922-block-h1-scenarios-20260401a.json` and `/tmp/booking_quality/a922-block-h1-replay-20260401a`
- do not touch runtime code or the old `r35f` artifact bundle on rollback

## No-go
- no runtime/core patching
- no broad default `expected_reply=true` for every turn
- no manual hand-edit of just one stale turn without shared compiler fix
- no full `Block H` claim from the focused oracle replay

## Риски / блокеры
- over-broad reply-required shaping could alter legitimate no-reply scenario rows outside booking/check-booking semantics
- focused replay may surface a different stale oracle row once this family is removed; if so, stop and classify the next family instead of widening this block
- the active worktree still needs a final full `Block H` rerun after this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `Block H` whole-system acceptance remains open after this focused oracle block
- locked `r35f` baseline/governance promotion chain is still external artifact state, not repo-owned data

### Why not in this block
- this block only removes the first surfaced oracle family and proves it on the minimal focused contour

### Risk if deferred
- final acceptance stays blocked by stale scenario red despite product-green current-head behavior

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`

### Expiry / trigger to stop deferral
- before any new full `Block H` replay or any new runtime block that cites `a922-block-h-replay-20260401b`

## Next-block contract (mandatory)
### Next block objective
- rerun full `Block H` on the locked `r35f` surface after this oracle family is removed, then close or reopen from fresh first-fail evidence

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k "check_booking or active_name" && python3 -m py_compile truffles-api/app/services/llm_quality_contracts.py && git diff --check`

### Blocked-by conditions
- focused deterministic scenario tests are red
- focused replay remains `semantic_valid=false` on the same oracle family
- runtime fingerprint on `127.0.0.1:18189` does not match current `HEAD`

### Owner role for closure
- Brain / Top Architect

## Branch / worktree / merge policy
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: current active worktree `HEAD`
- Merge policy: no closure claim beyond the focused oracle block until full `Block H` rerun is complete
- Cleanup: stop the local runtime and keep focused replay artifacts under `/tmp/booking_quality/a922-block-h1-replay-20260401a`
