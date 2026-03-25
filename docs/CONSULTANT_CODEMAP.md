# Consultant Code Map (ChatGPT‑5‑like but controlled)

**Purpose:** fast onboarding for new devs/agents. Shows where the "brain" lives in code, what each block does, and how it shapes behavior.

**Canon refs:**
- `SPECS/CONSULTANT.md` — behavior rules, safety, multi‑intent, no‑hallucination.
- `SPECS/ARCHITECTURE.md` — decision graph & stage order (canon).
- `SPECS/SYSTEM_REFERENCE.md` — code‑accurate pipeline map + testing SOP.

---

## 0) New agent checklist (read-first)

- Read `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Debug message flow with `ops/diagnose.py explain` first, then `trace-bundle`, then logs.
- Work only in the assigned worktree/branch; do not switch branches mid-task.
- `demo_salon` is a canary pack; never add demo‑only rules or “pass‑tests” hacks.
- Prefer semantic resolver/LLM controller; do not expand dictionaries to chase coverage.
- Use `ops/diagnose.py` for live‑check evidence; never “massage” DB/trace.
- Keep process artifacts updated: session log + Task Package; `STATE.md` only by Brain.

---

## Capabilities Passport (full audit)

**Scope:** capabilities of the consultant + platform from `truffles-main` **and** external folders in `/home/zhan`
(infra/landing/media).  
**Evidence rule:** only treat as FACT when backed by code/contracts/tests/runbooks. Anything else = GAP.  
**Legend:** Facts/Code → Tests/Runbooks → Limits/GAP.

### A) Channels & transport
- **WhatsApp via ChatFlow webhook (primary inbound path).**
  - Facts/Code: `truffles-api/app/routers/webhook/http.py`, `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: `truffles-api/tests/test_message_endpoint.py`, `SPECS/SYSTEM_REFERENCE.md` (live-check SOP), `ops/diagnose.py`.
  - Limits/GAP: depends on external ChatFlow delivery; retries/outbox handle send, not provider outages.
- **Outbound guard (TEST_MODE + allowlist) for ChatFlow sends.**
  - Facts/Code: `truffles-api/app/services/chatflow_service.py` (`TEST_MODE`, `_should_skip_outbound`,
    `OUTBOUND_ALLOWLIST_JIDS`).
  - Tests/Runbooks: `truffles-api/tests/test_chatflow_contract.py`.
  - Limits/GAP: when `TEST_MODE=1`, non-allowlisted JIDs are skipped; misconfigured allowlist can look like silent drops.
- **Ingress preflight: payload parsing, webhook secret, branch-number block.**
  - Facts/Code: `truffles-api/app/routers/webhook/parsing.py`, `truffles-api/app/routers/webhook/http.py`,
    `truffles-api/app/routers/webhook/secrets.py`.
  - Tests/Runbooks: `truffles-api/tests/test_branch_routing_instance.py` (preflight media-only).
  - Limits/GAP: secret mismatch rejects inbound; branch sender is ignored to prevent bot-to-bot loops.
- **Service topology (shadow apps for scale).**
  - Facts/Code: `truffles-api/app/decision_core_app.py`, `truffles-api/app/inbox_service_app.py`,
    `truffles-api/app/outbox_service_app.py`, `truffles-api/app/knowledge_gateway_app.py`,
    `truffles-api/app/provider_gateway_app.py`.
  - Tests/Runbooks: `docs/runbooks/SENTINEL.md`, `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: shadow services may not be fully wired for all traffic.
- **Provider Gateway (shadow) for inbound/outbound/status.**
  - Facts/Code: `truffles-api/app/provider_gateway_app.py`, `truffles-api/app/routers/provider_gateway.py`,
    `truffles-api/app/adapters/provider_gateway.py`, `contracts/integrations/provider_inbound.v1.jsonschema`,
    `contracts/integrations/provider_outbound.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_provider_gateway_inbound.py`,
    `truffles-api/tests/test_provider_gateway_outbound.py`, `truffles-api/tests/test_provider_gateway_integration.py`.
  - Limits/GAP: runs as shadow/canary in some flows; not the only production ingress.
- **Provider status callbacks (delivery receipts → outbox status events).**
  - Facts/Code: `truffles-api/app/routers/provider_gateway.py`,
    `truffles-api/app/services/provider_gateway_service.py`,
    `contracts/events/provider_status.v1.jsonschema`,
    `truffles-api/app/models/outbox_status_event.py`.
  - Tests/Runbooks: `truffles-api/tests/test_provider_gateway_outbound.py`,
    `truffles-api/tests/test_provider_gateway_app.py`.
  - Limits/GAP: requires `PROVIDER_GATEWAY_STATUS_ENABLED` + token; relies on provider callbacks.
- **Provider inbox capture (durable events + dedupe).**
  - Facts/Code: `truffles-api/app/routers/provider_gateway.py`,
    `truffles-api/app/services/inbox_event_service.py`,
    `truffles-api/app/models/inbox_event.py`.
  - Tests/Runbooks: no direct tests for provider inbox; `truffles-api/tests/test_inbox_service_app.py` covers
    `record_inbox_event`.
  - Limits/GAP: gated by `PROVIDER_GATEWAY_INBOX_ENABLED` / `PROVIDER_GATEWAY_INBOX_REQUIRED`; dedupe is per
    `(client_id, provider, channel, provider_message_id)`; client_slug mismatch blocks persistence.
- **Telegram manager channel (handoff UI + buttons).**
  - Facts/Code: `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/services/telegram_service.py`,
    `truffles-api/app/services/escalation_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_telegram_webhook.py`, `truffles-api/tests/test_manager_message_rbac.py`.
  - Limits/GAP: outbound depends on configured bot_token/chat_id; allowlist required for live-check.

### B) Message integrity & batching (multi-message meaning)
- **Dedup by message_id (Redis + DB).**
  - Facts/Code: `truffles-api/app/routers/webhook/dedup.py`, `truffles-api/migrations/010_add_message_dedup.sql`.
  - Tests/Runbooks: `truffles-api/tests/test_webhook_dedup.py`.
  - Limits/GAP: if Redis unavailable, falls back to DB; dedup granularity is per message_id.
- **Debounce + buffer (combine burst messages into one text).**
  - Facts/Code: `truffles-api/app/routers/webhook/dedup.py` (`DEBOUNCE_*` env, buffer drain).
  - Tests/Runbooks: `truffles-api/tests/test_webhook_dedup.py`, `truffles-api/tests/test_state_service.py`.
  - Limits/GAP: requires Redis; window is short (seconds); off if `DEBOUNCE_ENABLED=0`.

### C) Conversation state & memory
- **State machine: bot_active / pending / manager_active + SLA auto-close.**
  - Facts/Code: `truffles-api/app/services/state_machine.py`, `truffles-api/app/routers/webhook/pending.py`.
  - Tests/Runbooks: `truffles-api/tests/test_state_service.py`, `docs/runbooks/INCIDENTS.md`.
  - Limits/GAP: pending semantics must be obeyed by all flows; see GAPs in `STATE.md` if violated.
- **Auto-heal broken handovers/topics (sentinel health checks).**
  - Facts/Code: `truffles-api/app/services/health_service.py`, `truffles-api/app/workers/sentinel.py`.
  - Tests/Runbooks: `truffles-api/tests/test_health_service.py`, `docs/runbooks/SENTINEL.md`.
  - Limits/GAP: auto-heal resets to `bot_active` and resolves stale handovers; does not fix root causes.
- **Session memory + re-entry + expected reply context.**
  - Facts/Code: `truffles-api/app/routers/webhook/context_manager.py`,
    `truffles-api/app/routers/webhook/session_memory.py`.
  - Tests/Runbooks: `truffles-api/tests/test_webhook_response.py`.
  - Limits/GAP: time-awareness partial (see `SPECS/CONSULTANT.md`), memory_profile gated by consent.
- **Opt-out / mute + re-engage confirmation.**
  - Facts/Code: `truffles-api/app/routers/webhook/guards.py`,
    `truffles-api/app/services/intent_service.py` (opt-out detection).
  - Tests/Runbooks: `truffles-api/tests/test_intent.py`, `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: re-engage window is time-bounded; in `pending/manager_active` opt-out has different semantics.

