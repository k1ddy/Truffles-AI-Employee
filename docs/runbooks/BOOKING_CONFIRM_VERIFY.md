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

Notes
- Script uses dry-run by default; DB writes require `--apply`.
- Canceling appointments is optional and explicit.
- Calendar sync outbox may fail if OAuth tokens are placeholders. Fix: set `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` on API, complete OAuth via `/console/v1/calendar/google/connect` (callback `/api/calendar/callback`).
