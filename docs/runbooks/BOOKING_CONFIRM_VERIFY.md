# Runbook: Booking Confirm Verification

Purpose
- Verify booking confirm flow with confirm_slots + provider readiness using repeatable evidence.

When to use
- Booking confirm regressions (CA05/CA12).
- Calendar provider readiness checks (staleness gate).
- Need a single evidence bundle (livecheck + SQL + explain).

Prerequisites
- `minimum_data_contract` ready for target branch (check `/admin/health`).
- `TEST_MODE=1` in `truffles-api` container.
- Allowlist JIDs available (`OUTBOUND_ALLOWLIST_JIDS`).
- `branches.instance_id` present and matches payload instance_id.
- Local base URL (default `http://localhost:8000`).

LLM-quality start here (mandatory for new agents)
1. Entry points
   - `acceptance`: only `scripts/llm_quality_guarded.sh` (it injects chain token and enforces order).
   - `dev`: prefer `scripts/llm_quality_guarded.sh`; direct `python3 ops/diagnose.py llm-quality` is allowed only for forensic/dev lane and never as acceptance evidence.
2. Source of process truth
   - Lane model and gates: section `Quality Operating Model v2 (mandatory for all future runs)` in this file.
   - Acceptance chain operations: section `Guarded llm-quality quickstart (single entrypoint)` in this file.
3. Minimal acceptance workflow
   - Run `lock` using guarded wrapper in `quality-lane acceptance`.
   - Complete mandatory manual audit for the run dir.
   - Read chain `next_command` and run exactly that command.
   - Never start replay/full manually if `next_command` is empty or chain is blocked/aborted.
4. Mandatory artifacts per run
   - `/tmp/booking_quality/<run-id>/summary.json`
   - `/tmp/booking_quality/<run-id>/responses.jsonl`
   - `/tmp/booking_quality/<run-id>/trace_bundle.jsonl`
   - `/tmp/booking_quality/<run-id>/brief.md`
   - `/tmp/booking_quality/<run-id>/manual_audit.json` and `/tmp/booking_quality/<run-id>/manual_audit.md`
   - scenario governance registry entry in `/tmp/booking_quality/_scenario_governance_registry.json`
5. Mandatory actions by status
   - `canonical`: continue to chain `next_command`.
   - `incomplete`: resume same `run-id` (`--resume --output-dir ...`), do not start new run-id.
   - `invalid` or `failed`: stop expensive lane, return to deterministic + micro fail-fast loop (`L1/L2`), then re-enter acceptance through gates.

Tool map (quick reference)
| Tool | Main use | Never use for |
|------|----------|---------------|
| `scripts/llm_quality_guarded.sh` | Canonical runner entrypoint (dev/acceptance) | Bypassing chain/order/gates |
| `scripts/quality_chain_controller.sh` | Step orchestration (`prepare/finalize/status/abort/close`) | Running quality itself |
| `python3 ops/diagnose.py llm-quality` | Low-level engine (invoked by wrapper) | Manual acceptance launch without chain token |
| `python3 ops/diagnose.py llm-quality-audit` | Mandatory post-run manual audit artifact | Replacing contract evidence with judge text |

Quickstart (script)
```bash
scripts/booking_confirm_verify.sh \
  --client-slug demo_salon \
  --branch-slug branch_b \
  --apply \
  --cancel-appointments
```

Common overrides
```bash
scripts/booking_confirm_verify.sh \
  --client-slug demo_salon \
  --branch-slug branch_b \
  --base-url http://localhost:8000 \
  --jid-commit 77785890765@s.whatsapp.net \
  --jid-full 77015705555@s.whatsapp.net \
  --apply \
  --cancel-appointments
```

Manual steps (if not using script)
1) Preflight: `curl -s http://localhost:8000/admin/health`.
2) SQL: branch id + booking_settings + instance_id.
3) Provider readiness:
   - ensure `calendar_connections`, `google_calendar_tokens`, `calendar_sync_cursors` exist.
   - refresh cursor (`last_synced_at = now()`).
   - confirm `get_provider_health(...).ready == True`.
4) Live-check:
   - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca05-booking-commit ... --reset-before-suite`
   - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full ... --reset-before-suite`
5) Evidence SQL:
   - `appointments` (status CONFIRMED).
   - `appointment_sync_states` (row exists).
   - `outbox_messages` for booking send + calendar sync.
   - `calendar_blocks` unchanged.
6) Explain last inbound to confirm trace/meta and outbox guard status.

Evidence to capture
- Livecheck JSONL for CA05/CA12.
- Explain outputs for last step (CA05/CA12).
- SQL dumps: booking_settings, calendar connection/token/cursor, appointments, sync states, outbox, calendar blocks.

