# Consultant-Core Program Factual Proof Matrix

## Purpose
This report answers a narrower question than full acceptance:
- what is proven by the implemented code as it exists now,
- what is proven by generated proof/release artifacts,
- and what is still **not** fully proven if deterministic tests are excluded.

This is a repo-backed factual closure audit, not a substitute for realistic acceptance.

## Method
1. Code audit across the final active path and closed workstream seams.
2. Generated proof-artifact audit:
   - `python3 ops/shadow_replay.py --input /tmp/a922-proof/base.json --shadow /tmp/a922-proof/shadow.json --output /tmp/a922-proof/shadow_report.md`
   - `scripts/quality_chain_controller.sh bootstrap --mode full ...`
   - `LLM_QUALITY_CHAIN_ROOT=/tmp/a922-proof/chain-canary scripts/quality_chain_controller.sh bootstrap --mode canary ... --exit-code 1`
3. Explicit statement of proof strength and proof limits.

## Generated Artifacts
- Shadow diff report: `/tmp/a922-proof/shadow_report.md`
- Full canonical release evidence: `/tmp/a922-proof/booking-full-proof/release_gate.json`
- Canary rollback release evidence: `/tmp/a922-proof/booking-canary-proof/release_gate.json`
- Canary rollback payload: `/tmp/a922-proof/booking-canary-proof/rollback.json`

## Program-Level Conclusion
By factual code audit, the target program shape is implemented:
- one semantic owner on the hot path,
- one typed binding boundary,
- one canonical state substrate,
- planner/executor demoted off semantic/control co-ownership,
- legacy mesh reduced to compatibility-only residue,
- durable execution separated into a shared action-plane owner,
- governed snapshot owners added for growth seams,
- and machine-readable proof/release artifacts now exist.

What this report proves strongly:
- structural authority removal,
- final active-path contract shape,
- final proof/release artifact shape.

What this report does **not** prove by itself:
- broad realistic quality across many live dialogs/packs,
- absence of all hidden regressions outside the audited seams,
- performance/concurrency behavior,
- production rollout safety without the existing acceptance process.

## Workstream Matrix

### Workstream 1 — Semantic Owner Extraction
**Claim proved by code**
- `SemanticDecisionV1` is the hot-path meaning artifact: `truffles-api/app/core/semantic_decision.py:171`
- planner rejects missing owner output: `truffles-api/app/core/turn_planner.py:818`, `truffles-api/app/core/turn_planner.py:840`
- planner/runtime guard post-owner mutation explicitly: `truffles-api/app/core/turn_planner.py:466`, `truffles-api/app/core/consultant_runtime.py:600`
- executor/state use bounded `semantic_enrichment` rather than semantic rewrite: `truffles-api/app/core/turn_executor.py:866`, `truffles-api/app/core/consultant_runtime.py:725`, `truffles-api/app/core/dialog_state_service.py:970`

**Artifact proof**
- indirect but strong through final active-path trace shape:
  - `RuntimeTraceContractV1.owner_transition` exists: `truffles-api/app/core/runtime_trace_contract.py:77`
  - active runtime writes it: `truffles-api/app/core/consultant_runtime.py:1327`, `truffles-api/app/core/consultant_runtime.py:1448`
- the generated shadow replay report shows owner/binding/state transitions as first-class audit surfaces, not flat legacy meta only: `/tmp/a922-proof/shadow_report.md`

**Limit without deterministic tests**
- this does not by itself prove every old semantic-rewrite edge-case is unreachable on every historical path.

### Workstream 2 — Binding Boundary Extraction
**Claim proved by code**
- typed binding exists: `truffles-api/app/core/binding_plan.py:18`
- planner requires binding for semantic and synthetic decisions: `truffles-api/app/core/turn_planner.py:85`, `truffles-api/app/core/turn_planner.py:87`
- projector builds binding from the owner path: `truffles-api/app/core/policy_tool_projector.py:261`
- executor routes by `binding_outcome_type`, not free-form planner shaping: `truffles-api/app/core/turn_executor.py:251`, `truffles-api/app/core/turn_executor.py:255`, `truffles-api/app/core/turn_executor.py:277`
- runtime collect/handoff predicates read binding first: `truffles-api/app/core/consultant_runtime.py:1505`, `truffles-api/app/core/consultant_runtime.py:1513`, `truffles-api/app/core/consultant_runtime.py:1517`

