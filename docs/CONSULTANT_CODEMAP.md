# Consultant Code Map (ChatGPT‑5‑like but controlled)

**Purpose:** fast onboarding for new devs/agents. Shows where the "brain" lives in code, what each block does, and how it shapes behavior.

**Canon refs:**
- `SPECS/CONSULTANT.md` — behavior rules, safety, multi‑intent, no‑hallucination.
- `SPECS/ARCHITECTURE.md` — decision graph & stage order (canon).
- `SPECS/SYSTEM_REFERENCE.md` — code‑accurate pipeline map + testing SOP.

---

## 1) Entry point & decision graph (the brain orchestrator)

**Code:** `truffles-api/app/routers/webhook/decision.py` (`_handle_webhook_payload`).

**Responsibility:**
- Accept inbound message, enrich with context, run gates, choose action (reply/escalate/booking_prompt), and record `decision_meta`/`decision_trace`.

**Behavior impact:**
- **Order matters.** State/pending/LAW/policy gates can override any LLM meaning. This keeps the system safe and deterministic.
- If you change stage order, you change bot behavior. See `SPECS/SYSTEM_REFERENCE.md` → “Decision pipeline”.

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
- Topic resolver: `truffles-api/app/services/knowledge_service.py` → `resolve_consult_topic_candidates`
- LLM controller (topic select JSON): `truffles-api/app/services/ai_service.py` → `generate_consult_controller_output`
- Playbook first; LLM advice only for general beauty care and non‑medical topics (legacy fallback only when no pack decision).

**Behavior impact:**
- Booking keeps goal across interruptions; consult replies can be returned with booking follow‑up.
- Consult does **not** override booking goal when booking is active.

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
4) For facts: check `demo_salon_knowledge.py` + `SALON_TRUTH.yaml`.
5) Verify with `ops/diagnose.py chaos-sim` and/or `pytest truffles-api/tests/test_demo_salon_eval.py`.