Common failures and fixes
- Staleness gate: provider_ready false. Fix: refresh `calendar_sync_cursors.last_synced_at`.
- Appointment reuse: allowlist JID already has active appointment. Fix: cancel those appointments before running.
- Instance mismatch: payload instance_id != branch.instance_id. Fix: use branch instance_id.
- Outbox payload guard: calendar sync events rejected. Fix: allow `calendar.sync_outbound` in payload validator (known GAP).
- Date parsing flips: input `YYYY-MM-DD` interpreted as `YYYY-DD-MM` in ru locale. Use explicit format or ISO parser.
- OAuth callback redirects to `0.0.0.0`: set `NEXTAUTH_URL` (or `NEXT_PUBLIC_CONSOLE_URL`) to the Console public URL and retry.

Notes
- Script uses dry-run by default; DB writes require `--apply`.
- Canceling appointments is optional and explicit.
- Calendar sync outbox may fail if OAuth tokens are placeholders.

---

Dialog scenario generator (booking stress)

Purpose
- Generate 10–15 turn client-only dialogs with interruptions to stress booking flow.

Quickstart
```bash
python3 scripts/booking_dialog_scenarios.py \
  --count 5 \
  --min-turns 10 \
  --max-turns 15 \
  --coverage booking,info,interrupt \
  --include-media \
  --media-mode text \
  --output /tmp/booking_dialog_scenarios.json
```

LLM mode (optional)
```bash
OPENAI_API_KEY=... \
python3 scripts/booking_dialog_scenarios.py \
  --mode llm \
  --count 3 \
  --min-turns 10 \
  --max-turns 15 \
  --coverage booking,info,interrupt,handoff \
  --include-media \
  --media-mode text \
  --output /tmp/booking_dialog_scenarios_llm.json
```

Scenario patterns included
- Booking + price + location interrupts + photo reference.
- Time/name swap + noise interruptions.
- Master preference switch + alternative time.
- RU/KZ mixed booking questions.
- Multi-service booking request + duration interrupt.

Notes
- Generator outputs client turns only (consultant replies are produced by live system).
- Each turn includes `expect` (action/info_sections/reply_type/state/expected_reply) for rule-based evaluation.
- Use `--coverage booking,info,interrupt,handoff` to force escalation coverage.
- `media-mode payload` uses placeholder URLs; update for real media tests.
- Calendar sync outbox may fail if OAuth tokens are placeholders. Fix: set `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` on API, complete OAuth via `/console/v1/calendar/google/connect` (callback `/api/calendar/callback`).

---

LLM booking quality runner (state-aware)

Purpose
- Run booking dialogs (LLM or template) with state-aware evaluation (manager_active/pending).
- Persist a baseline and compare deltas to avoid repeating the same findings.

Important
- Commands in this section can be used for forensic/dev workflows.
- For acceptance evidence, use only `scripts/llm_quality_guarded.sh` flow from section `Guarded llm-quality quickstart (single entrypoint)`.

When to use
- After any booking-related changes (packs, routing, booking slots, expected_reply_type).
- When investigating booking dialog gaps (missing replies, repeated prompts).
- Before/after fixes to confirm improvement without drift.

Prerequisites
- `TEST_MODE=1` in `truffles-api`.
- Allowlist JIDs (`OUTBOUND_ALLOWLIST_JIDS`) or `--remote-jid` from allowlist.
- Valid `WEBHOOK_SECRET` and `branches.instance_id` (auto-resolved if present).
- Admin token for outbox (`ALERTS_ADMIN_TOKEN`) unless `--skip-outbox`.
- Manager simulation: Telegram chat id in client settings or Console token.
- LLM-judge (optional): `OPENAI_API_KEY` (or `--judge-api-key`).
- `llm-quality` now auto-discovers `OPENAI_API_KEY` from env files (`truffles-api/.env`, `infrastructure/.env`) and container env; if unresolved, run fails fast with explicit key-source diagnostics.

Quickstart (smoke, no baseline update)
```bash
python3 ops/diagnose.py llm-quality \
  --mode llm \
  --count 1 \
  --min-turns 6 \
  --max-turns 8 \
  --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" \
  --reset-before-dialog
```

Baseline run (accepted regression point)
```bash
python3 ops/diagnose.py llm-quality \
  --mode llm \
  --count 5 \
  --min-turns 10 \
  --max-turns 15 \
  --include-media \
  --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" \
  --scenario-coverage booking,info,interrupt,handoff \
  --manager-mode simulate \
  --pending-mode ack \
  --judge-sample 0.1 \
  --reset-before-dialog \
  --append-history \
  --update-baseline
```

