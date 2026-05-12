# Policy-Core v3 — Specification

Status: DRAFT (PoC, not wired)
Owner: Top Architect
Classification: REPLACE for legacy `truffles-api/app/services/intent_service.py`
Date: 2026-05-11

---

## 0. Why this exists

The legacy `intent_service.py` (~15,000 lines, ~30+ scenario-specific
`_policy_core_<scenario>_forced_fields` functions, multiple scenario-named
boundary services) violates AGENTS section 8 by making deterministic Python the
hidden semantic owner. The model is reduced to filling templates that the code
already pre-decided. This produces:

- structural inability to scale to new verticals (every messy dialog requires a
  new code branch),
- repeated `policy_core_degrade` / `policy_core:empty_response` failures when the
  model is over-constrained,
- impossible audit because the real decision is distributed across dozens of
  forced-field branches,
- impossible refactor because changes touch a god-file.

Policy-Core v3 replaces this layer with a single thin invoker around an LLM
that owns semantic decisions, plus typed contracts that other layers (planner,
boundary, executor) can rely on.

This document specifies v3. It does NOT modify the legacy hot path. The PoC
sits under `truffles-api/app/policy_core_v3/` behind a feature flag
`policy_core_v3_enabled` defaulting to `False`.

---

## 1. Position in the hot path

```
Ingress
  ↓
Turn Context Loader
  ↓
Policy-Core v3              ← THIS DOCUMENT
  ↓
Planner
  ↓
Boundary
  ↓
State Writer
  ↓
Executor (tools)
  ↓
Response Realizer
  ↓
Outbox / Provider
```

v3 is invoked once per inbound customer turn. It receives a typed
`PolicyTurnInput` and returns either a typed `PolicyDecisionV3` or a typed
`DegradeVerdict`. It performs no I/O beyond invoking the LLM provider passed
in.

---

## 2. Hard rules (binding)

1. v3 is the **single semantic owner**. No other layer may decide intent,
   tool selection, slot meaning, or follow-up semantics.
2. v3 must never write to the database, perform tool side effects, render the
   final customer message, or call provider APIs.
3. v3 must never contain scenario-specific forced-field branches. The prompt
   builder is composed from declarative inputs (pack view, capabilities, state,
   evidence, message). Adding a niche means changing inputs, never adding a
   Python branch.
4. v3 must never silently rewrite or rescue model output. Invalid output →
   bounded retry with deterministic policy → if still invalid, return a
   `DegradeVerdict`. The next layer (boundary/planner) decides what happens
   with a degrade.
5. v3 must never use regex/lexicon to *decide* anything. Regex/lexicon may be
   used only by upstream evidence layers and arrive in v3 as `evidence_bundle`
   inputs that the model reasons over.
6. v3 must produce machine-readable output validated against
   `PolicyDecisionV3`. Free-text-only model output is not acceptable as
   intent ownership.
7. v3 is tenant-agnostic and vertical-agnostic. All tenant/vertical content
   arrives via inputs (pack view, capabilities, tool contracts).

---

## 3. Output contract: `PolicyDecisionV3`

The model is required to emit (and v3 to validate) a single JSON object with
the following typed fields:

| Field | Type | Meaning |
|---|---|---|
| `intent` | string enum | One of: `fact_question`, `slot_collect`, `booking_request`, `booking_manage`, `handoff_request`, `smalltalk`, `unsupported`, `unknown` |
| `slots` | object | Key-value of typed slots already known/inferred this turn (e.g. `service_id`, `datetime`, `customer_name`, `customer_phone`, `lookup_identity`). All values are strings or null; semantic typing happens in planner. |
| `candidate_action` | object | `{tool: <tool_id or "none">, args: {...}}`. The tool must be in the input `tool_contracts` list. `none` means "no side effect this turn". |
| `evidence_refs` | string[] | Identifiers of evidence rows from `evidence_bundle` that the model used. Empty list is allowed; it forces the boundary to evaluate groundedness. |
| `message_draft` | string | The model's draft customer-facing message. Realizer may rewrite for tone/length. Boundary may suppress if rules are violated. |
| `uncertainty` | string enum | `low`, `medium`, `high`. `high` is a hint to boundary to prefer handoff over commit. |
| `degrade_reason` | string \| null | Always null on success. Set by v3 (not the model) on retry exhaustion or schema invalidity, and the response is then a `DegradeVerdict`, not a `PolicyDecisionV3`. |
| `notes` | string | Optional freeform model rationale, non-binding, for trace only. |

`DegradeVerdict` is a sibling type returned by v3 when the model cannot produce
a valid decision after the retry policy is exhausted:

