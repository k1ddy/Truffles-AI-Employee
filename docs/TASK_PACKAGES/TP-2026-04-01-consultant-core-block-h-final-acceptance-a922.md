# TP-2026-04-01-consultant-core-block-h-final-acceptance-a922

## Название / цель
Провести `Block H — Final Acceptance` только на active worktree и честно обновить practical truth через один fresh replay по уже locked `r35f` сценариям плюс полный human semantic audit. Блок не делает runtime hotfix; он либо подтверждает whole-path improvement, либо surfaced first-fail family и открывает следующий runtime block.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-replay-and-full-human-semantic-audit-acceptance-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`

## Invariant
- no product or whole-system closure claim without one fresh current-head replay and full human semantic audit
- no runtime code changes inside this block unless Block H explicitly reopens a new runtime block from fresh evidence
- no comparison against `truffles-main`; truth comes from active worktree code plus fresh replay artifacts

## One web search (mandatory before implementation)
- Not activated in this block.
- Reason: `Block H` is an evidence/closure block with no implementation scope unless fresh replay reopens a new runtime family.
- Rule carried forward: if the replay surfaces a runtime family and a new implementation block is opened, do exactly one focused web search there before code.

## Root cause (mandatory)
- Status: not yet activated for code.
- Symptom under investigation: unknown until fresh replay updates current practical truth beyond `r35f`.
- Minimal reproduction: replay current-head active worktree against locked `r35f` scenarios and audit every surfaced weak/fail turn.
- Evidence base before run:
  - current practical truth: `/tmp/booking_quality/a922-practical-proof-20260330-r35f`
  - current program lock: `docs/SOURCE_OF_TRUTH.yaml`
  - active next move: `start_block_h_final_acceptance_from_fresh_locked_replay_after_block_g_operational_closeout_20260401`
- Five Whys / shared mechanism / broken invariant:
  - deferred until fresh replay surfaces the first failure family
  - if replay is green, no new RCA block is opened
  - if replay is red, RCA must be authored in the follow-up TP before any code
- Layer classification before code:
  - `unknown_until_fresh_replay`
- Fix mechanism:
  - none in this block; this block only proves or reopens

## Reuse-first decision
- Reuse:
  - existing locked scenario bundle from current practical truth: `/tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json`
  - existing guarded runner: `scripts/llm_quality_guarded.sh`
  - existing audit tool: `python3 ops/diagnose.py llm-quality-audit`
- Integrate:
  - run current-head replay from the active worktree against the locked scenario bundle
  - compare against `/tmp/booking_quality/a922-practical-proof-20260330-r35f/summary.json`
- Build:
  - no new harnesses, wrappers, or evaluator shortcuts in this block

## Scope
- start a fresh local runtime from the active worktree only
- prove runtime fingerprint parity (`/admin/version.git_commit == HEAD`)
- execute one guarded replay against locked `r35f` scenarios
- complete full human semantic audit for that replay
- classify first surfaced family honestly

## Out of scope
- runtime code changes
- new scenario generation
- new baseline/lock promotion chain
- docs/state/canon sync before the replay + audit are complete

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
- `/tmp/booking_quality/a922-block-h-replay-20260401a/*`
- active docs/state/packet only after Block H closes honestly

## Plan
1. Verify current active-worktree acceptance prerequisites and runtime parity inputs.
2. Start one fresh local runtime from `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`.
3. Run one guarded replay against locked `r35f` scenarios into `/tmp/booking_quality/a922-block-h-replay-20260401a`.
4. Complete full human semantic audit for that replay.
5. If replay is green, sync current practical truth and close Block H honestly.
6. If replay is red, stop-the-line on the first surfaced family, classify it, and open the next runtime block instead of patching inside acceptance.

## DoD
- runtime parity is proven on the active worktree (`/admin/version.git_commit == HEAD`)
- one fresh replay exists at `/tmp/booking_quality/a922-block-h-replay-20260401a`
- replay has full artifact bundle:
  - `summary.json`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `brief.md`
  - `manual_audit.md/json`
  - `manual_audit_workspace.md/json`
  - `family_registry.json`
  - `judge_conflicts.jsonl`
- first surfaced family is classified honestly with layer + mechanism
- no runtime hotfix is made inside this block

## Work mode
- `closure`

## Checks
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- Runtime parity:
  - `curl -fsS http://127.0.0.1:18189/admin/version`
  - `curl -fsS http://127.0.0.1:18189/admin/health`
- Fresh replay:
  - `bash -lc 'cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922 && scripts/llm_quality_guarded.sh --mode replay --run-id a922-block-h-replay-20260401a -- --base-url http://127.0.0.1:18189 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260330-r35f/summary.json --count 10 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text \"ок\" --tool-hooks auto --tool-confirm-text \"да\" --tool-cancel-text \"отмена\" --tool-calendar-text \"проверь запись\" --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-block-h-replay-20260401a --history-max 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --quality-lane dev --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000'`
- Audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-block-h-replay-20260401a --analyst a922 --status done --strict-artifacts --human-semantic-valid <true|false> --human-semantic-summary '<summary>' --oracle-judge-alignment <corroborated|conflicted|not_applicable> [--oracle-winner contract --oracle-resolution-summary '<summary>' if conflicted]`

## Evidence
- runtime parity probe (`HEAD`, `/admin/version`, `/admin/health`)
- guarded replay command and output dir
- full artifact bundle under `/tmp/booking_quality/a922-block-h-replay-20260401a`
- final family classification and next-step decision
- `STATE.md` / active docs sync only if Block H closes honestly

## Rollback
- stop local replay runtime on `127.0.0.1:18189`
- discard Block H doc/state updates if replay is not fully audited
- no code rollback in this block

## No-go
- no direct `python3 ops/diagnose.py llm-quality ...` as acceptance evidence
- no scenario mutation or regenerated baseline disguised as replay
- no runtime patching during replay triage
- no `green` or `done` claim from contract/oracle alone without human audit

## Риски / блокеры
- fresh replay may reopen a runtime family unrelated to `Block G`
- local runtime may require env from `/home/zhan/truffles-main/truffles-api/.env` because the active worktree has no own `.env`
- judge/oracle conflicts may require explicit contract-wins arbitration in the audit

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- whole-system product closure is still unproven until the fresh replay + audit finish
- strict acceptance-chain `go_to_full` promotion evidence remains separate from this one-replay Block H proof step

### Why not in this block
- this block proves or reopens; it does not implement new runtime families or rebuild the acceptance-chain governance package

### Risk if deferred
- practical truth remains stale at `r35f`, and the repo can drift into unsupported closure claims

### Linked follow-up Task Package(s)
- if replay is green: none, close Block H honestly
- if replay is red: author one new runtime TP from the first surfaced family before any code

### Expiry / trigger to stop deferral
- stop deferral immediately if anyone proposes more runtime code without a fresh Block H replay artifact bundle

## Next-block contract (mandatory)
### Next block objective
- either close `Block H` honestly from the fresh replay
- or open the first new runtime block from the replay’s first surfaced family

### First deterministic check command
- `python3 scripts/recovery_execution_guard.py`

### Blocked-by conditions
- runtime fingerprint does not match active worktree `HEAD`
- replay artifacts are incomplete or unaudited
- fresh replay surfaces a runtime family that requires RCA before any new code

### Owner role for closure
- Brain / Top Architect

## Branch / worktree / merge policy
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: active worktree `HEAD`
- Merge policy: no merge/closure claim until replay + audit finish
- Cleanup: stop local runtime and leave artifacts under `/tmp/booking_quality/a922-block-h-replay-20260401a`