Deterministic bugfix loop (lock + replay)
```bash
# 1) Lock comparable baseline once (generates scenarios.json + summary.json)
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --mode llm \
  --count 10 \
  --min-turns 10 \
  --max-turns 15 \
  --include-media \
  --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" \
  --scenario-coverage booking,info,interrupt,handoff \
  --tool-hooks auto \
  --seed 42 \
  --run-id booking-lock-42

# 2) After each code fix: replay the same scenarios, compare to locked summary, stop early on obvious regressions
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --scenarios-file /tmp/booking_quality/booking-lock-42/scenarios.json \
  --baseline-summary /tmp/booking_quality/booking-lock-42/summary.json \
  --count 10 \
  --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" \
  --tool-hooks auto \
  --reset-before-dialog \
  --max-failures 20
```

State-isolated realistic profile (faster, less drift; recommended for daily bugfix loops)
```bash
# Fast lock/replay on frozen scenarios with stable runtime checks (logic-first)
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --base-url http://127.0.0.1:18084 \
  --client-slug demo_salon \
  --scenarios-file /tmp/booking_quality/<lock>/scenarios.json \
  --count 10 \
  --timeout-profile realistic \
  --reset-before-dialog \
  --jid-mode unique \
  --manager-mode skip \
  --pending-mode skip \
  --tool-hooks auto \
  --tool-evidence-policy strict \
  --skip-outbox \
  --judge-mode all \
  --baseline-summary /tmp/booking_quality/<canonical-baseline>/summary.json \
  --run-id booking-replay-<stamp>-unique
```

Why this profile
- `--jid-mode unique` isolates dialog state and prevents pending/handover leftovers from previous runs.
- `--skip-outbox` removes outbox latency from logic-focused debugging; keep full outbox checks for acceptance runs.
- `manager-mode/pending-mode=skip` avoids synthetic manager races while fixing core dialog logic.
- `--timeout-profile realistic` keeps non-aggressive network/poll windows.
- `--tool-evidence-policy strict` marks run `INVALID` when booking/calendar/confirm evidence is missing (`tool_evidence:*` in `infra_reasons`).

Realistic timeout profile (recommended for stable evidence)
```bash
# Default profile (recommended): realistic
--timeout-profile realistic

# For iterative replay loops (faster, still safe):
--timeout-profile fast-replay \
--min-wait 0 \
--max-wait 0.15
```

Parallel-safe runs across worktrees
- Do not reuse the same `--run-id` concurrently.
- If `--run-id` is omitted, `llm-quality` auto-generates a worktree-scoped id (`<timestamp>-<namespace>-p<pid>-<rand>`).
- This default keeps simultaneous runs from different worktrees isolated in `/tmp/booking_quality/*`.
- Prefer dedicated local API port per worktree (`--base-url http://127.0.0.1:<port>`); shared API ports increase state bleed and timeout noise.
- Preflight health gate before long run: `curl -sS --max-time 5 $BASE_URL/admin/health`.
- If run appears stalled, track progress by DB message-id count (not only `responses.jsonl`, which is buffered until process exit):
  - `SELECT count(*) FROM messages WHERE metadata->>'messageId' LIKE 'LLM-QUAL-<run-id>%';`

Webhook timeout triage (stop-the-line for invalid runs)
- Symptom: `/webhook/<client>` returns no bytes for 30-180s and runner logs `curl rc=28`.
- Check quickly before long replay:
  - `curl -sS --max-time 5 http://127.0.0.1:18084/admin/health`
  - Send one manual webhook and measure latency (same secret + instance_id as replay).
- If webhook hangs for >10 minutes (no `responses.jsonl` growth), stop run and mark infra:
  - `pkill -f "<run-id>"`
  - Keep partial artifacts, do not delete output dir.
- Restart only after infra is stable, then replay with the same:
  - `--scenarios-file`, `--baseline-summary`, `--run-id`, timeout profile.
- If branch routing is ambiguous, pass explicit `--instance-id` from `branches.instance_id` for target branch.
- If `preflight_clear` prints `state_before=pending` with `cleared=false`, treat run as contaminated and restart with `--jid-mode unique`.

Judge modes and when to use them
- `--judge-mode critical`: default for rapid fix loops. Judges only critical turns (booking/handoff/tool-sensitive or turns with strict reasons/explicit expectations).
- `--judge-mode all`: full semantic audit before final acceptance/baseline decision.
- `--judge-mode sample`: lightweight monitoring.
- `--judge-mode off`: debug only (not canonical for strict replay evidence).