**Artifact proof**
- direct and strong through generated shadow replay:
  - `binding_transition.selected_tool_or_workflow_ref` is scored separately in `/tmp/a922-proof/shadow_report.md`
- full runtime trace contract shape includes binding fields: `truffles-api/app/core/runtime_trace_contract.py:149`-`truffles-api/app/core/runtime_trace_contract.py:161`

**Limit without deterministic tests**
- this does not by itself prove every dormant compatibility caller stopped fabricating legacy binding payloads.

### Workstream 3 — Canonical State Unification
**Claim proved by code**
- typed journal exists: `truffles-api/app/core/turn_journal.py:47`
- typed primary read model exists: `truffles-api/app/core/conversation_projection.py:10`
- dialog state service normalizes and emits both: `truffles-api/app/core/dialog_state_service.py:259`, `truffles-api/app/core/dialog_state_service.py:269`, `truffles-api/app/core/dialog_state_service.py:3231`, `truffles-api/app/core/dialog_state_service.py:3232`
- context projections read projection-first for goal/question: `truffles-api/app/core/dialog_state_service.py:1484`, `truffles-api/app/core/dialog_state_service.py:1634`
- continuity writer guard now centers on governed core (`scripts/continuity_writer_guard.py`; allowlist collapsed in `docs/LEGACY_SUNSET.yaml`)

**Artifact proof**
- strong through final runtime trace contract:
  - `state_transition.journal_last_turn_id` and `journal_event_types`: `truffles-api/app/core/runtime_trace_contract.py:200`
- generated shadow replay report includes state-transition drift at canonical paths such as `/state_transition/current_goal`

**Limit without deterministic tests**
- this does not by itself prove there is no stale compatibility read on every dormant path outside the audited active runtime surface.

### Workstream 4 — Planner / Executor Demotion
**Claim proved by code**
- executor dispatch is binding-driven: `truffles-api/app/core/turn_executor.py:251`-`truffles-api/app/core/turn_executor.py:279`
- boundary request carriers do not shape planner action anymore: `truffles-api/app/core/turn_executor.py:79`, `truffles-api/app/core/turn_executor.py:95`
- synthetic planner boundaries are fixed-shape builders: `truffles-api/app/core/turn_planner.py:690`, `truffles-api/app/core/turn_planner.py:724`
- runtime handoff/collect predicates are binding-only: `truffles-api/app/core/consultant_runtime.py:1505`, `truffles-api/app/core/consultant_runtime.py:1513`, `truffles-api/app/core/consultant_runtime.py:1517`

**Artifact proof**
- indirect through final trace contract:
  - `action_transition.contract_action` and `binding_transition.binding_outcome_type` are present and emitted by runtime, which is consistent with planner/executor demotion
- final active-path proof surfaces no longer depend on free-form planner/executor compatibility shaping

**Limit without deterministic tests**
- runtime artifacts prove the final emitted shape, but not every internal planner/executor branch that could still be dormant.

### Workstream 5 — Legacy Mesh Strangler
**Claim proved by code**
- live router/service seams no longer call `decision_router.*` or `_decision_runtime(...)`:
  - `rg -n "_decision_runtime|decision_router\." truffles-api/app/routers/webhook/*.py truffles-api/app/services/*.py` -> no matches
- remaining app imports of `decision.py` are narrowed to compatibility package residue:
  - `truffles-api/app/routers/webhook/__init__.py:41`
  - `truffles-api/app/routers/webhook/_legacy.py:67`

**Artifact proof**
- mostly structural, not artifact-first.
- final runtime proof artifacts do not expose import graphs, so the strongest evidence here is the code graph itself.

**Limit without deterministic tests**
- this is the clearest case where code proof is stronger than runtime artifact proof.
- without guards/tests, hidden dead-code importers could still exist outside the searched surfaces.

### Workstream 6 — Durable Action Plane
**Claim proved by code**
- one concrete outbox executor remains: `truffles-api/app/services/outbox_runtime_service.py:794`
- live entrypoints call the shared owner:
  - `truffles-api/app/routers/outbox_service.py:10`
  - `truffles-api/app/routers/admin.py:27`
  - `truffles-api/app/routers/console.py:74`
  - `truffles-api/app/workers/outbox.py:8`
