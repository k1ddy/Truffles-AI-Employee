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

Artifacts
- `/tmp/booking_quality/<stamp>/scenarios.json`
- `/tmp/booking_quality/<stamp>/responses.jsonl`
- `/tmp/booking_quality/<stamp>/trace_bundle.jsonl`
- `/tmp/booking_quality/<stamp>/summary.json` (includes baseline_metrics + delta + coverage + judge)
- `/tmp/booking_quality/<stamp>/brief.md` (top failures + replay command + next-step hint)
- Baseline + history: `ops/results/booking_quality.json`

Evaluation contract (state-aware)
- `decision_meta` and `decision_trace` are required per inbound turn.
- If `turn.expect` is present, it overrides heuristic matching for action/info_sections/reply_type/state.
- Known states: `bot_active`, `pending`, `manager_active`; anything else is `unknown_state`.
- `manager_active`/`pending` mean no bot reply expected; replies here are flagged.
- `manager_active` requires a handover row; missing handover is a failure.
- Manager callbacks (simulate mode): `take` -> `manager_active` + `handover.status=active`; `resolve` -> `bot_active` + `resolved`; `return` -> `bot_active` + `bot_handling`.
- Info requests must match `info_sections`/intents (price/location/hours/promo/duration/parking/master).
- Booking-active turns should show slot progress; stalls are flagged.
- `booking_slot_stall` checks only slot-relevant turns (service/time/date/no-tag), not generic booking noise.
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
- unexpected_bot_reply_manager
- handover_missing
- info_section_miss
- booking_slot_stall
- manager_action_failed
- handoff_state_mismatch
- handoff_status_mismatch

Taxonomy (summary.taxonomy)
- expectation: expected_* mismatches (scenario/expectations drift).
- canon: missing decision_meta/trace or unknown_state (invariant breaks).
- code: missing_bot_reply, booking_slot_stall, handover state/status mismatches, manager_action_failed.
- data: info_section_miss (packs/content gaps).

Thresholds (summary.thresholds)
- reply_rate >= 0.90
- expected_reply_rate >= 0.95
- info_answer_rate >= 0.70
- unknown_state_rate <= 0.02
- booking_slot_progress_rate >= 0.25
- handoff_correct_rate >= 0.90

LLM judge (semantic, non-blocking)
- Enabled via `--judge-sample 0.1` (or `--judge-mode all` to judge every reply).
- Uses user text + bot reply + decision_meta/trace summary + pack truth (`SALON_TRUTH.yaml`) + consult playbook (`CONSULT_PLAYBOOK.yaml`).
  Judge context is limited to relevant sections (info tags / intents); full packs are not injected.
- Output stored in `summary.json` under `judge` and per-turn in `responses.jsonl`.
- Judge results are non-blocking and should be used as a signal, not a gate.

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