Three-step release-quality flow (`1/2/3`)
```bash
# 1) Replay on frozen scenarios with realistic profile and critical judge (fastest valid loop)
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --base-url http://127.0.0.1:18084 \
  --client-slug demo_salon \
  --branch-slug main \
  --scenarios-file /tmp/booking_quality/<lock>/scenarios.json \
  --baseline-summary /tmp/booking_quality/<lock>/summary.json \
  --count 10 \
  --tool-hooks auto \
  --reset-before-dialog \
  --judge-mode critical \
  --judge-max-tokens 220 \
  --judge-timeout 20 \
  --timeout 30 \
  --poll-timeout 25 \
  --poll-interval 0.4 \
  --trace-timeout 25 \
  --trace-interval 0.4 \
  --min-wait 0.2 \
  --max-wait 0.4 \
  --retry-count 2 \
  --retry-backoff 0.5 \
  --max-failures 20 \
  --run-id booking-replay-<stamp>-critical

# 2) Run the same frozen scenarios with judge-mode all for full semantic check
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --base-url http://127.0.0.1:18084 \
  --client-slug demo_salon \
  --branch-slug main \
  --scenarios-file /tmp/booking_quality/<lock>/scenarios.json \
  --baseline-summary /tmp/booking_quality/<lock>/summary.json \
  --count 10 \
  --tool-hooks auto \
  --reset-before-dialog \
  --judge-mode all \
  --judge-timeout 25 \
  --timeout 30 \
  --poll-timeout 25 \
  --poll-interval 0.4 \
  --trace-timeout 25 \
  --trace-interval 0.4 \
  --min-wait 0.2 \
  --max-wait 0.4 \
  --retry-count 2 \
  --retry-backoff 0.5 \
  --max-failures 20 \
  --run-id booking-replay-<stamp>-all

# 3) Update canonical baseline only if run is canonical-valid:
# infra_valid=true, semantic_valid=true, judge.enabled=true
TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --mode llm \
  --count 10 \
  --min-turns 10 \
  --max-turns 15 \
  --include-media \
  --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" \
  --scenario-coverage booking,info,interrupt,handoff \
  --tool-hooks auto \
  --seed 42 \
  --judge-mode all \
  --timeout 30 \
  --poll-timeout 25 \
  --trace-timeout 25 \
  --reset-before-dialog \
  --update-baseline \
  --run-id booking-lock-<stamp>-canonical
```

Parallel worktree isolation notes
- Use dedicated output dirs per run: `/tmp/booking_quality/<run-id>`.
- Keep unique `run-id` per run/worktree.
- Judge cache file is namespaced by worktree path to avoid cross-worktree contamination.
- Never compare runs with different scenarios/seed/profile.

Strict replay (fast, frozen scenarios, anti-false-OK)
```bash
# Use external timeout so network/outbox stalls do not block progress for hours.
timeout 20m TEST_MODE=1 python3 ops/diagnose.py llm-quality \
  --base-url http://localhost:8000 \
  --client-slug demo_salon \
  --scenarios-file /tmp/booking_quality/20260207-stress-main-seed-1337-gen/scenarios.json \
  --count 10 \
  --tool-hooks check \
  --manager-mode check \
  --pending-mode skip \
  --min-wait 0 \
  --max-wait 0 \
  --max-failures 20 \
  --output-dir /tmp/booking_quality/<stamp>-strict-main-seed-1337-replay
```

If timeout is hit
1. Do not delete partial artifacts.
2. Check whether `/summary.json` exists in output dir.
3. If no summary: rerun exact same command and output dir.
4. If summary exists: treat run as complete and continue analysis.

Resumable matrix runner (recommended for unstable network/session)
```bash
# Resume in-place without touching completed artifacts
scripts/booking_quality_matrix_resumable.sh \
  --run-stamp 20260207-stress \
  --base-url http://localhost:8000 \
  --client-slug demo_salon \
  --branches main,branch_b \
  --seeds 42,1337,2026,9001
```

What the runner guarantees
- Step identity is deterministic: `{run_stamp}-{branch}-baseline|seed-{seed}-gen|seed-{seed}-replay`.
- If `summary.json` exists for a step, the step is skipped (no overwrite).
- Incomplete step (missing `summary.json`) is re-run with retry/backoff.
- Stop-the-line is automatic on `webhook_errors > 0` or `infra_errors > 0`.
- Writes heartbeat/state into `/tmp/booking_quality/<run_stamp>-state.json`.
- Rebuilds `/tmp/booking_quality/<run_stamp>-matrix-report.tsv` on each run.

Long-run execution (tmux/nohup)
```bash
# tmux (preferred for remote sessions)
tmux new -s booking-matrix
scripts/booking_quality_matrix_resumable.sh --run-stamp 20260207-stress | tee /tmp/booking_quality/20260207-stress-run.log
# detach: Ctrl+b then d
# reattach:
tmux attach -t booking-matrix

# or nohup
nohup scripts/booking_quality_matrix_resumable.sh --run-stamp 20260207-stress \
  > /tmp/booking_quality/20260207-stress-run.log 2>&1 &
```