### D) LLM reasoning & routing
- **Intent classifier + dialogue controller (LLM for meaning).**
  - Facts/Code: `truffles-api/app/services/intent_service.py`, `prompts/intent_classifier.md`,
    `contracts/llm/dialogue_controller_output.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_intent.py`, `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: depends on LLM availability; offline fallback is rule-based.
- **Multi-intent decomposition + answer interpreter (slot extraction).**
  - Facts/Code: `truffles-api/app/services/ai_service.py`, `truffles-api/app/services/intent_service.py`,
    `contracts/llm/answer_interpreter_output.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: slot parsing failures in booking are tracked in `STATE.md`.
- **Hybrid LLM plan (plan → validate → tools → compose).**
  - Facts/Code: `prompts/llm_plan.md`, `contracts/llm/llm_plan_output.v1.jsonschema`,
    `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: in runtime, plan is invoked only when `expected_reply_type` is None (see `STATE.md` GAP).
- **LLM policy core (DEC‑023).**
  - Facts/Code: `contracts/llm/llm_policy_core_output.v1.jsonschema`, `prompts/llm_policy_core.md`.
  - Tests/Runbooks: `truffles-api/tests/test_llm_policy_core.py`.
  - Limits/GAP: not fully wired in runtime (explicit GAP in `STATE.md`).
- **LLM budget + cache.**
  - Facts/Code: `truffles-api/app/services/ai_service.py` (budget/caching).
  - Tests/Runbooks: `truffles-api/tests/test_ai_service.py`.
  - Limits/GAP: budgets configured per client; depletion triggers degradation.
- **LLM degradation + budget gates (fallback behavior).**
  - Facts/Code: `truffles-api/app/services/ai_service.py`,
    `truffles-api/app/routers/webhook/response.py` (degradation tracing).
  - Tests/Runbooks: `truffles-api/tests/test_ai_service.py`,
    `truffles-api/tests/test_demo_salon_eval.py`.
  - Limits/GAP: fallback depends on configured thresholds/timeouts; may reduce semantic quality.
- **Safety gates (Hard‑LAW / policy / OOD).**
  - Facts/Code: `truffles-api/app/routers/webhook/policy.py`,
    `truffles-api/app/routers/webhook/guards.py`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONSULTANT.md`.
  - Tests/Runbooks: `truffles-api/tests/test_demo_salon_eval.py`,
    `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: safety gates override LLM decisions; policy core wiring is incomplete (see `STATE.md`).
- **Behavioral shield (spam/toxic/nonsense drops or escalation).**
  - Facts/Code: `truffles-api/app/routers/webhook/shield.py`.
  - Tests/Runbooks: `truffles-api/tests/test_shield_trace_contract.py`.
  - Limits/GAP: shield skips replies in extreme cases; tuning depends on heuristics.
- **Router SLA tracking (fallback/timeout rate flag).**
  - Facts/Code: `truffles-api/app/routers/webhook/router_sla.py`,
    `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: none explicit; verify via decision_meta/trace in `ops/diagnose.py`.
  - Limits/GAP: in-memory counters reset on restart.

### E) Knowledge, packs, and business agnosticism
- **Pack-first facts (truth gate, policy, consult playbooks).**
  - Facts/Code: `truffles-api/app/services/demo_salon_knowledge.py`,
    `truffles-api/app/services/consult_pack_service.py`,
    `contracts/consult/consult_playbook.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_demo_salon_eval.py`,
    `docs/runbooks/DIALOG_REPORT.md`.
  - Limits/GAP: correctness for any niche depends on pack completeness; demo_salon is a canary pack;
    `_legacy` heuristics and demo adapter still exist, so full business-agnostic purity is not yet guaranteed.
- **Pack-Compiler + Policy/Signal DSL + Knowledge Snapshot.**
  - Facts/Code: `truffles-api/app/services/pack_compiler_service.py`,
    `contracts/policy/policy_bundle.v1.jsonschema`, `contracts/packs/signal_graph.v1.jsonschema`,
    `truffles-api/app/services/knowledge_snapshot_consumer.py`,
    `truffles-api/app/knowledge_gateway_app.py`.
  - Tests/Runbooks: `truffles-api/tests/test_pack_compiler.py`,
    `truffles-api/tests/test_policy_dsl.py`, `truffles-api/tests/test_knowledge_snapshot_gateway.py`.
  - Limits/GAP: RU/KZ variants not enforced by schema (see `STATE.md` GAP); safe-mode semantics conflict
    between `STRATEGY/REQUIREMENTS.md` and `docs/PROCESSES.md`.
- **RAG + semantic matching (Qdrant).**
  - Facts/Code: `truffles-api/app/services/knowledge_service.py`,
    `truffles-api/app/services/demo_salon_knowledge.py`.
  - Tests/Runbooks: `truffles-api/tests/test_knowledge_service.py`, `ops/check_qdrant.py`.
  - Limits/GAP: requires Qdrant + embeddings; low confidence falls back to clarify/handoff.
- **Knowledge backlog (capture missing facts + admin retrieval).**
  - Facts/Code: `truffles-api/app/routers/webhook/decision.py` (`_record_knowledge_backlog`),
    `truffles-api/app/routers/webhook/response.py`, `truffles-api/app/routers/admin.py` (`/admin/knowledge-backlog`).
  - Tests/Runbooks: none explicit; backlog path is exercised in `truffles-api/tests/test_message_endpoint.py`.
  - Limits/GAP: admin endpoint requires `ALERTS_ADMIN_TOKEN`; backlog accuracy depends on trace/meta flow.
- **Embedding service (BGE-M3) and ops helpers.**
  - Facts/Code: `ops/docker-compose-bge.yml`, `ops/start_bge_m3.sh`,
    `ops/test_bge.py`, `ops/test_full_flow.py`.
  - Tests/Runbooks: no formal tests; verify via ops scripts.
  - Limits/GAP: embedding service is external; failures degrade semantic retrieval.

### F) Consultant domain flows (info / consult / booking)
- **Info/truth flow (address, hours, pricing, duration).**
  - Facts/Code: `truffles-api/app/routers/webhook/info.py`,
    `truffles-api/app/services/demo_salon_knowledge.py`.
  - Tests/Runbooks: `truffles-api/tests/test_demo_salon_eval.py`.
  - Limits/GAP: depends on pack facts; missing facts → clarify/handoff.
- **Consult flow (pack-playbook only, controlled advice).**
  - Facts/Code: `truffles-api/app/routers/webhook/response.py`,
    `truffles-api/app/services/consult_pack_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_demo_salon_eval.py`, `docs/REPORTS/2026-01-24-consult-quality.md`.
  - Limits/GAP: no advice outside playbooks; consult snapshot in strict mode for allowlisted packs.
