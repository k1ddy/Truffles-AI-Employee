# Consultant Code Map (ChatGPT‑5‑like but controlled)

**Purpose:** fast onboarding for new devs/agents. Shows where the "brain" lives in code, what each block does, and how it shapes behavior.

**Canon refs:**
- `SPECS/CONSULTANT.md` — behavior rules, safety, multi‑intent, no‑hallucination.
- `SPECS/ARCHITECTURE.md` — decision graph & stage order (canon).
- `SPECS/SYSTEM_REFERENCE.md` — code‑accurate pipeline map + testing SOP.

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

8) Domain flows (deterministic core)
   - Booking/info/consult flows run before LLM generation and can return early:
     `truffles-api/app/routers/webhook/booking.py`, `truffles-api/app/routers/webhook/info.py`,
     `truffles-api/app/routers/webhook/response.py`

9) LLM primary response (only if domain flows did not answer)
   - `_handle_llm_primary` → `generate_bot_response` → `generate_ai_response` (RAG + LLM).
     `truffles-api/app/routers/webhook/decision.py:6583`, `truffles-api/app/routers/webhook/response.py:1073`,
     `truffles-api/app/services/message_service.py:104`, `truffles-api/app/services/ai_service.py:1948`
   - If LLM primary fails or is skipped, `truth_gate` fallback can still answer deterministically.

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

**Interpretation:** this message hit the truth gate (deterministic reply) but still used LLM for routing
(`controller_llm_ms`, `multi_intent_llm_ms`). LLM generation (`ai_response`) did not run because the
truth gate provided a safe response.

## 1) Entry point & decision graph (the brain orchestrator)

**Code:** `truffles-api/app/routers/webhook/decision.py` (`_handle_webhook_payload`).

**Responsibility:**
- Accept inbound message, enrich with context, run gates, choose action (reply/escalate/booking_prompt), and record `decision_meta`/`decision_trace`.

**Behavior impact:**
- **Order matters.** State/pending/LAW/policy gates can override any LLM meaning. This keeps the system safe and deterministic.
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
- Domain facts + service availability: `truffles-api/app/services/demo_salon_knowledge.py`
- Truth pack (facts/policy): `truffles-api/app/knowledge/<client_slug>/SALON_TRUTH.yaml`
- Consult playbooks (care advice): `truffles-api/app/knowledge/<client_slug>/CONSULT_PLAYBOOK.yaml`
- Knowledge Snapshot Gateway (shadow): `truffles-api/app/routers/knowledge_gateway.py` + `truffles-api/app/services/knowledge_snapshot_service.py`
- Consult contracts: `truffles-api/app/schemas/consult.py` (runtime validation), `contracts/consult/consult_playbook.v1.jsonschema`
- Generic pack scaffold (CI/tests): `truffles-api/app/knowledge/generic/*`
- EVAL cases: `truffles-api/app/knowledge/demo_salon/EVAL.yaml`

**Behavior impact:**
- **No hallucinations:** facts only from `client_pack`/`consult_playbooks`.
- If service is not offered → explicit **"не оказываем"** reply (`service_not_found`).

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

---

## Consult pack flow (current behavior, line-accurate)

**Decision entry (consult branch in main pipeline)**
- `truffles-api/app/routers/webhook/decision.py:6332` → `_handle_consult_flow(...)` is invoked before multi-intent routing.

**Pack load + schema validation**
- `truffles-api/app/services/consult_pack_service.py:22-163` → load/validate pack, build deterministic reply.
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