| Field | Type | Meaning |
|---|---|---|
| `degrade_reason` | string enum | `empty_response`, `schema_invalid`, `timeout`, `provider_error`, `tool_not_in_contract`, `intent_not_in_enum` |
| `last_raw_output` | string \| null | Truncated model output for trace, never used downstream |
| `attempts` | int | Number of LLM calls performed |
| `notes` | string | Diagnostic only |

Boundary receives `PolicyDecisionV3 | DegradeVerdict` and decides whether to
degrade to handoff, ask a clarifying question, or accept.

---

## 4. Input contract: `PolicyTurnInput`

| Field | Type | Source | Notes |
|---|---|---|---|
| `tenant_id` | string | turn_context_loader | Opaque to v3 |
| `conversation_id` | string | turn_context_loader | Opaque |
| `current_message` | string | ingress | Raw customer text this turn |
| `conversation_history` | `Turn[]` | state | Last N normalized turns (role, text). N is configurable. |
| `state_slots` | object | state | Slots already collected in this conversation |
| `pack_view` | `PackView` (Protocol) | pack runtime | Read-only services/specialists/rules slice |
| `capabilities` | string[] | pack/capability registry | Allowed capability ids for this tenant |
| `tool_contracts` | `ToolContract[]` | tool registry | List of allowed tools with id, args schema, description |
| `evidence_bundle` | `EvidenceItem[]` | evidence layer | RAG hits, lexicon normalizations, datetime candidates, phone candidates. Each has `id`, `source`, `kind`, `payload`, `confidence`. |
| `now` | datetime | clock | Tenant-local current time |
| `locale` | string | tenant settings | e.g. `ru-KZ` |
| `policy_version` | string | snapshot service | For trace pinning |

`PackView` is intentionally a **minimum** Protocol for v3, scoped to what the
prompt-builder needs:

```python
class PackView(Protocol):
    pack_id: str
    services: list[ServiceView]
    specialists: list[SpecialistView]
    rules: PackRules         # bot_can_confirm, required_for_booking, identity_for_lookup, escalate_topics
    business_summary: str    # 1-3 sentence pack summary used in the system header
```

Full `PackV1` will subsume this Protocol in a later session. v3 consumers must
not depend on anything beyond `PackView`.

---

## 5. Prompt builder principles

The prompt builder is a **pure function** of `PolicyTurnInput`. It contains
zero scenario-specific branches. Its only knobs are layout/formatting.

The prompt is assembled from these sections in fixed order:

1. **System header** — role, hard rules, output schema (JSON), refusal rules.
2. **Tenant pack** — `pack_view.business_summary`, services list (id, name,
   aliases, price, duration), specialists list, rules block (`bot_can_confirm`,
   required_for_booking, identity_for_lookup, escalate_topics).
3. **Capabilities** — list of allowed capabilities and what each means.
4. **Tools** — list of `tool_contracts` with id, description, args schema.
5. **Conversation state** — collected slots, pending fields, last bot draft if
   any.
6. **Conversation history** — last N turns.
7. **Evidence bundle** — id, source, kind, payload, confidence. The model is
   instructed to cite evidence ids in `evidence_refs`.
8. **Current message** — verbatim.
9. **Output instructions** — produce exactly one JSON object matching
   `PolicyDecisionV3`. No prose.

Forbidden in prompt builder:

- branching on tenant id, vertical id, or specific service names;
- hardcoded text snippets that imply a particular intent;
- per-scenario "forced fields" hints;
- regex over `current_message` to choose a section variant.

Allowed:

- truncating long history (deterministic, by token budget);
- omitting empty sections;
- locale-specific output language directive.

---

## 6. Retry & degrade policy

v3 owns a **deterministic, scenario-free retry policy**. This is the only
place where retry decisions are made.

| Failure | Action | Max attempts |
|---|---|---|
| `timeout` | retry with same input | 1 |
| `provider_error` (5xx, network) | retry with same input | 1 |
| `empty_response` (whitespace only) | retry with shorter prompt (drop oldest history turns) | 1 |
| `schema_invalid` (JSON parse fail or pydantic fail) | retry with explicit "your last output failed schema X with reason Y, return only JSON object" hint | 1 |
| `tool_not_in_contract` | retry once with explicit list of allowed tool ids | 1 |
| `intent_not_in_enum` | retry once with explicit list of allowed intents | 1 |

Total cap: **2 LLM calls per turn**. After cap, return `DegradeVerdict`.

Forbidden:

- per-scenario retry tweaks;
- silently rewriting model output to make it pass schema;
- inferring missing fields from conversation history (that is the planner's
  job once it receives a `DegradeVerdict`).

---

## 7. What v3 does NOT do

- Does not write to the database.
- Does not call tools (calendar, handoff, fact lookups).
- Does not render the final customer message — `message_draft` may be
  rewritten by the response realizer.
- Does not validate business rules (e.g. "no booking without phone"). That is
  the boundary's typed responsibility.
