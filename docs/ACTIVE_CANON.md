# ACTIVE CANON

## Semantic Authority
Target authority is only `PolicyDecision`.
Current cutover truth: policy-core already defines the intended semantic contract, but legacy router code still participates in active runtime behavior.

Only the semantic owner may define:
- outcome
- interaction_owner
- interaction_target
- interaction_relation
- pending_question_contract
- tool_intent

## Continuity Authority
Target authority is only `DialogState`.
Current cutover truth: continuity still spans canonical dialog state, session memory, and pending-resume snapshots; Week 1 freezes new drift and documents the current allowed writer set.

## Boundary Scope
Deterministic boundary may only:
- validate
- block
- degrade with explicit reason-code
- request replan

Boundary may not silently invent or reset semantic meaning.

## Proof Scope
Proof/eval is a read-only observer of runtime artifacts.
It may not retag, normalize into truth, repair, or reinterpret runtime semantics post-hoc.

## Sunset Files
These files may not receive new semantic logic without an explicit recorded waiver:
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`

## Platform Claim Rule
No business-agnostic claim is valid without multi-pack evidence.
`demo_salon` remains canary only.