- **Booking flow (slot intake + confirm + tools).**
  - Facts/Code: `truffles-api/app/routers/webhook/booking.py`,
    `truffles-api/app/services/appointment_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_booking_appointments.py`,
    `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, `scripts/booking_confirm_verify.sh`.
  - Limits/GAP: booking dialog gaps (missing replies/unknown_state) recorded in `STATE.md`.
- **Response composition (ack + facts + next step).**
  - Facts/Code: `truffles-api/app/routers/webhook/response.py` (response composer).
  - Tests/Runbooks: `truffles-api/tests/test_webhook_response.py`.
  - Limits/GAP: requires pack variants to customize; otherwise defaults apply.
- **Branch selection + multi-branch routing.**
  - Facts/Code: `truffles-api/app/routers/webhook/branch_selection.py`,
    `contracts/tenancy/tenant_context.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_branch_routing_instance.py`.
  - Limits/GAP: requires branch data; without it, safe-mode may apply.

### G) Tools and calendar integration
- **Tool registry (calendar + catalog).**
  - Facts/Code: `truffles-api/app/services/tool_registry_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_booking_appointments.py`.
  - Limits/GAP: tool calls require correct pack refs; missing data leads to COLLECT/handoff.
- **Calendar sync + reminders.**
  - Facts/Code: `truffles-api/app/services/calendar_sync_service.py`,
    `truffles-api/app/services/appointment_reminder_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_calendar_provider_sync.py`,
    `truffles-api/tests/test_reminder_jobs.py`.
  - Limits/GAP: outbound calendar sync failed without OAuth tokens (see `STATE.md`).
- **Google Calendar OAuth (connect/callback/status) + console proxy callback.**
  - Facts/Code: `truffles-api/app/routers/calendar.py`, `truffles-api/app/services/google_calendar_service.py`,
    `console-web/src/app/api/calendar/callback/route.ts`.
  - Tests/Runbooks: `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
  - Limits/GAP: requires Google OAuth credentials + redirect URI; expired tokens block provider health.
- **Calendar inbound/outbound sync via outbox (sync_outbound/sync_inbound).**
  - Facts/Code: `truffles-api/app/services/calendar_sync_service.py`,
    `truffles-api/app/routers/webhook/outbox.py`, `truffles-api/app/workers/outbox.py`,
    `truffles-api/app/routers/outbox_service.py`, `truffles-api/app/routers/admin.py`.
  - Tests/Runbooks: `truffles-api/tests/test_calendar_provider_sync.py`,
    `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
  - Limits/GAP: inbound scheduling is env‑gated; outbox payload guards can block calendar events (see runbook GAP);
    conflicts may escalate to pending.

### H) Media & ASR
- **Media intake (photo/audio/document).**
  - Facts/Code: `truffles-api/app/routers/webhook/media.py`, `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: `truffles-api/tests/test_branch_routing_instance.py`,
    `truffles-api/tests/test_provider_gateway_outbound.py`.
  - Limits/GAP: video unsupported; size/rate limits apply; storage optional.
- **Media policy: type/size/rate limits + cleanup TTL + console upload limits.**
  - Facts/Code: `truffles-api/app/routers/webhook/media.py`, `truffles-api/app/routers/webhook/decision.py`,
    `truffles-api/app/routers/admin.py`, `truffles-api/app/services/manager_message_service.py`,
    `truffles-api/app/routers/console.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_media.py`, `docs/runbooks/DIALOG_REPORT.md`.
  - Limits/GAP: rate limiter falls back to in-memory if Redis is unavailable; cleanup is admin-triggered;
    console rejects video uploads.
- **Voice ASR (speech → text).**
  - Facts/Code: `truffles-api/app/routers/webhook/media.py`, `truffles-api/app/services/ai_service.py`.
  - Tests/Runbooks: no dedicated ASR test suite; verify via `ops/diagnose.py trace-bundle`.
  - Limits/GAP: low-confidence transcripts prompt for text; ASR depends on provider.
- **Style reference detection (photo in any dialog position).**
  - Facts/Code: `truffles-api/app/routers/webhook/media.py`, `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: covered indirectly in live-check media flow; runbook `docs/runbooks/DIALOG_REPORT.md`.
  - Limits/GAP: system auto-handoffs on reference; no user prompt “send to manager?” (it informs and proceeds).
- **Media forwarding to manager + signed URL TTL for outbound media.**
  - Facts/Code: `truffles-api/app/routers/webhook/media.py` (Telegram forward),
    `truffles-api/app/adapters/provider_gateway.py`, `contracts/integrations/media_send.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_provider_gateway_outbound.py`.
  - Limits/GAP: requires provider gateway media support; signed URL expiry must be valid.

### I) Escalation & manager workflow
- **Handover creation + pending/manager_active.**
  - Facts/Code: `truffles-api/app/services/escalation_service.py`,
    `truffles-api/app/services/state_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_escalation.py`, `docs/runbooks/SENTINEL.md`.
  - Limits/GAP: pending guard required; outbound manager replies rely on Telegram routing.
- **Manager messages to client (outbox).**
  - Facts/Code: `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/workers/outbox.py`.
  - Tests/Runbooks: `truffles-api/tests/test_manager_message_rbac.py`, `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: depends on outbox delivery + provider availability.
- **Manager callbacks (take/resolve/return/skip).**
  - Facts/Code: `truffles-api/app/services/callback_service.py`,
    `truffles-api/app/routers/telegram_webhook.py`.
  - Tests/Runbooks: `truffles-api/tests/test_callback.py`, `truffles-api/tests/test_telegram_webhook.py`.
  - Limits/GAP: callbacks rely on correct handover state; invalid state rejects action.
- **Telegram callback dedup (prevents double-processing).**
  - Facts/Code: `truffles-api/app/services/callback_dedup.py`, `truffles-api/app/routers/telegram_webhook.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: in-memory TTL only; not shared across workers or restarts.
- **Pending SLA reminders + auto-close + no-response alerts.**
  - Facts/Code: `truffles-api/app/services/reminder_service.py`, `truffles-api/app/services/alert_service.py`,
    `truffles-api/app/models/alert_event.py`.
  - Tests/Runbooks: `truffles-api/tests/test_reminders.py`, `truffles-api/tests/test_reminder_jobs.py`.
  - Limits/GAP: depends on scheduled workers; alert thresholds are env-driven.

### J) Outbox, inbox, and delivery guarantees
- **Outbox pipeline + idempotency + status events.**
  - Facts/Code: `truffles-api/app/routers/webhook/outbox.py`, `truffles-api/app/workers/outbox.py`,
    `truffles-api/app/models/outbox_status_event.py`.
  - Tests/Runbooks: `truffles-api/tests/test_outbox_payload_contract.py`,
    `truffles-api/tests/test_outbox_worker_settings.py`, `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: delivery failures handled with alerts; provider outages still cause FAILED statuses.
- **Auto-heal for stuck PROCESSING (release stale processing).**
  - Facts/Code: `truffles-api/app/services/outbox_service.py`,
    `truffles-api/app/workers/outbox.py`.
  - Tests/Runbooks: none explicit; verify via outbox status events.
  - Limits/GAP: relies on worker cadence and configured backoff.
- **Durable inbox events (shadow service).**
  - Facts/Code: `truffles-api/app/routers/inbox_service.py`, `contracts/events/inbox_event.v1.jsonschema`.
  - Tests/Runbooks: `truffles-api/tests/test_inbox_service_app.py`.
  - Limits/GAP: shadow path; not all traffic routed through it yet.