- legacy webhook outbox path is a shim over the shared owner: `truffles-api/app/routers/webhook/outbox.py:5`

**Artifact proof**
- indirect only in this audit.
- release-gate artifacts prove the quality chain is now machine-readable, but they do not prove outbox choreography directly.

**Limit without deterministic tests**
- this does not prove worker-loop behavior under load or long-running retries.

### Workstream 7 — Minimum Control Plane
**Claim proved by code**
- routing snapshot owner: `truffles-api/app/services/policy_snapshot_service.py`
- tool registry snapshot owner: `truffles-api/app/services/tool_registry_snapshot_service.py`
- context recipe snapshot owner: `truffles-api/app/services/policy_context_snapshot_service.py`
- vocabulary snapshot owner: `truffles-api/app/services/policy_vocabulary_snapshot_service.py`
- prompt snapshot owners: `truffles-api/app/services/policy_prompt_snapshot_service.py`, `truffles-api/app/services/controller_plan_prompt_snapshot_service.py`
- capability registry snapshot owner: `truffles-api/app/services/capability_registry_snapshot_service.py`
- hotspots now import them:
  - `truffles-api/app/routers/webhook/policy.py:28`
  - `truffles-api/app/core/policy_tool_projector.py:9`
  - `truffles-api/app/services/intent_service.py:2050`, `truffles-api/app/services/intent_service.py:2100`
  - `truffles-api/app/services/capability_manifest_service.py:5`

**Artifact proof**
- mostly structural.
- final runtime artifacts do not enumerate governance owners directly; they prove the resulting runtime path, not the growth-control compile path.

**Limit without deterministic tests**
- this does not prove all future growth will respect the new governance owners; that requires guards and review discipline.

### Workstream 8 — Observability, Proof, and Release Gates
**Claim proved by code**
- typed runtime trace exists: `truffles-api/app/core/runtime_trace_contract.py:77`
- runtime emits canonical trace contract: `truffles-api/app/core/consultant_runtime.py:1327`, `truffles-api/app/core/consultant_runtime.py:1448`
- shadow diff scoring exists: `ops/shadow_replay.py:156`, `ops/shadow_replay.py:340`
- machine-readable release-gate contract exists: `contracts/runtime/release_gate_evidence.v1.jsonschema:21`
- chain controller writes `release_gate.json`: `scripts/quality_chain_controller.sh:1231`, `scripts/quality_chain_controller.sh:1234`, `scripts/quality_chain_controller.sh:1672`, `scripts/quality_chain_controller.sh:1877`, `scripts/quality_chain_controller.sh:1967`

**Artifact proof**
- direct and strong:
  - `/tmp/a922-proof/shadow_report.md` shows `runtime_trace_contract.shadow_score: 0.9221` and JSON-pointer mismatches
  - `/tmp/a922-proof/booking-full-proof/release_gate.json` shows canonical acceptance evidence with `decision="accept"`
  - `/tmp/a922-proof/booking-canary-proof/release_gate.json` shows rollback evidence with `decision="rollback_executed"` and embedded rollback payload

**Limit without deterministic tests**
- these artifacts prove that the proof/release machinery runs and emits the right shape on the audited scenarios, but not that every future chain input or runtime trace shape is regression-free.

## What Is Proven Strongly Without Deterministic Tests
- The final code structure matches the intended architecture.
- The active proof lane now emits machine-readable observability and release artifacts.
- The end-state runtime contract shape reflects one semantic owner, one binding boundary, and one canonical state substrate.

## What Is Not Fully Proven Without Deterministic Tests
- No hidden regression on untouched paths.
- No hidden dormant importer/consumer outside searched seams.
- No cross-pack/open-world robustness.
- No performance or concurrency regressions.
- No realistic booking-quality acceptance outcome.

## Honest Final Statement
Without deterministic tests, I can prove the **implemented structural end-state** and the **existence of executable proof/release artifacts**.
I cannot honestly prove full behavioral correctness across the whole system without the deterministic layer and realistic acceptance layer.