Resume protocol after interruption
1. Check current state:
   `cat /tmp/booking_quality/20260207-stress-state.json`
2. Check completed steps:
   `cat /tmp/booking_quality/20260207-stress-matrix-report.tsv`
3. Re-run the same command with the same `--run-stamp`.
4. Confirm that already completed outputs were skipped (look for `skip completed step` in log).

Advanced stress matrix (human + agent guide)
1. Fix constants before run:
   - One runtime (`--base-url`) for all compared runs.
   - Stable knobs: `--count`, `--min-turns`, `--max-turns`, `--scenario-coverage`, `--include-media`.
   - Always `--reset-before-dialog`.
2. Collect baseline per branch:
   - At least `count >= 5` before using comparisons for decisions.
3. Generate stress per seed:
   - Use at least 4 seeds (`42,1337,2026,9001`) to reduce accidental overfit.
   - Keep generation and replay count equal (`count=10` recommended).
4. Replay only from frozen scenarios:
   - `--scenarios-file <gen>/scenarios.json`
   - `--baseline-summary <baseline>/summary.json`
5. Enforce gates:
   - Hard stop: `webhook_errors`, `infra_errors`.
   - Quality targets: `decision_meta_coverage=1.0`, `unknown_state_rate<=0.02`, track pass-rate and info mismatch trend.
6. Triage failures into 3 bins:
   - `code`: pipeline/routing/trace/meta bugs.
   - `data`: pack/content gaps (`info_section_miss` with correct routing).
   - `expectation`: stale or wrong evaluator expectations.
7. Fix discipline:
   - One repeatable failure -> one fix -> one regression test.
   - Re-run only affected seed replay first, then full branch matrix.
8. Evidence bundle for handoff:
   - `summary.json`, `responses.jsonl`, `trace_bundle.jsonl`, `brief.md`, `matrix-report.tsv`, and exact replay command.