- **Inbox Service shadow endpoint (/inbox/event + token gate).**
  - Facts/Code: `truffles-api/app/inbox_service_app.py`, `truffles-api/app/routers/inbox_service.py`,
    `truffles-api/app/services/inbox_event_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_inbox_service_app.py`.
  - Limits/GAP: requires `INBOX_SERVICE_ENABLED`; token optional but recommended; duplicate detection is per provider_message_id.
- **Outbox Service shadow endpoint (/outbox/process + token gate).**
  - Facts/Code: `truffles-api/app/outbox_service_app.py`, `truffles-api/app/routers/outbox_service.py`,
    `truffles-api/app/services/outbox_service.py`, `truffles-api/app/services/calendar_sync_service.py`,
    `truffles-api/app/services/appointment_reminder_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_outbox_service_app.py`, `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: requires `OUTBOX_SERVICE_ENABLED`; optional token; schedules inbound calendar syncs and reminders
    but does not fix provider outages.

### K) Observability & monitoring
- **decision_trace + decision_meta (audit trail).**
  - Facts/Code: `truffles-api/app/routers/webhook/trace.py`, `SPECS/SYSTEM_REFERENCE.md`.
  - Tests/Runbooks: `docs/runbooks/TRACE_BUNDLE.md`, `ops/diagnose.py`.
  - Limits/GAP: evidence must come from real inbound rows; do not modify DB for “clean” traces.
- **Trace retention + contract validation (fact/action/response).**
  - Facts/Code: `truffles-api/app/routers/webhook/trace.py`,
    `truffles-api/app/contracts/decision.py`.
  - Tests/Runbooks: `truffles-api/tests/test_webhook_trace.py`.
  - Limits/GAP: contract trace is informational; does not auto-correct behavior.
- **Admin health + env contract checks.**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `truffles-api/app/services/health_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_admin_health.py`.
  - Limits/GAP: health reflects configured env/pack validation; does not guarantee provider uptime.
- **OTel/Tempo + alerts.**
  - Facts/Code: `truffles-api/app/logging_config.py`, `truffles-api/app/workers/sentinel.py`,
    `/home/zhan/infrastructure/tempo.yml`, `/home/zhan/infrastructure/prometheus.yml`,
    `/home/zhan/infrastructure/alertmanager.yml`.
  - Tests/Runbooks: `docs/runbooks/SENTINEL.md`, `docs/runbooks/INCIDENTS.md`.
  - Limits/GAP: monitoring stack lives outside repo; config drift possible.
- **Audit events (console actions).**
  - Facts/Code: `truffles-api/app/services/audit_service.py`, `truffles-api/app/models/__init__.py`,
    `truffles-api/app/routers/console.py`.
  - Tests/Runbooks: none explicit; verify via DB and console actions.
  - Limits/GAP: audit logging depends on callers recording events.

### L) Testing & evaluation harness
- **Core pytest suites (backend).**
  - Facts/Code: `truffles-api/tests/*`, `scripts/test_api_container.sh`.
  - Tests/Runbooks: `SPECS/SYSTEM_REFERENCE.md` (test design).
  - Limits/GAP: container vs local drift exists; follow test-compose SOP.
- **Dialog analysis + chaos simulation.**
  - Facts/Code: `ops/diagnose.py`, `ops/shadow_replay.py`.
  - Tests/Runbooks: `docs/runbooks/DIALOG_REPORT.md`, `docs/runbooks/CHAOS_SIM.md`.
  - Limits/GAP: LLM outcomes are evaluated via trace/meta (not raw text).
- **Booking quality runner (LLM state-aware).**
  - Facts/Code: `ops/diagnose.py` (llm-quality), `ops/results/booking_quality.json`.
  - Tests/Runbooks: `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
  - Limits/GAP: baseline currently shows low pass-rate; semantics require separate review.
- **Console API contract testing (Schemathesis).**
  - Facts/Code: `contracts/console_api/openapi.v1.yaml`,
    `contracts/console_api/schemathesis.toml`.
  - Tests/Runbooks: `contracts/console_api/README.md`.
  - Limits/GAP: requires valid auth token and running console API.

### M) Control Plane (Console UI + API)
- **Console UI (Inbox, Cases, Settings, Analytics, Provisioning).**
  - Facts/Code: `console-web/src/app/*`, `docs/CONSOLE_AUDIT/INDEX.md`.
  - Tests/Runbooks: `console-web/e2e/*`, `docs/CONSOLE_AUDIT/*`.
  - Limits/GAP: some features are P1/P2 per `STRATEGY/REQUIREMENTS.md`.
- **Calendar console UI + API (specialists/slots/bookings/create/cancel).**
  - Facts/Code: `truffles-api/app/routers/calendar.py`,
    `console-web/src/app/calendar/page.tsx`, `console-web/src/app/team/page.tsx`,
    `console-web/src/lib/api-client.ts`.
  - Tests/Runbooks: `console-web/e2e/smoke.spec.ts`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
  - Limits/GAP: no dedicated backend tests for calendar router; console supports create/cancel but not reschedule/edit;
    access gated by calendar RBAC.
- **Telegram connector (health/verify/test + thread links).**
  - Facts/Code: `truffles-api/app/routers/console.py`, `truffles-api/app/services/telegram_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_telegram_connector.py`,
    `truffles-api/tests/test_console_telegram_helpers.py`.
  - Limits/GAP: requires bot token + chat id; verify/test depend on Telegram availability.
- **Case lifecycle (list/take/resolve/return) + SLA indicators.**
  - Facts/Code: `truffles-api/app/routers/console.py`, `truffles-api/app/services/state_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_cases_helpers.py`.
  - Limits/GAP: actions are RBAC-bound; only assigned agent or owner/admin can resolve/return.
- **Inbox macros (personal/team canned replies).**
  - Facts/Code: `truffles-api/app/routers/console.py`, `truffles-api/app/models/console_macro.py`,
    `console-web/src/components/InboxMacros.tsx`.
  - Tests/Runbooks: `truffles-api/tests/test_console_inbox_macros.py`.
  - Limits/GAP: text-only macros; no variable templating.
- **Console API + RBAC.**
  - Facts/Code: `truffles-api/app/routers/console.py`,
    `contracts/console_api/openapi.v1.yaml`, `SPECS/CONTROL_PLANE.md`.
  - Tests/Runbooks: `truffles-api/tests/test_console_*`.
  - Limits/GAP: requires correct OIDC mapping and agent identities.
- **Ops outbox queue (list + retry failed).**
  - Facts/Code: `truffles-api/app/routers/console.py` (`/ops/outbox`, `/ops/outbox/retry`).
  - Tests/Runbooks: `truffles-api/tests/test_console_outbox_ops.py`, `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: retries only requeue failed items; does not fix provider outages.
- **Destructive action confirmations (knowledge rollback, branch deactivate).**
  - Facts/Code: `truffles-api/app/services/console_confirmations.py`,
    `truffles-api/app/routers/console.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_confirmations.py`.
  - Limits/GAP: TTL-bound; only owner/admin can request; mismatches reject the action.
- **Console auth + agent identity mapping (OIDC).**
  - Facts/Code: `truffles-api/app/services/console_auth.py`,
    `truffles-api/app/models/agent_identity.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_auth_access.py`.
  - Limits/GAP: misconfigured identities lead to access denial or client-selection required.
- **Agent link tokens (Telegram deep-link binding).**
  - Facts/Code: `truffles-api/app/services/agent_link_service.py`, `truffles-api/app/models/agent_link_token.py`,
    `truffles-api/app/routers/console.py`, `truffles-api/app/routers/telegram_webhook.py`.
  - Tests/Runbooks: `truffles-api/tests/test_agent_link_service.py`.
  - Limits/GAP: short-lived single-use tokens; requires configured Telegram bot username.
- **Analytics snapshots (metrics_daily).**
  - Facts/Code: `truffles-api/app/services/metrics_daily_service.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_analytics.py`.
  - Limits/GAP: relies on scheduled worker cadence and outbox status events.

### N) Multi-tenant onboarding & safety gates
- **Tenant/branch + onboarding state machine.**
  - Facts/Code: `truffles-api/app/services/onboarding_state.py`,
    `truffles-api/app/models/branch.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_onboarding_state.py`.
  - Limits/GAP: onboarding automation TODO in `STATE.md`.
- **Platform admin provisioning (company/client updates + tenant validation).**
  - Facts/Code: `truffles-api/app/routers/console.py`, `truffles-api/app/schemas/console.py`.
  - Tests/Runbooks: `truffles-api/tests/test_console_admin_provisioning.py`,
    `truffles-api/tests/test_console_provisioning_validation.py`.
  - Limits/GAP: platform_admin role required; client slug must be unique.
- **Capabilities contract (channels/providers/features).**
  - Facts/Code: `truffles-api/app/services/capabilities_service.py`,
    `contracts/capabilities/capabilities.v1.jsonschema`.
  - Tests/Runbooks: none explicit; validate via console API contract tests.
  - Limits/GAP: requires correct provisioning data; does not enforce behavior by itself.
- **Minimum Data Contract + safe-mode gate.**
  - Facts/Code: `truffles-api/app/services/knowledge_validation.py`,
    `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: `truffles-api/tests/test_minimum_data_contract.py`,
    `truffles-api/tests/test_safe_mode_gate.py`.
  - Limits/GAP: safe-mode semantics conflict noted in `STATE.md`.

### O) Learning, consent, and data governance
- **Learning consent + pack candidates approval.**
  - Facts/Code: `truffles-api/app/services/learning_service.py`,
    `truffles-api/app/services/learned_response_service.py`,
    `truffles-api/migrations/018_add_learning_consent_pack_candidates.sql`.
  - Tests/Runbooks: `truffles-api/tests/test_learning_service.py`.
  - Limits/GAP: only works for consented data; retention governed by policy.
- **Learning anonymization (PII redaction for phone/email/card).**
  - Facts/Code: `truffles-api/app/services/learning_service.py`,
    `truffles-api/app/services/learned_response_service.py`,
    `truffles-api/app/routers/admin.py` (anonymization mode).
  - Tests/Runbooks: `truffles-api/tests/test_learning_service.py`.
  - Limits/GAP: redaction applies only to learning payloads, not to live replies.

### P) External assets & infra (outside repo)
- **Infra stack (traefik, postgres, redis, qdrant, prometheus/grafana/tempo).**
  - Facts/Code: `/home/zhan/infrastructure/docker-compose.truffles.yml`,
    `/home/zhan/infrastructure/prometheus.yml`, `/home/zhan/infrastructure/tempo.yml`.
  - Tests/Runbooks: no repo tests; ops validation via infra logs.
  - Limits/GAP: non-canonical vs repo; drift risk across environments.
- **Automation/admin services (n8n, pgadmin).**
  - Facts/Code: `/home/zhan/infrastructure/docker-compose.truffles.yml`.
  - Tests/Runbooks: none in repo; validate via service health and logs.
  - Limits/GAP: not part of core runtime; availability depends on infra ops.
- **Landing sites (truffles.kz).**
  - Facts/Code: `/home/zhan/infrastructure/frontend/*`, `/home/zhan/landing-website/*`,
    `/home/zhan/truffles-landing/*`.
  - Tests/Runbooks: none in repo; deploy evidence tracked in `STATE.md`.
  - Limits/GAP: multiple sources; confirm which is deployed before changes.
- **Local media storage.**
  - Facts/Code: `/home/zhan/truffles-media/*` (stored assets), `truffles-api/app/routers/webhook/media.py`.
  - Tests/Runbooks: provider gateway media tests cover signed URLs.
  - Limits/GAP: storage path is local; not portable across hosts.
- **Non-canonical code copies (for awareness).**
  - Facts/Code: `/home/zhan/WebDev-Truffles-AI-Employee/console-web`, `/home/zhan/truffles-api/app`.
  - Tests/Runbooks: none; treat as non-source-of-truth vs `truffles-main`.
  - Limits/GAP: risk of drift if edited outside the canonical repo.

### Q) Language handling (RU/KZ)
- **RU/KZ signal lexicons and language list in packs.**
  - Facts/Code: `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`,
    `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`,
    `truffles-api/app/routers/webhook/decision.py` (language preference detection).
  - Tests/Runbooks: none specific; covered indirectly in evals.
  - Limits/GAP: RU/KZ variants for all user-facing strings not enforced (explicit GAP in `STATE.md`).

### R) Simulation & test-mode controls
- **Simulation metadata on inbound/outbound (mode/id/llm/time).**
  - Facts/Code: `truffles-api/app/schemas/webhook.py`, `truffles-api/app/schemas/outbox_payload.py`,
    `truffles-api/app/services/state_service.py`, `truffles-api/app/routers/webhook/decision.py`.
  - Tests/Runbooks: `docs/runbooks/CHAOS_SIM.md`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, `ops/diagnose.py`.
  - Limits/GAP: fields are optional; missing simulation flags use real routing and can send outbound messages.
- **Simulation-aware manager/outbox handling (no real send).**
  - Facts/Code: `truffles-api/app/services/escalation_service.py`,
    `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/routers/telegram_webhook.py`,
    `truffles-api/app/routers/webhook/outbox.py`.
  - Tests/Runbooks: `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
  - Limits/GAP: simulation markers are best-effort; no explicit tests for multi-worker behavior.
- **LLM gating + simulated time (offline datetime parsing).**
  - Facts/Code: `truffles-api/app/services/ai_service.py` (`_simulation_llm_allowed`),
    `truffles-api/app/services/state_service.py` (simulation_time),
    `truffles-api/app/routers/webhook/decision.py` (`get_simulation_time`).
  - Tests/Runbooks: `docs/TASK_PACKAGES/TP-2026-01-25-sim-time-override.md`, `ops/diagnose.py`.
  - Limits/GAP: LLM is skipped unless `simulation_llm=true`; time override only applies when simulation_time is present.
- **Owner/Admin consultant verification compare override.**
  - Facts/Code: `truffles-api/app/services/console_consultant_verification.py` (`run_consultant_verification_compare`),
    `truffles-api/app/services/knowledge_runtime.py` (`set_runtime_truth_override`, `build_runtime_truth_from_payload`).
  - Tests/Runbooks: `truffles-api/tests/test_console_consultant_verification_api.py`.
  - Limits/GAP: compare currently runs one prompt/finding at a time; publish gate depends on a recent compare proof for the saved branch draft.

### S) Admin & ops endpoints (non-console)
- **Admin token gate (X-Admin-Token / ALERTS_ADMIN_TOKEN).**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `truffles-api/app/routers/alerts.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: missing token returns 401/500; endpoints are not public-safe.
- **Prompt management (per-client system prompt).**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `truffles-api/app/models/prompt.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: update requires admin token; validation is length-only.
- **Client settings (mute/reminder, branch resolution, manager scope, auto-approve roles, learning settings).**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `truffles-api/app/models/client_settings.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: values are validated by ranges/enums; misconfiguration changes runtime behavior.
- **Manual outbox processing + release stale + calendar inbound sync.**
  - Facts/Code: `truffles-api/app/routers/admin.py`,
    `truffles-api/app/services/outbox_service.py`, `truffles-api/app/services/calendar_sync_service.py`.
  - Tests/Runbooks: `docs/runbooks/OUTBOX.md`.
  - Limits/GAP: requires admin token; does not fix provider outages.
- **Media cleanup (TTL).**
  - Facts/Code: `truffles-api/app/routers/admin.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: destructive without `dry_run`; uses local storage path.
- **Metrics daily snapshot/backfill + metrics read.**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `truffles-api/app/services/metrics_daily_service.py`,
    `ops/metrics_daily_snapshot.sql`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: backfill capped by env; requires admin token.
- **Version info endpoint (/admin/version).**
  - Facts/Code: `truffles-api/app/routers/admin.py`, `.github/workflows/monitor-prod-version.yml`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: relies on build-time env values.
- **Alerts test endpoint (/alerts/test).**
  - Facts/Code: `truffles-api/app/routers/alerts.py`, `truffles-api/app/services/alert_service.py`.
  - Tests/Runbooks: none explicit.
  - Limits/GAP: requires admin token + Telegram alert bot config.

---

## 0) E2E inbound message flow (code-accurate, with LLM touchpoints)

This is the full WA/ChatFlow inbound path in code order. Every step is traced in `decision_trace` unless a
preflight reject happens before a conversation is resolved.

1) Ingress (ChatFlow webhook)
   - Direct: `POST /webhook/{client_slug}` → `handle_webhook_direct` → `_parse_webhook_request` → `_handle_webhook_payload`.
     `truffles-api/app/routers/webhook/http.py:288`, `truffles-api/app/routers/webhook/parsing.py:118`,
     `truffles-api/app/routers/webhook/decision.py:3474`
   - Legacy wrapper: `POST /webhook` → `handle_webhook` → `_handle_webhook_payload`.
     `truffles-api/app/routers/webhook/http.py:323`, `truffles-api/app/routers/webhook/decision.py:3474`
   - Internal API: `POST /message` builds a `WebhookRequest` and calls the same pipeline.
     `truffles-api/app/routers/message.py:16`, `truffles-api/app/routers/message.py:37`

2) Preflight (rejects before any LLM)
   - Validates client/secret/remoteJid and blocks sender=branch numbers (anti bot‑to‑bot loop).
     `truffles-api/app/routers/webhook/http.py:53`

3) Dedupe + persist
   - `_handle_dedup_gate` (drop duplicates) → `get_or_create_user` → `get_or_create_conversation` →
     `save_message`.
     `truffles-api/app/routers/webhook/decision.py:3820`, `truffles-api/app/routers/webhook/decision.py:3843`,
     `truffles-api/app/routers/webhook/decision.py:3853`, `truffles-api/app/routers/webhook/decision.py:3898`

4) Context contract + decision graph snapshot
   - Context contract recorded before domain logic; decision plan stages are written to trace.
     `truffles-api/app/routers/webhook/decision.py:3922`

5) Media + ASR (only when media present)
   - Voice ASR: `_maybe_transcribe_voice` → `transcribe_audio_with_fallback`, text replaced with transcript.
     `truffles-api/app/routers/webhook/decision.py:3960`, `truffles-api/app/routers/webhook/media.py:371`,
     `truffles-api/app/services/ai_service.py:799`
   - Media‑only early reply (no LLM): `media_only` stage.
     `truffles-api/app/routers/webhook/decision.py:5172`

6) Early gates (safety first, before LLM response)
   - Debounce gate: `truffles-api/app/routers/webhook/decision.py:5199`
   - Handover confirmation gate: `truffles-api/app/routers/webhook/decision.py:5220`
   - Hard‑LAW gate: `truffles-api/app/routers/webhook/decision.py:5261`
   - Policy gates (discount/payment info) live in `truffles-api/app/routers/webhook/policy.py` and are called
     from `decision.py`.

7) Intent decomposition (LLM for meaning, not facts)
   - Multi‑intent + intent decomposition trace: `_run_intent_decomposition`.
     `truffles-api/app/routers/webhook/decision.py:886`, `truffles-api/app/routers/webhook/decision.py:5282`

8) LLM policy core (DEC‑023 target state)
   - LLM decides action/slots/next_question; safety code only validates schema + enforces hard safety.

9) Domain flows (tool execution after LLM decision)
   - Booking/info/consult flows are executed as tools chosen by the LLM policy core.
     `truffles-api/app/routers/webhook/booking.py`, `truffles-api/app/routers/webhook/info.py`,
     `truffles-api/app/routers/webhook/response.py`
   - LLM response (`_handle_llm_primary`) is used when action=reply and no tool output is required.

10) Outbox delivery
    - Outbox enqueue + send happens after response creation.
      `truffles-api/app/routers/webhook/outbox.py`

11) Observability (trace/meta are the audit trail)
    - `decision_trace` + `decision_meta` are written by `truffles-api/app/routers/webhook/trace.py`.
    - `timing.stages` shows LLM/RAG timings (e.g., `controller_llm_ms`, `multi_intent_llm_ms`,
      `rag_rewrite_llm_ms`, `rag_ms`).

### LLM call map (what runs where)

**LLM for meaning (router/slots):**
- Intent classifier: `_detect_intent_signals` → `classify_intent`.
  `truffles-api/app/routers/webhook/decision.py:370`, `truffles-api/app/services/intent_service.py:462`
- Dialogue controller (LLM‑router): `_build_router_state` → `route_dialogue_controller`.
  `truffles-api/app/routers/webhook/decision.py:1408`, `truffles-api/app/services/intent_service.py:543`
- Multi‑intent decomposition: `detect_multi_intent` (+ optional `rewrite_for_service_match`).
  `truffles-api/app/routers/webhook/decision.py:933`, `truffles-api/app/services/ai_service.py:1212`,
  `truffles-api/app/services/ai_service.py:980`
- Booking slot extraction (answer interpreter): `interpret_expected_reply` → `slot_extract` trace.
  `truffles-api/app/routers/webhook/decision.py:605`, `truffles-api/app/services/intent_service.py:849`

**LLM for language (RAG + response generation):**
- RAG rewrite: `_ensure_rag_rewrite` → `rewrite_query_for_retrieval`.
  `truffles-api/app/routers/webhook/response.py:337`, `truffles-api/app/services/ai_service.py:1093`
- Primary answer: `_handle_llm_primary` → `generate_bot_response` → `generate_ai_response`.
  `truffles-api/app/routers/webhook/decision.py:6583`, `truffles-api/app/routers/webhook/response.py:1073`,
  `truffles-api/app/services/message_service.py:104`, `truffles-api/app/services/ai_service.py:1948`
- Consult fallback (no playbook): `generate_consult_advice`.
  `truffles-api/app/routers/webhook/response.py:686`, `truffles-api/app/services/ai_service.py:2265`
- Service semantic rewrite: `rewrite_for_service_match` (used when semantic match misses).
  `truffles-api/app/routers/webhook/response.py:1618`, `truffles-api/app/services/ai_service.py:980`

**LLM provider (real HTTP calls):**
- Provider resolution: `get_llm_provider`.
  `truffles-api/app/services/ai_service.py:452`
- Chat completions: `OpenAIProvider.generate`.
  `truffles-api/app/services/llm/openai_provider.py:20`
- ASR transcription: `OpenAIProvider.transcribe_audio`.
  `truffles-api/app/services/llm/openai_provider.py:74`

### Live demo trace (demo_salon) — evidence

**Note:** `demo_salon` is a canary pack used for examples/evidence only. If you have another pack,
use its `client_slug`. Never tailor logic to `demo_salon`.

**How it was run (per Live‑check SOP):**
```bash
python3 ops/diagnose.py send-and-explain \
  --instance-id "eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6IkNsZWFuIn0=" \
  --jid "77055740455@s.whatsapp.net" \
  --receiver-phone "+77055740455" \
  --client-slug demo_salon \
  --text "Почему у вас дороже, чем в соседнем салоне?" \
  --marker-prefix "LC-LLM-FLOW"

python3 ops/diagnose.py trace-bundle \
  --client-slug demo_salon \
  --text "LC-LLM-FLOW-20260125-221234" \
  --output /tmp/trace_bundle_llm_flow.json
```

**Trace bundle (file):** `/tmp/trace_bundle_llm_flow.json`

**Correlation keys:**
- `message_id`: `3EB0A592AF3A16118E2548`
- `message_uuid`: `7bca8319-bb60-4d86-966a-67d1f42c1437`
- `conversation_id`: `10049e90-5805-425f-841b-c0c9419c9c30`
- `trace_id`: `61153e870b649ef07128a3264e757343`
- `remote_jid`: `77785890765@s.whatsapp.net`

**decision_meta (result):**
- `action=reply`
- `source=truth_gate`
- `intent=objection_price`
- `llm_used=false` (response not generated by LLM)
- `rag_reason=overridden_by_gate`

**Stages for this inbound (filtered by recorded_at around message time):**
- `decision_graph` → `data`
- `decision_graph` → `action`
- `decision_graph` → `response`
- `decision_graph` → `update`
- `intent_decomposition` (multi_intent=false)
- `context_manager` → `current_goal`
- `session_memory` → `update`
- `context_manager` → `summary_updated`
- `truth_gate` → `reply` (intent=objection_price)
- `fact_resolver` → `missing`
- `contract` → `fact`
- `contract` → `action`
- `contract` → `response`

**LLM timing evidence (routing/meaning LLM):**
- `controller_llm_ms=2805.17`
- `multi_intent_llm_ms=1511.85`

**Outbox evidence:**
- `outbox_id`: `39f2759c-f445-427f-9800-ed8a6dd65083`
- `status`: `SENT`
- `outbox.latency_ms.inbound_to_outbox_ms=10541.99`

**Interpretation:** this message hit a safety gate (hard policy/LAW) while still using LLM for routing
(`controller_llm_ms`, `multi_intent_llm_ms`). Under DEC‑023, only hard safety gates can override the
LLM policy decision; all other replies remain LLM‑driven.

## 1) Entry point & decision graph (the brain orchestrator)

**Code:** `truffles-api/app/routers/webhook/decision.py` (`_handle_webhook_payload`).

**Responsibility:**
- Accept inbound message, enrich with context, run gates, choose action (reply/escalate/booking_prompt), and record `decision_meta`/`decision_trace`.

**Behavior impact:**
- **Order matters.** Only hard safety gates (LAW/policy/schema) may override LLM policy decisions.
- If you change stage order, you change bot behavior. See `SPECS/SYSTEM_REFERENCE.md` → “Decision pipeline”.

## 1.1) Ingress adapters (ChatFlow + Provider Gateway)

**ChatFlow webhook**
- `truffles-api/app/routers/webhook/http.py` → `/webhook` + `/webhook/{client_slug}`
- Normalizes payload and calls `_handle_webhook_payload`.

**Provider Gateway (shadow)**
- `truffles-api/app/routers/provider_gateway.py` → `POST /provider/inbound` (gated by `PROVIDER_GATEWAY_INBOUND_ENABLED`)
- Validates `ProviderInbound`, translates to `WebhookRequest` via `truffles-api/app/services/provider_gateway_service.py`,
  then calls the same `_handle_webhook_payload`.
- If `PROVIDER_GATEWAY_INBOX_ENABLED=1`, the inbound handler records a durable `inbox_events` row
  before passing control to the webhook pipeline.

---

## 2) Gates & safety (hard control layer)

**Code blocks:**
- Pending/state gates: `truffles-api/app/routers/webhook/pending.py`, `decision.py`
- Policy/LAW: `truffles-api/app/routers/webhook/policy.py` + policy pack (data)
- Shield (spam/toxic/noise): `truffles-api/app/routers/webhook/shield.py`
- Media gate: `truffles-api/app/routers/webhook/media.py`

**Behavior impact:**
- **Pending/manager_active**: always respond with pending status; ignore booking/info/consult until resolved.
- **Policy/LAW**: escalates for payment/refund/complaint/medical; no advice.
- **Shield**: drop or escalate on abusive or noisy input.

---

## 3) Meaning extraction (LLM controller + routing)

**Code blocks:**
- Intent + class router: `decision.py` (intent_decomp, class_router)
- Multi‑intent queue: `decision.py` (`_set_intent_queue` etc.)

**Behavior impact:**
- LLM/controller decides *meaning* (intent/classes/slots), not facts.
- Router selects **info / consult / booking / handoff**.
- Multi‑intent is allowed, but **goal is preserved** (booking stays active, consult answers can be appended).

---

## 4) Knowledge + truth (facts only from packs/tools)

**Code blocks:**
- Domain facts + service availability: `truffles-api/app/services/demo_salon_knowledge.py` (current canary implementation)
- Truth pack (facts/policy): `truffles-api/app/knowledge/<client_slug>/SALON_TRUTH.yaml`
- Consult playbooks (care advice): `truffles-api/app/knowledge/<client_slug>/CONSULT_PLAYBOOK.yaml`
- Knowledge Snapshot Gateway (shadow): `truffles-api/app/routers/knowledge_gateway.py` + `truffles-api/app/services/knowledge_snapshot_service.py`
- Consult contracts: `truffles-api/app/schemas/consult.py` (runtime validation), `contracts/consult/consult_playbook.v1.jsonschema`
- Generic pack scaffold (CI/tests): `truffles-api/app/knowledge/generic/*`
- EVAL cases: `truffles-api/app/knowledge/demo_salon/EVAL.yaml`

**Behavior impact:**
- **No hallucinations:** facts only from `client_pack`/`consult_playbooks`.
- If service is not offered → explicit **"не оказываем"** reply (`service_not_found`).
- Packs define behavior; do not hardcode logic for `demo_salon`.

---

## 5) Domain flows (info/consult/booking)

**Booking**
- `truffles-api/app/routers/webhook/booking.py`
- Handles `expected_reply_type` (service/time/name), booking slots, booking interrupts.

**Info**
- `truffles-api/app/routers/webhook/info.py`
- Info bundle aggregation (address/hours/parking/etc). Keeps class carryover.

**Consult (pack-first, domain-agnostic)**
- Entry point: `truffles-api/app/routers/webhook/response.py` → `_handle_consult_flow`
- Pack load + schema validate: `truffles-api/app/services/consult_pack_service.py` (load/validate) + `truffles-api/app/schemas/consult.py`
- Snapshot consumer: `truffles-api/app/services/knowledge_snapshot_consumer.py` builds/validates consult playbook from snapshot and records `consult_snapshot` trace. Shadow mode is gated by `KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED`; cutover uses `KNOWLEDGE_SNAPSHOT_CONSULT_MODE` + `KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST` (fallback/strict).
- Topic resolver: `truffles-api/app/services/knowledge_service.py` → `resolve_consult_topic_candidates`
- LLM controller (topic select JSON): `truffles-api/app/services/ai_service.py` → `generate_consult_controller_output`
- Playbook first; LLM advice only for general beauty care and non‑medical topics (legacy fallback only when no pack decision).

**Behavior impact:**
- Booking keeps goal across interruptions; consult replies can be returned with booking follow‑up.
- Consult does **not** override booking goal when booking is active.
- Consult contract is domain‑agnostic: topics and allowed advice come from pack schema, not dictionaries.
  Implementation plan: `docs/TASK_PACKAGES/TP-2026-01-26-consult-agnostic-implementation.md`.

**Consult schema (canon):**
- Pack schema: `contracts/consult/consult_playbook.v1.jsonschema` (topics, allowed_advice, required_questions, risk).
- LLM output contract: `contracts/consult/consult_controller_output.v1.jsonschema` (intent, topic_id, confidence, risk_class, actions).
- Topic resolver: semantic retrieval over pack topics → Top‑K candidates → LLM selects `topic_id` (no phrase dictionaries).
- Response guard: answer only from `allowed_advice` + pack/tool facts; otherwise clarify or handoff.

---

## 6) LLM usage + RAG (language & retrieval)

**Code blocks:**
- LLM + rewrite: `truffles-api/app/services/ai_service.py`
- Consult controller (LLM JSON for topic/intent): `truffles-api/app/services/ai_service.py`
- RAG/embeddings: `truffles-api/app/services/knowledge_service.py` + Qdrant
- Response composition/guard: `truffles-api/app/routers/webhook/response.py`

**Behavior impact:**
- LLM provides *meaning/wording*, not facts.
- RAG retrieves supporting facts; response guard enforces policy and output shape.
- Consult controller output is validated against the schema contract before commit.

---

## 7) Memory & context (goal preservation)

**Code blocks:**
- Context manager: `truffles-api/app/routers/webhook/context_manager.py`
- Session memory: `truffles-api/app/routers/webhook/session_memory.py`

**Behavior impact:**
- Maintains `current_goal`, `expected_reply_type`, carryover (info_bundle, service). Keeps goal 10–15 turns.
- When booking goal is active, consult answers are appended without resetting goal.

---

## 8) Escalation + manager handoff

**Code blocks:**
- Escalation flow: `truffles-api/app/routers/webhook/pending.py`, `truffles-api/app/services/escalation_service.py`
- Manager actions: `truffles-api/app/services/manager_message_service.py`

**Behavior impact:**
- Always transparent status: pending → manager_active → resolved → bot_active.
- Handoff is a product feature; not a failure.

---

## 9) Outbox & delivery

**Code blocks:**
- Outbox enqueue + send: `truffles-api/app/routers/webhook/outbox.py`, workers in `truffles-api/app/workers/*`

**Behavior impact:**
- Idempotent sends; retries; state changes tracked in `outbox_messages`.
- When `PROVIDER_GATEWAY_OUTBOUND_ENABLED=1`, outbox event sends use `ProviderGatewayAdapter` and emit
  `provider_outbound` payloads; status callbacks update outbox meta via `/provider/status`.

---

## 10) Observability (why did bot reply this way)

**Code blocks:**
- Trace/meta: `truffles-api/app/routers/webhook/trace.py`
- OTel/metrics: `truffles-api/app/logging_config.py`
- Trace bundle: `docs/runbooks/TRACE_BUNDLE.md`

**Behavior impact:**
- Every stage records `decision_trace` + `decision_meta`. This is the source of truth for debugging.

---

## 11) Simulation & evaluation

**Code blocks:**
- Chaos sim runner + evaluator: `ops/diagnose.py` (`chaos-sim`)
- Livecheck auto (CA suites): `ops/diagnose.py` (`livecheck-auto`)
- Eval tests: `truffles-api/tests/test_demo_salon_eval.py` (uses `EVAL.yaml`)

**Behavior impact:**
- Simulates 10–15 turn dialogs with noise and mixed languages, validates behavior by trace/meta (not by text).
- `demo_salon` eval is a canary; tests assert invariants and must not drive demo‑only logic.

---

## Consult snapshot strict cutover (canary)

**How to enable (demo_salon):**
- Ensure published `knowledge_versions` payload includes `consult_playbook`.
- Set env: `KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED=1`, `KNOWLEDGE_SNAPSHOT_CONSULT_MODE=strict`,
  `KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST=demo_salon`.

**Behavior impact:**
- Consult uses snapshot playbook only for allowlisted tenants.
- Missing playbook → clarify (no fallback to file packs in strict mode).

---

## Consult pack flow (current behavior, line-accurate)

**Decision entry (consult branch in main pipeline)**
- `truffles-api/app/routers/webhook/decision.py:6332` → `_handle_consult_flow(...)` is invoked before multi-intent routing.

**Pack load + schema validation**
- `truffles-api/app/services/consult_pack_service.py:22-163` → load/validate pack, build pack-sourced reply.
- `truffles-api/app/schemas/consult.py:37-120` → playbook + controller output schemas (validate/guard).

**Topic resolution (semantic + controller)**
- `truffles-api/app/services/knowledge_service.py:81-141` → `resolve_consult_topic_candidates` (embeddings + top-k).
- If embeddings fail, resolver falls back to lexical token matching (still `consult_topic_resolver` trace).
- `truffles-api/app/services/ai_service.py:1593-1679` → `generate_consult_controller_output` (LLM JSON, strict schema).
- Selection order in consult flow: controller topic → semantic top-1 (score >= 0.6) → intent_decomp topic.
  `truffles-api/app/routers/webhook/response.py:657-673`.

**Explicit info short-circuit**
- If explicit info intent present, consult flow records `consult_flow` short_circuit and returns to info/booking flow.
  `truffles-api/app/routers/webhook/response.py:583-692`.

**Service availability integration (facts)**
- service_matcher/truth/multi_truth response is merged into consult meta and can be combined with consult reply.
  `truffles-api/app/routers/webhook/response.py:1090-1162`.

**Consult trace/meta**
- consult_flow decision + reason recorded here:
  `truffles-api/app/routers/webhook/response.py:1228-1257`.
- consult_context is set for goal preservation:
  `truffles-api/app/routers/webhook/response.py:1259-1289`.

**Tests + livecheck probes**
- Pack meta/trace: `truffles-api/tests/test_message_endpoint.py:855-991`
- Pack flow trace/meta (controller + resolver): `truffles-api/tests/test_message_endpoint.py:1109-1256`
- Livecheck: CA06 consult suite in `ops/diagnose.py` (ACK skipped to avoid trace override):
  `ops/diagnose.py:6936-6938`

---

## Quick start (new dev/agent)

1) Read `SPECS/CONSULTANT.md` (behavior rules).
2) Open `decision.py` → find stage order + gates.
3) For flow change: check `booking.py`, `info.py`, `response.py` (consult).
4) For consult schema: check `contracts/consult/consult_playbook.v1.jsonschema` and
   `contracts/consult/consult_controller_output.v1.jsonschema`.
5) For facts: check `demo_salon_knowledge.py` + `SALON_TRUTH.yaml`.
6) Verify with `ops/diagnose.py chaos-sim` and/or `pytest truffles-api/tests/test_demo_salon_eval.py`.
