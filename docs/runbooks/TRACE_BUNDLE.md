# Runbook: Trace Bundle

Purpose
- Single evidence bundle for one inbound message (decision_meta + decision_trace + outbox rows + timing).

When to use
- Live-check failures (missing_action, timeout, no reply).
- Outbox latency spikes (p90/p95) or PROCESSING backlog.
- Contract errors (outbox payload, action gate).

Command
```bash
python3 ops/diagnose.py trace-bundle \
  --client-slug demo_salon \
  --message-id "<CHATFLOW_MESSAGE_ID>" \
  --output /tmp/trace-bundle.json
```

Inputs
- `--message-id` (ChatFlow messageId), or
- `--message-uuid` (messages.id), or
- `--conversation-id`, or
- `--text` + `--minutes`, or
- `--receiver-phone` (auto-resolve client_slug)

What to read (quick map)
- `message.*` → correlation keys: `message_id`, `conversation_id`, `remote_jid`.
- `decision_meta.action/source/intent` → final decision.
- `decision_trace` → ordered stages (see `DECISION_STAGE_ORDER_SNAPSHOT`).
- `timing` (and `decision_meta.timing`) → pipeline timing + stage timings + outbox timing.
- `outbox.rows[].meta.timing` → worker timings (wait/process/total).
- `outbox.latency_ms` → inbound→outbox enqueue latency (derived).

Stage timing keys (timing.stages)
- `controller_llm_ms`, `multi_intent_llm_ms`, `rag_rewrite_llm_ms`, `rag_ms`, `knowledge_search_ms`.
- `dedup_ms`, `outbox_enqueue_ms`, `outbox_process_ms`, `send_ms`.

Correlation keys
- `message_id` → ChatFlow inbound id.
- `outbox_id` → outbox row id.
- `trace_id` → decision_meta trace id (propagates to timing/outbox logs).

Evidence to capture
- Trace-bundle JSON file path.
- 1–3 key fields from decision_meta/trace/outbox meta.
- CI run URL (if live-check involved).

Notes
- Do not edit DB/trace to fabricate evidence.
- If `decision_meta.action` missing → check `outbox_payload_guard` or `action_gate` stages.
- Stage order changes require updating `DECISION_STAGE_ORDER_SNAPSHOT` hash in `truffles-api/tests/test_outbox_payload_contract.py`.