- Does not maintain conversation memory — state writer owns persistence.
- Does not dispatch metrics. It returns trace fields; an outer caller
  publishes metrics.
- Does not load tenant/pack/tool data. All inputs are passed in.

---

## 8. Migration plan

### Phase A — PoC (this session)
- Module skeleton at `truffles-api/app/policy_core_v3/`.
- Schemas, prompt builder, retry policy, invoker.
- Unit tests with mock LLM and mock pack.
- Feature flag `policy_core_v3_enabled = False`.
- Not wired to runtime.

### Phase B — Shadow run (next session)
- Add an inert call site in `consultant_runtime` that, when the flag is on,
  invokes v3 in parallel with the legacy path, captures both decisions, and
  emits a comparison artifact. Legacy still owns the customer reply.
- Build a small approved corpus runner that compares v3 vs legacy across the
  approved internal pilot dialogs.

### Phase C — Cutover (later session)
- For a single tenant in canary, switch the customer-facing decision to v3
  output, with legacy retained as fallback only on `DegradeVerdict`.
- Compare metrics: `policy_core_degrade_rate`, `boundary_reject_rate`,
  `dialog_business_success_rate`.

### Phase D — Cleanup (later session)
- Once v3 owns all tenants and approved corpora pass, delete:
  - all `_policy_core_<scenario>_forced_fields` functions in
    `intent_service.py`,
  - `policy_timeout_*_boundary_service.py` files (merged into one boundary
    rule),
  - shadow comparison artifact code,
  - legacy `intent_service.IntentService.run` after callers migrated.

Cutover is irreversible only at Phase D. Phases A–C can be reverted by
flipping the feature flag.

---

## 9. Acceptance criteria for the PoC

The PoC is acceptable for this session if all hold:

1. `python3 -m py_compile` succeeds for every new file.
2. `pytest truffles-api/tests/policy_core_v3/ -q` passes.
3. The new module has no import dependency on `truffles-api/app/services/`,
   `truffles-api/app/core/`, or any pack-runtime adapter. (Independence
   guarantee.)
4. The prompt builder is a pure function: the same `PolicyTurnInput` produces
   byte-equal prompt strings.
5. The invoker's retry policy is decision-table driven, not branching on
   message content.
6. Feature flag `policy_core_v3_enabled` exists and defaults to `False`.
7. No file in `truffles-api/app/services/`, `truffles-api/app/core/`, or
   `truffles-api/app/main.py` is modified by this session.
8. A Decision Ledger entry records the PoC, classification, known limits, and
   `do_not_repeat` items.

---

## 10. Acceptance criteria for production cutover (Phase C)

Cutover requires all of:

1. On the owner-approved internal pilot corpus (≥30 messy dialogs), v3
   achieves: `dialog_business_success_rate ≥ 0.95`, `policy_core_degrade_rate
   ≤ 0.05`, `boundary_reject_rate` no worse than legacy by more than 2 points.
2. Zero scenario-specific Python branches in `policy_core_v3/`.
3. v3 output is consumable by boundary, state writer, and executor without
   any compatibility shim.
4. Trace shows 100% of v3 turns producing either `PolicyDecisionV3` or
   `DegradeVerdict` — never raw model text bypassing schema.
5. Adding a new niche pack to a test tenant does not require any change in
   `policy_core_v3/`.

---

## 11. Open questions (to resolve before Phase B)

- **Q1**: Token budget for the prompt — fixed cap or adaptive? Current PoC
  uses fixed cap.
- **Q2**: Should `evidence_refs` be required when `intent == fact_question`?
  Tentatively yes, to be enforced by boundary, not v3.
- **Q3**: Should `message_draft` always be in customer locale? Yes, prompt
  enforces it; non-locale output is treated as `schema_invalid`.
- **Q4**: How does v3 surface "I need a clarifying question" without acting
  on assumptions? Tentative answer: `intent = slot_collect`, `candidate_action
  = {tool: "none"}`, `message_draft` is the question. Boundary verifies the
  question targets a known required slot.
- **Q5**: Multi-message turns (customer sends 3 messages quickly) — handled by
  upstream turn aggregator, not v3.
- **Q6**: Locale and pack i18n — pack provides `business_summary` already in
  customer locale; future PackV1 will formalize this.

---

## 12. Do-not-repeat (binding for any future v3 work)

- Do not add a `_policy_core_<anything>_forced_fields` style branch.
- Do not add scenario-named files (e.g. `policy_timeout_<scenario>.py`)
  inside or around v3.
- Do not import legacy intent_service helpers into v3.
- Do not let v3 perform side effects.
- Do not infer slot values via regex inside v3; evidence layer owns that
  upstream.
- Do not swallow `DegradeVerdict` and produce a synthetic success.
