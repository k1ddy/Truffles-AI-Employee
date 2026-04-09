# TP-2026-04-01-consultant-core-block-h2-simulated-manager-take-callback-robustness-a922

## Название / цель
Закрыть первый surfaced blocker после full `Block H` acceptance rerun на shared manager-action simulation seam. Simulated `take` callback должен повторно использовать canonical infra-retry transport, чтобы acceptance replay не падал на transient callback timeout до перехода `pending -> manager_active`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/summary.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/responses.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/manual_audit.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/manual_audit.json`
- `/tmp/booking_quality/a922-block-h-replay-20260401d/family_registry.json`
- `ops/diagnose.py`
- `truffles-api/tests/test_diagnose_run_command.py`

## Invariant
- no runtime consultant/handoff business semantics change in this block
- no oracle weakening or manager-action failure suppression
- no timeout inflation as the primary fix
- no `STATE.md` / `docs/ACTIVE_*` / `docs/SOURCE_OF_TRUTH.yaml` / `docs/RECOVERY_EXECUTION_LOCK.yaml` / `docs/_generated/*` sync until code + focused tests + one focused replay proof are complete

## One web search (mandatory before implementation)
- Query: `Python urllib.request timeout retry official documentation`
- Date/time: `2026-04-01T19:00:07+05:00`
- Sources opened:
  - `https://docs.python.org/3.11/howto/urllib2.html`
- Source quality:
  - official Python documentation / primary source
- Found reusable ideas:
  - `urllib` timeout handling is caller-owned at the socket/request layer
  - retry policy should live in the caller transport wrapper instead of being faked by ad-hoc sleeps in higher-level business logic
- Decision:
  - `reuse -> integrate`
  - reuse existing `_send_webhook_payload_with_retry(...)` in `ops/diagnose.py` for simulated Telegram manager callbacks
- Rejected options:
  - broadening run timeout budgets
  - patching runtime handoff state transitions to satisfy acceptance harness timing
  - adding scenario-specific sleeps or special-casing only one handoff dialog

## Root cause (mandatory)
- Symptom:
  - full acceptance replay `/tmp/booking_quality/a922-block-h-replay-20260401d` finished `infra_valid=true`, `semantic_valid=false`, `human_semantic_valid=false`
  - the only surfaced family is `reason:manager_action_failed|type:manager_action|category:code|action:take|state:pending`
  - explicit handoff turn `LLM-QUAL-a922-block-h-replay-20260401d-003-01-1f945a` is user-facing green, but simulated manager action `take` timed out and left the conversation pending
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-block-h-replay-20260401d/responses.jsonl` for dialog `3`, turn `1`
  2. confirm `manager_actions[0] = {"action":"take","error":"timeout: timed out","state_after":"pending","reasons":["manager_action_failed"]}`
  3. confirm `manager_actions[1]` then resolves successfully from `pending` to `bot_active`
  4. inspect `ops/diagnose.py` and confirm simulated Telegram manager callbacks use `_send_webhook_payload(...)` directly, while the main webhook transport already owns `_send_webhook_payload_with_retry(...)`
- Evidence:
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/summary.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/responses.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/manual_audit.md`
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/manual_audit.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401d/family_registry.json`
  - `ops/diagnose.py`
- Exact path map:
  - input: user turn `Позовите менеджера, пожалуйста` plus simulated callback payload `take_<handover_id>`
  - owner output: consultant runtime issues canonical `HANDOFF`, conversation becomes `pending`, handover becomes `pending`
  - validator / boundary: `ops/diagnose.py::_simulate_manager_actions(...)` sends the Telegram callback to `/telegram-webhook`
  - continuity preservation: not applicable on the consultant semantic path; the handoff issuance itself is already correct
  - fallback / degrade: callback transport does not reuse the existing retry wrapper, so a transient timeout is recorded as `manager_action_failed`
  - final response: acceptance replay turns semantic red even though the user-facing handoff response is correct
  - trace/meta evidence: `summary.json.failure_families`, `responses.jsonl.manager_actions`, `manual_audit.json`
  - layer classification: `oracle_or_evaluator_error` on the acceptance operational seam
- Five Whys:
  1. Why did final acceptance stay red? Because the simulated manager `take` callback failed with a timeout.
  2. Why did that callback failure become the first blocker family? Because handoff issuance itself was green and all other turns passed.
  3. Why did the callback timeout surface as a hard family? Because manager simulation records transport timeout directly as `manager_action_failed`.
  4. Why is the manager callback seam more fragile than normal webhook turns? Because it bypasses the shared `_send_webhook_payload_with_retry(...)` transport wrapper.
  5. Why is that one shared mechanism? Because every simulated Telegram manager action in llm-quality currently uses the same direct callback transport path.
- Broken invariant:
  - acceptance manager-action simulation must use the same canonical infra-retry transport policy as the main webhook execution path before declaring callback failure
- Shared mechanism:
  - simulated Telegram manager callbacks in `ops/diagnose.py` call `_send_webhook_payload(...)` directly instead of reusing `_send_webhook_payload_with_retry(...)`
- Why the surfaced family belongs to that mechanism:
  - the only surfaced failure is a callback timeout on the manager simulation seam, and that seam is the only place where callback transport bypasses the shared retry wrapper
- Open-world envelope expected to improve:
  - acceptance/focused handoff replays will stop failing on transient simulated callback transport blips while still surfacing real HTTP/business failures
- Root cause statement:
  - full `Block H` acceptance failed on a shared harness transport seam because simulated Telegram manager callbacks bypass the canonical retry wrapper, so a transient `take` timeout is promoted to `manager_action_failed` even though the handoff runtime path itself is correct
- Fix mechanism:
  - extract one reusable simulated Telegram manager callback sender that routes through `_send_webhook_payload_with_retry(...)`
  - reuse existing `--retry-count` / `--retry-backoff` knobs rather than inventing new scenario sleeps
  - cover the helper with deterministic tests and prove it with one focused handoff replay

## Reuse-first decision
- Reuse:
  - `_send_webhook_payload_with_retry(...)`
  - existing `--retry-count` and `--retry-backoff` llm-quality knobs
- Integrate:
  - integrate the retry wrapper into simulated Telegram manager callback transport
- Build:
  - no new transport framework, no runtime handoff state patch, no scenario-specific branch

## Scope
- `ops/diagnose.py`
- deterministic tests for the simulated manager callback sender
- one focused handoff replay proving the callback family is removed

## Out of scope
- consultant runtime / Telegram webhook business semantics changes
- console manager action path changes
- full `Block H` docs/state closeout before the focused proof is green
- unrelated acceptance families

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h2-simulated-manager-take-callback-robustness-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_diagnose_run_command.py`
- `/tmp/booking_quality/a922-block-h2-handoff-replay-20260401a/*`
- active docs/state/packet only after honest closeout

## Plan
1. Add one reusable simulated Telegram manager callback helper in `ops/diagnose.py` that reuses `_send_webhook_payload_with_retry(...)`.
2. Route llm-quality simulated Telegram manager actions through that helper and preserve existing failure accounting for non-retryable errors.
3. Add deterministic tests proving the helper calls the retry wrapper with the correct callback payload and retry parameters.
4. Run the focused deterministic checks.
5. Run one focused handoff replay and audit it.
6. Only if that replay is green, rerun full `Block H`.

## DoD
- simulated Telegram manager callbacks no longer bypass `_send_webhook_payload_with_retry(...)`
- deterministic tests prove callback payload shape plus retry wrapper reuse
- one focused handoff replay is `infra_valid=true`, `semantic_valid=true`, `human_semantic_valid=true`
- next admissible move is rerunning full `Block H`

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_diagnose_run_command.py -k "manager_telegram_action or scenarios_file or materialize"`
- `python3 -m py_compile ops/diagnose.py`
- `git diff --check`
- focused replay runtime parity:
  - `curl -fsS http://127.0.0.1:18189/admin/version`
  - `curl -fsS http://127.0.0.1:18189/admin/health`
- focused replay:
  - `set -a && . /home/zhan/truffles-main/truffles-api/.env && set +a && scripts/llm_quality_guarded.sh --mode replay --run-id a922-block-h2-handoff-replay-20260401a --allow-pending-previous --allow-repeat-fingerprint -- --base-url http://127.0.0.1:18189 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-block-h-handoff-repro-scenarios-20260401a.json --count 1 --mode llm --min-turns 1 --max-turns 1 --scenario-coverage handoff --batch-size 1 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.0 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-block-h2-handoff-replay-20260401a --history-max 20 --max-failures 1 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --quality-lane dev --judge-mode all --judge-sample 1.0 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-block-h2-handoff-replay-20260401a --analyst a922 --status done --strict-artifacts --human-semantic-valid true --human-semantic-summary '<summary>'`

## Evidence
- updated TP with exact RCA + one web search
- deterministic test output
- focused handoff replay bundle at `/tmp/booking_quality/a922-block-h2-handoff-replay-20260401a`
- full `Block H` replay bundle remains `/tmp/booking_quality/a922-block-h-replay-20260401d`
- docs/state/packet sync only after the block is proven

## Rollback
- revert only the simulated manager callback transport change and matching tests
- delete `/tmp/booking_quality/a922-block-h2-handoff-replay-20260401a`
- keep `/tmp/booking_quality/a922-block-h-replay-20260401d` as the source evidence bundle

## No-go
- no consultant-runtime handoff patching
- no manager-action failure suppression without transport evidence
- no scenario-specific hardcode for dialog `3`
- no full `Block H` green claim from the focused handoff replay alone

## Риски / блокеры
- the timeout may still be a deeper runtime lock issue; if the focused replay stays red after the shared retry integration, stop and re-open RCA instead of broadening this block
- manual-audit gate must be kept clean; do not stack invalid repro runs again
- final acceptance remains open even if the focused handoff block closes

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- full `Block H` acceptance remains open until rerun on current `HEAD`
- manager action simulation still depends on live `/telegram-webhook` callback execution rather than a narrower test seam

### Why not in this block
- this block is only about the shared callback transport robustness seam surfaced by the acceptance replay

### Risk if deferred
- final acceptance remains blocked by a harness-owned manager callback timeout family

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`

### Expiry / trigger to stop deferral
- before the next full `Block H` rerun or any acceptance claim that includes handoff coverage

## Next-block contract (mandatory)
### Next block objective
- rerun full `Block H` after the focused handoff callback family is removed

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_diagnose_run_command.py -k "manager_telegram_action or scenarios_file or materialize" && python3 -m py_compile ops/diagnose.py && git diff --check`

### Blocked-by conditions
- simulated callback helper still bypasses the retry wrapper
- focused handoff replay stays `semantic_valid=false`
- runtime fingerprint on `127.0.0.1:18189` no longer matches current `HEAD`

### Owner role for closure
- Brain / Top Architect

## Branch / worktree / merge policy
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: current active worktree `HEAD`
- Merge policy: no whole-system closure claim until fresh full `Block H` replay is green
- Cleanup: stop the local runtime after focused replay unless immediately reused for the full `Block H` rerun
