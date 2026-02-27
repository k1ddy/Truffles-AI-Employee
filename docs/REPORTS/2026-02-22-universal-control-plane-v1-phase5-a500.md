# Universal Control Plane v1 - Phase 5 Policy Governance Split (a500)

Date
- 2026-02-27

## Block identity
- `BLOCK_ID`: UCPV1-PHASE5
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE4
- `UNLOCKS`: UCPV1-PHASE6

## Input baseline (FACT)
- `UCPV1-PHASE4` закрыт и переведен в `passed`; следующий unlocked блок: `UCPV1-PHASE5`.
- В runtime уже есть hard-law gate (`_resolve_hard_law_sections`) и policy-pack load path (`_get_policy_pack`), но нет capability-level operational policy override contract.
- Отдельного `/admin/*` policy registry CRUD в текущем console API нет.

## FACT pre-check evidence (before changes)
- `rg -n "@router\\.(get|post|patch|delete)\\(\"/admin/.+policy" truffles-api/app/routers/console.py` -> no matches.
- `rg -n "policy_bundle|handoff_policy|allowed_fact_scopes" truffles-api/app/schemas truffles-api/app/services contracts` -> policy bundle schema present, capability governance fields present, but no operational policy override field.
- `truffles-api/app/routers/webhook/policy.py:142` -> `_get_policy_pack` returns config/pack policy without capability override merge.

## One web search evidence
- `Query (exact)` -> `policy as code versioning rollback best practices open policy agent`
- `Sources opened`:
  - https://www.openpolicyagent.org/docs/management
  - https://www.openpolicyagent.org/docs/deploy
- `Decision` -> reuse existing capabilities + runtime boundary and add policy-overrides contract instead of introducing new orchestration engine.
- `What was reused` -> `CapabilitiesPayload`, runtime capability context, hard-law resolver `_resolve_hard_law_sections`.

## Root cause validation
- `Symptom` -> runtime policy path does not expose safe operational override layer; hard-law and operational policy are not cleanly split in capability contract.
- `Minimal reproduction` -> inspect `CapabilitiesPayload` and `_get_policy_pack`; verify absence of override contract and absence of hard-law deny on override path.
- `Root cause statement` -> missing explicit operational-policy override boundary with hard-law deny semantics.
- `Proof after fix` -> runtime now applies `policy_overrides` only for operational sections and skips overrides when target section is hard-law.

## Reuse-first outcome
- `Internal reuse applied` -> yes; leveraged existing capabilities merge, runtime context, and hard-law detection.
- `External reuse applied` -> design guidance only (OPA best practices), no new dependency.
- `If build-new` -> not applicable.

## Contract delta
- Added `policy_overrides` to `CapabilitiesPayload` with strict operational-only schema (`payment_info`, `discounts`).
- Runtime policy pack resolution now applies capability overrides through `_apply_runtime_policy_overrides`.
- Hard-law boundary enforced: override is ignored when section is part of current hard-law set.

## Implemented changes
- `truffles-api/app/schemas/capabilities.py`
- `truffles-api/app/services/capabilities_service.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/tests/test_capabilities_runtime.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase5-a500.md`
- `docs/SESSION_INDEX.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`

## Checks + outcomes
- `pytest -q truffles-api/tests/test_capabilities_runtime.py` -> `10 passed in 2.97s`
- `pytest -q truffles-api/tests/test_policy_handler_runtime.py` -> `9 passed in 2.64s`
- `python3 -m py_compile truffles-api/app/schemas/capabilities.py truffles-api/app/services/capabilities_service.py truffles-api/app/routers/webhook/policy.py` -> pass
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `1`
- `Stop condition respected` -> `yes`
- `If exceeded` -> n/a

## Evidence
- Local test outputs from commands listed above.
- Runtime guard logic and schema changes in touched files.

## Release safety decision
- `Strategy used` -> phased tenant-scoped adoption via capabilities payload values.
- `Go/no-go signals observed` -> deterministic tests green; hard-law override deny path covered.
- `Rollback readiness` -> verified by code-level rollback (revert commit) and deterministic re-run of touched tests.

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
  - `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase5-a500.md`
  - `docs/SESSION_INDEX.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift resolved`: `partial`
- `If no`: B05 target still needs versioned policy registry CRUD and explicit version pin/rollback workflows.

## Residual GAP / Risks
- B05 acceptance criterion `versioned policy registry` is still open.
- Current wave enables operational override boundary only for `payment_info` and `discounts`.
- Future wave must deliver policy version lifecycle in Console Plane before phase closure.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `Do not touch`: unrelated onboarding and marketing tracks
- `Open risks`: policy registry versioning gap
- `First command to verify`: `pytest -q truffles-api/tests/test_capabilities_runtime.py truffles-api/tests/test_policy_handler_runtime.py`

## Verdict
- `Blocked`