Detailed operator workflow (future agents + humans)
1. Pre-run checklist (must pass before first command)
   - Confirm branch/worktree/session ownership (`scripts/session_check.sh`).
   - Confirm API health (`curl -s <base-url>/admin/health`).
   - Confirm allowlist JIDs are present and not equal to branch sender JID.
   - Confirm baseline path exists and is readable.
   - Confirm output stamp is new (do not reuse someone else's stamp).
2. Generation strategy
   - Preferred: generate once per seed, replay many times from frozen `scenarios.json`.
   - If `OPENAI_API_KEY` is unavailable, do not block: reuse previously generated `scenarios.json`.
   - Keep `count/min-turns/max-turns` identical between generation and replay.
3. Replay strategy
   - Always pass `--scenarios-file` and `--baseline-summary` for comparisons.
   - Keep one runtime and one branch per run command.
   - Use `--max-failures` to cap runtime during regression loops.
   - For long runs, always tee logs to file and run in tmux/nohup.
4. Interruption recovery (network/shell/session reset)
   - Do not delete partial artifacts in `/tmp/booking_quality`.
   - Check whether run already finished: `test -f <output>/summary.json`.
   - If finished: collect metrics only, do not rerun.
   - If not finished: rerun the exact replay command with the same output dir and same run stamp.
   - For single-run recovery use `--resume` on the same `--run-id`/`--output-dir`; do not use `--allow-output-overwrite` for recovery.
   - Resume requires `<output>/runtime_state.json`; if it is missing (legacy run), restart from lock/replay command as a fresh run.
   - Resume safety checks are strict: run id, scenario fingerprint, and `responses/trace` row counts must match checkpoint; mismatches stop the run.
   - Expected stdout evidence for successful resume:
     - `stage=llm_quality_resume_preflight` with `completed_turns > 0`
     - `stage=llm_quality_progress event=dialog_resume_skip|dialog_resume_continue`
     - final `quality_status.run_integrity_valid=true`
   - For matrix script: rerun the same `scripts/booking_quality_matrix_resumable.sh --run-stamp ...`; completed steps are skipped automatically.
5. Analysis order (to avoid false conclusions)
   - First: `stop_reason`, `webhook_errors`, `infra_errors` (hard blockers).
   - Second: `strict_pass_rate`, `hard_fail_rate`, `unknown_state_rate`, `decision_meta_coverage`.
   - Third: `pass_rate` as supporting metric only.
   - Fourth: reason deltas (`expected_*`, `info_section_miss`, `missing_bot_reply`, `outbox_delivery_failed`, `outbox_delivery_timeout`, `booking_slot_stall`, `false_booking_confirmation`, `calendar_tool_contract_miss`).
   - Fifth: inspect top 3 reasons in `summary.top_failures` and confirm on `responses.jsonl`.
6. Fix loop contract
   - One dominant repeatable reason -> one code/data/evaluator fix.
   - Add one regression test for that reason.
   - Replay only affected seed first.
   - If improved, run broader seed set and update handoff evidence.
7. Handoff package (minimum)
   - Paths to `summary.json`, `responses.jsonl`, `trace_bundle.jsonl`, `brief.md`.
   - Table of deltas versus baseline (seed-by-seed).
   - Explicit callout: which failures improved and which worsened.
   - Exact next command for continuation.

Guarded llm-quality quickstart (single entrypoint)
1. Purpose
   - `scripts/llm_quality_guarded.sh` is the canonical runner wrapper.
   - It is semi-automatic: it runs checks and blocks bad launches, and for `quality-lane=acceptance` it now delegates step control to `scripts/quality_chain_controller.sh`.
   - Direct acceptance run via `python3 ops/diagnose.py llm-quality ...` is blocked unless chain token args are present.
2. Lock run (acceptance envelope)
   - Prepare `PG0..PG6` checklist JSON (example path: `/tmp/booking_quality/pg_checklist-<id>.json`).
   - Required schema (minimum):
     ```json
     {
       "go_to_full": {
         "PG0": {"status": "pass"},
         "PG1": {"status": "pass"},
         "PG2": {"status": "pass"},
         "PG3": {"status": "pass"},
         "PG4": {"status": "pass"},
         "PG5": {"status": "pass"},
         "PG6": {"status": "pass"},
         "root_cause_statement": "one-sentence root cause linked to evidence",
         "defect_mapping": [
           {
             "defect_class": "booking_flow_break",
             "target_test": "path::test_name",
             "gate": "PG1",
             "owner": "a1"
           }
         ],
         "l1_evidence": {
           "junit_xml_path": "/tmp/booking_quality/<l1-run-id>/pytest-junit.xml",
           "recorded_at": "2026-03-01T05:40:00Z"
         },
         "l2_evidence": {
           "summary_path": "/tmp/booking_quality/<l2-run-id>/summary.json",
           "run_id": "<l2-run-id>"
         },
         "evidence_freshness_hours": 24
       }
     }
     ```
   - `target_test` is enforced as executable reference: `path/to/test_file.py::test_name` must exist in repository.
   - `l1_evidence.junit_xml_path` is mandatory and machine-validated against every `defect_mapping.target_test` (must be `passed` in JUnit report).
   - `l2_evidence.summary_path` is mandatory and fail-closed validated (`infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`, `quality_lane_effective != acceptance`).
   - `evidence_freshness_hours` (default `24`) fail-closes stale L1/L2 evidence.
   - `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-<id> --pg-checklist /tmp/booking_quality/pg_checklist-<id>.json -- --base-url <url> --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
3. Replay run (same scenarios + baseline)
   - `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-<id> -- --base-url <url> --client-slug demo_salon --scenarios-file /tmp/booking_quality/booking-lock-<id>/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-<id>/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
4. Full run (same acceptance lane)
   - `scripts/llm_quality_guarded.sh --mode full --run-id booking-full-<id> -- --base-url <url> --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-<id>/summary.json`
5. Mandatory post-run audit
   - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/<run-id> --status done --strict-artifacts`
   - For conflict runs, include explicit arbitration:
     `--oracle-judge-alignment conflicted --oracle-winner contract --oracle-resolution-summary "<contract evidence wins>"`
6. Resume one interrupted run
   - `scripts/llm_quality_guarded.sh --mode <lock|replay|full> --run-id <same-run-id> -- --base-url <url> --client-slug demo_salon --resume --output-dir /tmp/booking_quality/<run-id> ...`
7. Why a run can be blocked by guard
   - Previous run in same mode is `incomplete/invalid/failed`.
   - Previous run has `manual_audit != done`.
   - Forensic SLA invalid (`manual_audit` missing analyst/timestamp/root-cause/next-step/oracle arbitration contract).
   - Oracle conflict unresolved (judge-vs-contract conflict without `winner=contract` and resolution).
   - Scenario governance missing (acceptance replay/full scenarios are not registered or not promotion-eligible).
   - Duplicate fingerprint or reused run-id.
   - Chain-controller preflight failed (step-order/run_id-mode mismatch/resume-only/token mismatch).
   - Acceptance `lock` missing/failed `--pg-checklist` (`PG0..PG6`).
8. Allowed override (for stale historical index only)
   - Use `--allow-pending-previous` only to bypass old unrelated mode blockers.
   - Do not use it to bypass current run failures; fix root cause first.
9. Chain controller status / lifecycle
   - Status: `scripts/quality_chain_controller.sh status --chain-id <id>`
   - Manual abort: `scripts/quality_chain_controller.sh abort --chain-id <id> --reason root_cause_required`
   - Manual close (after accepted full canonical): `scripts/quality_chain_controller.sh close --chain-id <id>`

Artifacts
- `/tmp/booking_quality/<stamp>/scenarios.json`
- `/tmp/booking_quality/<stamp>/responses.jsonl`
- `/tmp/booking_quality/<stamp>/trace_bundle.jsonl`
- `/tmp/booking_quality/<stamp>/summary.json` (includes baseline_metrics + delta + coverage + judge)
- `/tmp/booking_quality/<stamp>/brief.md` (top failures + replay command + next-step hint)
- Baseline + history: `ops/results/booking_quality.json`

Evaluation contract (state-aware)
- `decision_meta` and `decision_trace` are required per inbound turn.
- `evaluation.ok` is legacy compatibility; use `evaluation.strict_ok` + `strict_pass_rate` for real quality gate.
- Hard-fail reasons (`missing_bot_reply`, `outbox_delivery_failed`, `outbox_delivery_timeout`, `false_booking_confirmation`, `calendar_tool_contract_miss`, meta/trace/state contract breaks) must never be treated as OK.
- If `turn.expect` is present, it overrides heuristic matching for action/info_sections/reply_type/state.
- Known states: `bot_active`, `pending`, `manager_active`; anything else is `unknown_state`.
- `manager_active`/`pending` mean no bot reply expected; replies here are flagged.
- `manager_active` requires a handover row; missing handover is a failure.
- Manager callbacks (simulate mode): `take` -> `manager_active` + `handover.status=active`; `resolve` -> `bot_active` + `resolved`; `return` -> `bot_active` + `bot_handling`.
- Info requests must match `info_sections`/intents (price/location/hours/promo/duration/parking/master).
- Info matching is current-turn scoped (pipeline window); stale historical trace must not satisfy current info request.
- Booking-active turns should show slot progress; stalls are flagged.
- `booking_slot_stall` checks only slot-relevant turns (service/time/date/no-tag), not generic booking noise.
- If response text claims booking confirmation, evaluator requires appointment/calendar evidence; otherwise `false_booking_confirmation`.
- If appointment/calendar path is active without successful calendar outcome, evaluator reports `calendar_tool_contract_miss`.
- Booking `expected_reply_type` is limited to `service_choice`/`time`/`name` (phone/confirm are not expected_reply_type).

Reason codes (summary.failures / failure_counts)
- decision_meta_missing
- decision_trace_missing
- unknown_state
- expected_state_mismatch
- expected_action_mismatch
- expected_reply_type_mismatch
- expected_reply_mismatch
- expected_info_section_miss
- missing_bot_reply
- outbox_delivery_failed
- outbox_delivery_timeout
- unexpected_bot_reply_manager
- handover_missing
- info_section_miss
- booking_slot_stall
- false_booking_confirmation
- calendar_tool_contract_miss
- judge_fail
- manager_action_failed
- handoff_state_mismatch
- handoff_status_mismatch

Taxonomy (summary.taxonomy)
- expectation: expected_* mismatches (scenario/expectations drift).
- canon: missing decision_meta/trace or unknown_state (invariant breaks).
- code: missing_bot_reply, outbox_delivery_failed, outbox_delivery_timeout, booking_slot_stall, false_booking_confirmation, calendar_tool_contract_miss, handover state/status mismatches, manager_action_failed.
- data: info_section_miss (packs/content gaps).

Thresholds (summary.thresholds)
- reply_rate >= 0.90
- strict_pass_rate >= 0.90
- expected_reply_rate >= 0.95
- info_answer_rate >= 0.70
- hard_fail_rate <= 0.00
- unknown_state_rate <= 0.02
- booking_slot_progress_rate >= 0.25
- handoff_correct_rate >= 0.90

LLM judge (semantic signal, optional strict gate)
- Enabled via `--judge-sample 0.1` (or `--judge-mode all` to judge every reply).
- Uses user text + bot reply + decision_meta/trace summary + pack truth (`SALON_TRUTH.yaml`) + consult playbook (`CONSULT_PLAYBOOK.yaml`).
  Judge context is limited to relevant sections (info tags / intents); full packs are not injected.
- Output stored in `summary.json` under `judge` and per-turn in `responses.jsonl`.
- If judge is enabled and verdict is `fail`, evaluator adds `judge_fail` to `evaluation.strict_reasons`.
- Keep judge disabled for pure deterministic runs; enable it when semantic supervision is needed.

Chaos coverage map (summary.coverage)
- states: bot_active/pending/manager_active/unknown.
- intents/actions: from decision_meta.
- language: ru/kk/mixed/latin/unknown.
- modality: text vs media (+ media_kind).
- noise: noisy vs total turns.
- trace_stages: gate coverage by trace stages.
- tools: confirm/commit/cancel/calendar events + outcomes.

Tool hooks (optional)
- `--tool-hooks check` (default): record tool signals only.
- `--tool-hooks auto`: send confirm/cancel/calendar texts when tool signals fire (skips if turn has matching tag).
- `--tool-confirm-text` / `--tool-cancel-text` / `--tool-calendar-text` / `--tool-hook-limit` / `--tool-hook-wait` tune hooks.

How to read results
- `reply_rate` counts inline `bot_response` + outbox; `expected_reply_rate` excludes expected non-replies (pending/manager_active).
- `info_answer_rate` and `info_mismatch` flag interruptions (price/location/hours/promo/etc).
- `responses.jsonl` is the drill-down: check `conversation_state`, `expected_response_reason`, `info_mismatch`.
- `summary.metrics.state.reply_rate_by_state` shows reply rate per state; keep `unknown_state_rate` low.
- `trace_bundle.jsonl` contains trace/meta/outbox + trace_id for fast inspection and per-turn diffs.
- `summary.failures` is the compact error list (conversation/message/trace/stage pointers).
- `summary.taxonomy` shows how failures split across expectation/canon/code/data.

Continuity / no-drift rules
- If baseline is empty (first run), a small bootstrap run is acceptable; replace with `--count >= 5` on the next accepted run.
- Do not update baseline on tiny runs after bootstrap; use `--count >= 5` for baseline updates.
- Keep `--count`, `--min-turns`, `--max-turns`, `--mode`, `--include-media` stable across comparisons.
- For bugfix iterations, compare only against an explicit locked run:
  `--scenarios-file <lock>/scenarios.json --baseline-summary <lock>/summary.json`.
- Use `--max-failures` for fail-fast loops to cap runtime during regressions.
- Attach `brief.md` from the latest run into session handoff so the next agent starts from concrete top failures.
- For gates, add `--fail-on-thresholds` and `--fail-on-regression --regression-tolerance 0.02`.
- Use `--append-history` to track failure trends in `ops/results/booking_quality.json`.
- Always record the run in `STATE.md` with the `summary.json` path and keep `ops/results/booking_quality.json` in git.
- Use `--seed` for reproducible deltas when debugging the same issue.

Notes
- Requires allowlist JIDs (state mode). Use `--remote-jid` for a fixed allowlist number.
- Manager simulation uses Telegram callbacks by default; switch to console with `--manager-channel console`.
- Use `--reset-before-dialog` to clear pending/manager_active before each dialog.

---

Quality Operating Model v2 (mandatory for all future runs)
1. Lane model
   - `L0`: static/contract checks (no expensive LLM runs).
   - `L1`: deterministic targeted tests for concrete root-cause.
   - `L2`: micro chaos fail-fast (`--max-failures`), cheap validation.
   - `L3`: acceptance release chain only (`lock -> replay -> full`).
2. Key rule
   - `L3` is not a debug loop. It is a release gate and runs only after `L0/L1/L2` are green.
3. No-Loop Law
   - Do not repeat expensive run with same fingerprint without new root-cause evidence.
   - If `L3` run is `INVALID/NON-CANONICAL`, return to `L1/L2`; do not start next `L3` immediately.
4. Oracle priority
   - Primary: `decision_meta/decision_trace/outcome` contract.
   - Secondary: judge verdict as corroboration.
   - Tertiary: text checks as debug hints only.

Go-to-Full checklist (must pass before any L3 run)
1. `PG0`: root-cause statement linked to artifacts (`summary/responses/trace/manual_audit`).
2. `PG1`: target contract test exists and is green after fix.
3. `PG2`: deterministic subset green.
4. `PG3`: micro fail-fast run shows improvement on target blocker class.
   - Machine evidence: checklist includes green `l2_evidence.summary_path`.
   - Promotion linkage: checklist includes green `l1_evidence.junit_xml_path` proving deterministic target tests are passed.
5. `PG4`: manual audit done and consistent with summary.
6. `PG5`: runtime/provenance/preflight valid.
7. `PG6`: no pending interrupted run in same chain/fingerprint.

Minimal operating sequence (recommended)
1. Run `L1` tests for the target defect.
2. Run one `L2` micro fail-fast validation.
3. Complete forensic handoff (`root_causes`, `top_failures`, `next_command`).
4. Only then start `L3 lock` via guarded wrapper/chain controller.
5. Continue `replay/full` only if `lock` is canonical and solves target blocker.

Hard no-go
- Do not run `lock/replay/full` “just to check maybe it passes now”.
- Do not use judge-only success as acceptance evidence.
- Do not skip manual audit before next expensive run.
- Do not start new run-id when `resume` is required.
- Do not launch `L3 lock` with stale (`> evidence_freshness_hours`) or self-declared-only L1/L2 evidence.
