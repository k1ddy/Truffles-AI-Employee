# Consultant Core Implementation Program

Status: `open`
Purpose: record the archive-only implementation hypothesis that was derived from the older target decision. It is no longer allowed to restart runtime work by itself.

Archive-layer note: this is an archive-only implementation hypothesis. Current implementation remains blocked until the outside-readiness blockers named in `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md` are closed.

## Program Rule
Every workstream must reduce old authority, not merely move code.

A block does **not** count as progress if it only:
- renames modules,
- adds wrappers,
- adds observability without authority reduction,
- adds tests without changing authority,
- or improves old planner/executor/state behavior without shrinking their semantic role.

## Program Sequence
There are eight bounded workstreams.

### Workstream 1 — Semantic Owner Extraction
Objective:
- make `SemanticDecisionV1` the only hot-path meaning artifact

Primary result:
- one owner writes semantic meaning once per turn

Primary authority removed:
- planner/executor/state layers stop re-authoring meaning

Main files/subsystems likely involved:
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/policy_tool_projector.py`

Completion criteria:
1. exactly one `SemanticDecisionV1` per canaried turn
2. no downstream mutation of semantic owner fields
3. owner output contains no concrete `tool_args`
4. legacy owner-adjacent paths are shadow-only or deleted

Blocked by:
- missing `SemanticDecisionV1` contract

### Workstream 2 — Binding Boundary Extraction
Objective:
- separate binding from meaning via `BindingPlanV1`

Primary result:
- capability -> authorized tool/workflow/handoff becomes a deterministic boundary

Primary authority removed:
- executor/planner no longer choose or reinterpret capability through binding logic

Main files/subsystems likely involved:
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/app/core/turn_executor.py`
- tool/workflow adapters

Completion criteria:
1. binding consumes `SemanticDecisionV1` only
2. binding may resolve args/authz/timeouts but may not change capability meaning
3. direct `tool_args` semantic ownership disappears from owner contract
4. deny/handoff outcomes are explicit and typed

Blocked by:
- Workstream 1
- missing `BindingPlanV1` contract

### Workstream 3 — Canonical State Unification
Objective:
- make `TurnJournalV1 + ConversationProjectionV1` the only canonical semantic state substrate

Primary result:
- state has one system of record and one primary read model

Primary authority removed:
- peer truth-carriers and state-side semantic reconstruction

Main files/subsystems likely involved:
- `truffles-api/app/core/dialog_state_service.py`
- compatibility readers/writers
- state persistence layer

Completion criteria:
1. journal append law exists and is enforced
2. one primary projection is used by runtime
3. compatibility surfaces become derived views only
4. no independent peer semantic truths remain on the active path

Blocked by:
- Workstream 1
- missing `TurnJournalV1` and `ConversationProjectionV1` contracts

### Workstream 4 — Planner / Executor Demotion
Objective:
- shrink `turn_planner` and `turn_executor` to adapter/execution roles

Primary result:
- planner is no longer a semantic shaper
- executor is no longer a semantic rebuilder

Primary authority removed:
- synthetic degrade/preflight meaning reconstruction
- semantic contract rebuilding
- info->tool remapping as a meaning choice

Main files/subsystems likely involved:
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`

Completion criteria:
1. planner only adapts ingress/context and reads owner output
2. executor only executes binding/action outcomes
3. post-owner mutation guard remains green

Blocked by:
- Workstreams 1-3

### Workstream 5 — Legacy Mesh Strangler
Objective:
- remove semantic/control authority from the legacy compatibility mesh

Primary result:
- legacy modules become adapter-only, shadow-only, or deleted

Primary authority removed:
- `_legacy.py`
- `decision.py`
- `context_manager.py`
- `response.py`
- `booking.py`
- `info.py`
- `pending.py`
- `policy.py`
- `guards.py`
- `dedup.py`

Completion criteria:
1. no live semantic authority remains in legacy mesh
2. all surviving legacy surfaces are adapter-only or shadow-only
3. delete candidates have no live callers

Blocked by:
- Workstreams 1-4
- runtime caller evidence for delete safety

### Workstream 6 — Durable Action Plane
Objective:
- separate action sagas and long-running execution from the semantic kernel

Primary result:
- workflows/outbox/side-effect coordination become execution-plane concerns

Primary authority removed:
- chat semantic runtime stops carrying long-running action orchestration as meaning logic

Main files/subsystems likely involved:
- outbox service/admin/worker/console seams
- workflow start/advance runtime

Completion criteria:
1. long-running actions use one durable execution model
2. duplicated `_process_outbox_rows` seams are removed or unified
3. semantic kernel starts workflows, not owns their business choreography

Blocked by:
- Workstream 2
- partial Workstream 3

### Workstream 7 — Minimum Control Plane
Objective:
- create the smallest governance plane that prevents runtime-core growth through branching

Primary result:
- runtime consumes compiled registry/policy/context snapshots

Phase-1 scope only:
- capability registry
- tool/workflow registry
- policy packs
- context recipes

Completion criteria:
1. phase-1 registry objects exist and are versioned
2. runtime reads compiled snapshots instead of scattered ad hoc constants
3. new capability/tool additions no longer require core semantic branching by default

Blocked by:
- Workstreams 1-2

### Workstream 8 — Observability, Proof, and Release Gates
Objective:
- make architecture behavior observable, evaluable, and governable during migration

Primary result:
- authority changes are verified by evidence, not narrative

Completion criteria:
1. trace contract covers owner/binding/action/state transitions
2. post-owner mutation guard exists
3. shadow diff scoring exists
4. canary/go-no-go/rollback evidence is standardized

Blocked by:
- Workstreams 1-3 at minimum

## Dependency Order
1. Workstream 1
2. Workstream 2
3. Workstream 3
4. Workstream 4
5. Workstream 5
6. Workstream 6
7. Workstream 7
8. Workstream 8

Allowed overlap:
- Workstream 8 may start partially once Workstream 1 artifacts exist
- Workstream 7 may start minimally once Workstream 2 shapes are stable

## Program-Level Done Criteria
The program is `done` only when all of the following are true:
1. one semantic owner on the hot path
2. one canonical semantic state
3. one control path
4. planner/executor/state layers are no longer semantic co-owners
5. legacy compatibility mesh has no semantic authority
6. growth happens through governed registries/policies/context packs, not semantic core branching
7. durable execution is separated from semantic ownership
8. release decisions are backed by trace/eval/governance evidence

## What Does Not Count As Program Completion
1. wrapper renames
2. adding more compatibility bridges
3. adding more tests while authority stays the same
4. adding more prompts/cards without governance or contracts
5. moving logic between planner and executor without removing their semantic power

## Next Concrete Move
The next implementation TP must start Workstream 1 and must reference:
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
