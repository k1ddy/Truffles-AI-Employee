# TP-2026-01-26 - Consult Domain-Agnostic Implementation (No Dictionaries)

## Goal
Implement domain-agnostic consult routing and response guard using consult pack schema and LLM controller
contract, without phrase dictionaries or client-specific logic. Provide tests and live-check evidence.

## Invariant
- Hard-LAW/policy/pending gates remain pre-LLM and fail-closed.
- LLM does not create facts; consult answers only from pack/tools.
- No phrase dictionaries or client/niche-specific rules in code.
- decision_meta/decision_trace written for every inbound message.

## Scope
- Implement consult pack schema usage and controller output validation.
- Add semantic topic resolver (embeddings + Top-K + LLM topic selection).
- Add consult response guard enforcing allowed_advice and fact requirements.
- Add tests (unit + integration + trace/meta + contract).
- Add live-check plan + evidence capture.

## Out of scope
- Any changes to booking/info flows.
- Pack content changes for specific clients.
- Changes to architecture outside consult pipeline.

## Touch-list
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/knowledge_service.py`
- `truffles-api/app/routers/webhook/trace.py`
- `contracts/consult/consult_playbook.v1.jsonschema`
- `contracts/consult/consult_controller_output.v1.jsonschema`
- `truffles-api/tests/test_consult_*`
- `truffles-api/tests/test_webhook_trace.py`
- `docs/runbooks/TRACE_BUNDLE.md` (if new trace fields require docs)

## Plan
1) Validate consult pack schema at load time; fail-closed if invalid.
2) Implement semantic topic resolver (embeddings over pack topics → Top-K → LLM chooses topic_id).
3) Validate LLM controller output against `consult_controller_output.v1`.
4) Implement consult response guard (allowed_advice only; facts only from pack/tools).
5) Add trace/meta fields (`consult_topic_id`, `consult_source`, `consult_guard`, `consult_risk_class`, `consult_confidence`).
6) Add tests (unit schema/guard, integration consult flow, trace/meta assertions).
7) Live-check via `ops/diagnose.py trace-bundle` and record evidence in `STATE.md`.

## DoD
- Consult answers never include claims outside pack/tools.
- No phrase dictionaries used for consult routing.
- Trace/meta includes consult fields and decision source.
- Tests pass and live-check evidence recorded.

## Checks
- `pytest -q truffles-api/tests/test_consult_*`
- `pytest -q truffles-api/tests/test_webhook_trace.py`
- `python3 ops/diagnose.py trace-bundle --client-slug <slug> --text "<marker>"`

## Evidence
- CI run URL(s) with consult tests.
- Trace bundle JSON path + correlation keys.
- decision_meta fields include consult_source/consult_topic_id/consult_risk_class.

## Rollback
- Revert commits that touch consult pipeline and contracts.

## No-go
- Any dictionary-based routing or client-specific conditionals.
- Missing decision_meta/decision_trace for consult replies.
- LLM-generated facts or policy bypass.

## Risks / blockers
- Need a generic (non-niche) pack for CI and tests.
- Confidence thresholds require calibration to avoid over-escalation.

## Branch / Worktree
- Branch: `feat/consult-agnostic-implementation-2026-01-26`
- Worktree: `/home/zhan/worktrees/consult-agnostic-implementation`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain after merge
