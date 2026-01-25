# CHAOS-SIM — Human-Like Dialog Runs

Purpose: run realistic (noisy, interrupted) dialog simulations against `/webhook` and evaluate decision_meta/trace
without relying on scripted inputs. This runbook documents the current setup and how to continue safely.

Acceptance: use `SPECS/CONSULTANT.md` → “DEFINITION OF DONE — Consultant v1” to decide readiness.

## Current Context (2026-01-25)

- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Branch: `feat/slot-lock-booking-confirm`
- Files touched: `ops/diagnose.py` (evaluator relaxations + `--kinds` filter + `--sim-time`)
- Latest booking-only run (sim-time, completed):
  - Command:
    ```
    python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high \
      --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" \
      --manager-mode skip \
      --min-wait 0 --max-wait 0.2 \
      --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_booking_simtime_mgrskip_5b
    ```
  - Summary: failures=9, cases_processed=5, completed
  - Artifacts: `/tmp/chaos_booking_simtime_mgrskip_5b` (`cases.jsonl`, `failures.jsonl`, `report.md`, `summary.json`)
- Prior booking-only run (sim-time, completed): `/tmp/chaos_booking_simtime_eval_5b` (failures=20)
- Previous booking-only run (pre sim-time): `/tmp/chaos_booking_5`

## What Changed in `ops/diagnose.py`

- Human-like generator already in place (fillers, interruptions, corrections).
- Evaluator relaxations to reduce false positives for:
  - booking prompt interruptions and multi-intent replies,
  - clarify-limit escalation during pending/booking completion,
  - pending responses treated as acceptable booking completion,
  - ai_response counted as reply/smalltalk,
  - pending action variance (pending_ack/wait/status),
  - out_of_domain false positives (now only when action/intent is OOD).
- New filter: `--kinds` to run only a subset of cases.

Where to look:
- Generator and evaluators: `ops/diagnose.py`
- Key helpers: `_chaos_action_fallback_ok`, `_chaos_reply_type_fallback_ok`,
  `_chaos_pending_action_ok`, `_chaos_state_fallback_ok`.

## Quick Runs (Recommended)

1) Dry-run generator only (no webhook):
```
python3 ops/diagnose.py chaos-sim --count 3 --min-turns 10 --max-turns 12 --noise high \
  --mode logic --dry-run --dump-cases --output-dir /tmp/chaos_human
```

2) Booking-only sanity (logic mode, 5–10 cases):
```
python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high \
  --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" \
  --manager-mode skip \
  --min-wait 0 --max-wait 0.2 \
  --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_booking_simtime_eval_5
```

3) Full mix (once booking-only is stable):
```
python3 ops/diagnose.py chaos-sim --count 20 --min-turns 10 --max-turns 12 --noise high \
  --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" \
  --min-wait 0 --max-wait 0.2 \
  --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_full
```

4) LLM mode (requires keys and budget):
```
python3 ops/diagnose.py chaos-sim --count 5 --min-turns 10 --max-turns 12 --noise high \
  --mode llm --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" \
  --min-wait 0 --max-wait 0.2 \
  --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_llm
```

## Run Continuity (Run-Ledger + Resume)

- Always set `--run-id` and `--output-dir` for any investigation you plan to continue.
- Use `--resume` to continue the same run (same seed/jid_base/case map).
- Use `--bundle-on-fail` to auto-save trace bundles for each failure message_id.

Example:
```
python3 ops/diagnose.py chaos-sim --run-id demo-run-01 --count 1 --kinds booking --mode llm \
  --sim-time "2026-01-24T12:00:00+06:00" --bundle-on-fail --output-dir /tmp/chaos_continuity_demo

python3 ops/diagnose.py chaos-sim --resume --run-id demo-run-01 --output-dir /tmp/chaos_continuity_demo
```

Artifacts:
- `run.json` (ledger)
- `report.md` (actionable summary)
- `bundles/*` (trace bundles on failures)

## Artifacts to Review

- `cases.jsonl`: generated dialogue turns (what we sent).
- `failures.jsonl`: per-turn evaluation failures with expected vs actual.
- `report.md`: summary + failure counts.
- `rag_debug.jsonl`: only when `--rag-audit` is enabled.

## Livecheck E2E (Booking + Manager)

- Command:
  ```
  python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full
  ```
- Latest run (2026-01-25):
  - conversation_id: `a7ec4c6e-d5b4-4c5d-ae8e-909b09ea9aaf`
  - appointment_id: `f589bb54-520c-4b31-a949-66b3582a1b8c` (status `PENDING_CONFIRMATION`)
  - decision_trace: `booking_commit` present
  - outbox_status: `SENT`
  - handover: `pending` → `resolved` (manager take/resolve 200)
- Note: booking flow escalates after commit; suite reuses that handover for manager actions.

## Known Limitations (Current)

- Ensure `--sim-time` stays within business hours for booking flows.
- Use `--manager-mode skip` for chaos-only runs; manager take/resolve is validated in live suites.
