# Runbook: Dialog Report

Purpose
- One-command dialog analysis: timeline + decision_meta/trace summary + outbox status + media/ASR.

When to use
- Need a full dialog reconstruction (user/assistant) for a time window.
- Investigating why a consultant replied a certain way.
- Preparing evidence for audit (decision_meta + outbox).

Command (typical)
```bash
python3 ops/diagnose.py dialog-report \
  --date 2026-01-29 \
  --start 16:27 \
  --end 16:36 \
  --tz Asia/Almaty \
  --sender "+7 778 589 0765" \
  --receiver-phone "+7 778 165 87 99"
```

Optional filters
- `--conversation-id` to force a specific conversation.
- `--branch-id` when receiver phone lookup fails.
- `--remote-jid` to override sender JID (skips phone normalization).
- `--output /tmp/dialog-report-<stamp>.md` or `--output -` for stdout.

Input rules
- `--start`/`--end` accept `HH:MM[:SS]` or `YYYY-MM-DD HH:MM[:SS]`.
- If time has no date, `--date` is required.
- If receiver lookup fails, retry with digits-only phone or pass `--branch-id`.

What you get
- Timeline of messages with `message_id`.
- Decision summary + raw `decision_meta` for each inbound.
- Outbox status/errors for each inbound (if any).
- Media info: type, storage path, ASR transcript (if available).

Evidence to capture
- The report path (e.g., `/tmp/dialog-report-*.md`).
- Command used (exact CLI).
- If needed, the conversation_id from the report header.

Notes
- Read-only: no DB writes.
- Media files live under `/home/zhan/truffles-media` and may be cleaned by TTL.
