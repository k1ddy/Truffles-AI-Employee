# Runbook: Trace Bundle

Purpose
- Capture a single bundle with decision_meta, decision_trace, outbox rows, and latency.

When to use
- Live-check failures or slow delivery.
- Need a single artifact for STATE.md evidence.

Command
```bash
python3 ops/diagnose.py trace-bundle \
  --client-slug demo_salon \
  --message-id "<CHATFLOW_MESSAGE_ID>" \
  --output /tmp/trace-bundle.json
```

Alternative selectors
```bash
python3 ops/diagnose.py trace-bundle --conversation-id "<CONV_ID>" --limit 1
python3 ops/diagnose.py trace-bundle --remote-jid "7701...@s.whatsapp.net" --minutes 60
python3 ops/diagnose.py trace-bundle --receiver-phone "+7701..." --text "LC-MARKER" --minutes 120
```

What you get
- `decision_meta` (including `timing.*` if present).
- `decision_trace` (conversation context trace list).
- `outbox.rows` with status, attempts, last_error, payload_meta.
- `outbox.latency_ms` with inbound-to-outbox and outbox total time.

Evidence to capture
- Bundle file path and a short snippet (message_id, conversation_id).
- Any `outbox.last_error` or high latency fields.

Notes
- Use real inbound messages; do not edit DB/trace to fabricate evidence.
- For outbox retries, the latest row reflects current status.
