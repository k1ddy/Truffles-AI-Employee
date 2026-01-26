# TP-2026-01-26 - Consult DoD: Domain-Agnostic, Pack-First, No Dictionaries

## Goal
Define a scalable consult pipeline that passes Consult DoD without expanding phrase dictionaries and without
any client or niche binding. Produce a spec-only package (schema + contracts + test plan) ready for build.

## Invariant
- Hard-LAW/policy/pending gates remain pre-LLM and fail-closed.
- LLM does not create facts; facts come only from packs/tools.
- Consult is pack-first; LLM advice only within allowed claims.
- decision_meta/decision_trace are written for every inbound message.

## Scope
- Define a domain-agnostic consult pack schema and LLM output contract.
- Define deterministic commit rules and response guard for consult answers.
- Define test plan and evidence matrix aligned with Consult DoD.

## Out of scope
- Runtime implementation changes.
- Pack content creation for any specific domain.
- CI or live-check execution.

## Touch-list (planned)
- `SPECS/CONSULTANT.md` (add canonical consult schema and guard rules)
- `SPECS/ARCHITECTURE.md` (pipeline contract + trace/meta)
- `truffles-api/app/routers/webhook/response.py` (consult flow)
- `truffles-api/app/services/ai_service.py` (LLM controller + RAG)
- `truffles-api/app/services/knowledge_service.py` (semantic topic resolver)
- `contracts/consult/consult_playbook.v1.jsonschema` (new)
- `contracts/consult/consult_controller_output.v1.jsonschema` (new)
- `truffles-api/tests/*` (contract + behavior tests)
- `docs/CONSULTANT_CODEMAP.md` (flow diagram update)

## Plan
1) Add consult pack schema (Appendix A) and LLM output contract (Appendix B).
2) Define semantic topic resolver: embeddings over pack topics, Top-K candidates, LLM chooses topic_id.
3) Add deterministic commit rules + response guard for consult.
4) Add tests (unit + contract + integration + chaos) per Appendix C.
5) Run CI and live-check, record evidence in `STATE.md`.

## DoD
- Schema and contracts are published and referenced in `SPECS/CONSULTANT.md`.
- Consult flow uses semantic topic resolver (no phrase dictionaries).
- Response guard blocks any claim outside pack/tools.
- Trace/meta includes consult topic_id, decision source, and guard result.
- Tests pass for consult invariants (pack-first, no hallucination, clarify-limit).
- Live-check evidence recorded (trace bundle + decision_meta).

## Checks
- `rg -n "consult_playbook.v1|consult_controller_output.v1" SPECS/CONSULTANT.md`
- `pytest -q truffles-api/tests/test_consult_*`
- `python3 ops/diagnose.py trace-bundle --client-slug <slug> --text "<marker>"`

## Evidence
- CI run URL(s) with consult tests green.
- Trace bundle JSON path + correlation keys (message_id, trace_id, outbox_id).
- decision_meta fields: `action`, `intent`, `consult_topic_id`, `consult_source`, `llm_used`.

## Rollback
- Revert commits adding schema/contracts and consult pipeline changes.

## No-go
- Adding phrase dictionaries or client-specific rules to code.
- LLM generating facts or decisions without deterministic guard.
- Missing decision_meta/decision_trace for consult replies.

## Risks / blockers
- Need a neutral "generic" pack for CI to avoid niche coupling.
- Requires agreement on consult schema in canon docs.

## Branch / Worktree
- Branch: `docs/consult-agnostic-dod`
- Worktree: `/home/zhan/worktrees/consult-agnostic-dod`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain after merge

---

## Appendix A - Consult Pack Schema (draft, domain-agnostic)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "consult_playbook.v1",
  "type": "object",
  "required": ["version", "topics"],
  "properties": {
    "version": { "const": "v1" },
    "topics": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": [
          "id",
          "title",
          "summary",
          "allowed_advice",
          "required_questions",
          "clarify_limit",
          "risk_tags",
          "escalate_when"
        ],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z0-9_-]+$" },
          "title": { "type": "string", "minLength": 2 },
          "summary": { "type": "string", "minLength": 8 },
          "allowed_advice": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string", "minLength": 3 }
          },
          "required_questions": {
            "type": "array",
            "minItems": 0,
            "items": { "type": "string", "minLength": 3 }
          },
          "optional_questions": {
            "type": "array",
            "items": { "type": "string", "minLength": 3 }
          },
          "disallowed_claims": {
            "type": "array",
            "items": { "type": "string", "minLength": 3 }
          },
          "fact_requirements": {
            "type": "array",
            "items": {
              "enum": [
                "service_exists",
                "policy_present",
                "price_allowed",
                "duration_allowed"
              ]
            }
          },
          "risk_tags": {
            "type": "array",
            "items": {
              "enum": ["none", "medical", "legal", "payment", "safety", "privacy"]
            }
          },
          "clarify_limit": { "type": "integer", "minimum": 0, "maximum": 2 },
          "escalate_when": {
            "type": "array",
            "items": {
              "enum": [
                "risk_high",
                "needs_human",
                "missing_fact",
                "unknown_topic",
                "clarify_limit_exceeded"
              ]
            }
          },
          "next_step": { "type": "string" }
        },
        "additionalProperties": false
      }
    },
    "default_policy": {
      "type": "object",
      "properties": {
        "clarify_limit": { "type": "integer", "minimum": 0, "maximum": 2 },
        "escalate_on_low_confidence": { "type": "boolean" }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

## Appendix B - LLM Controller Output Contract (draft)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "consult_controller_output.v1",
  "type": "object",
  "required": ["intent", "topic_id", "confidence", "risk_class", "actions"],
  "properties": {
    "intent": {
      "enum": ["consult", "info", "booking", "handoff", "out_of_domain"]
    },
    "topic_id": { "type": "string" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "risk_class": { "enum": ["low", "medium", "high", "blocked"] },
    "actions": {
      "type": "array",
      "items": { "enum": ["answer", "clarify", "handoff"] }
    },
    "slots": {
      "type": "object",
      "additionalProperties": { "type": "string" }
    },
    "notes": { "type": "string" }
  },
  "additionalProperties": false
}
```

## Appendix C - Test Plan and Evidence Matrix

### Test tiers
- **L0 (unit)**: schema validation, guard rules, clarify limits.
- **L1 (integration)**: consult flow with mock LLM + pack topics (no dictionaries).
- **L2 (eval/chaos)**: multi-turn consult interruptions, mixed intents, low-confidence.
- **L3 (live-check)**: real inbound with trace bundle evidence.

### Required evidence (Consult DoD)
| Check | Evidence | Source |
| --- | --- | --- |
| Pack-first consult | decision_meta `consult_source=pack` | trace-bundle JSON |
| No hallucination | response guard blocks non-pack claims | unit + integration tests |
| Clarify limit | `clarify_attempt` <= 2, then handoff | trace/meta + tests |
| Risk gates | `risk_class=high` => `action=handoff` | tests + live-check |
| Trace/meta | `decision_trace` + `decision_meta` on inbound | trace-bundle JSON |

### Live-check (generic, no niche)
- Use a neutral pack in CI (no domain-specific vocab).
- Live-check validates only decision_meta/trace, not text content.
- Evidence stored as trace bundle + correlation keys in `STATE.md`.
