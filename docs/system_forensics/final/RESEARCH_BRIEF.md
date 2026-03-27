# Consultant Core External Research Brief

Status: `open`
Purpose: define the external research problem so reviewers can propose better target architectures and migration strategies than the current team can see from inside the codebase.

## What This Brief Is
This is a research contract, not an implementation plan.

It exists to:
- summarize what is already proven from the repo,
- define the target properties of the future system,
- state non-negotiable constraints,
- identify the design space that remains open to challenge,
- and require a concrete research output that can drive future architecture work.

This brief should be read together with:
- `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`

## Research Mission
Design a target architecture and operating model for a production-grade semantic operating system that can scale and evolve in many directions without reintroducing the current failure classes.

The research must optimize for:
- semantic integrity,
- architectural changeability,
- control-plane governance,
- observability and proofability,
- operational safety,
- and realistic migration from the current codebase.

The research must not optimize only for "smarter runtime behavior". It must optimize for safe long-term evolution under governance.

## Current Proven Facts
These are already repo-backed and should not be re-discovered from scratch.

1. The active core control path is currently centered on:
- `consultant_core_v2 -> consultant_runtime -> turn_planner -> intent_service -> turn_executor -> dialog_state_service`

2. `consultant_core_v2` is not yet an extracted runtime module-set.
- It is still a wrapper/cutover contour around `consultant_runtime`.

3. The system does not yet have one canonical semantic owner in the strong architectural sense.
- semantic shaping/reconstruction still exists downstream of the owner path.

4. The system does not yet have one canonical semantic state.
- `DialogStateService` materializes canonical state, but multiple other continuity/truth carriers still exist.

5. The deterministic/runtime layer is not yet a pure boundary layer.
- planner/executor/context bridges still reconstruct or rewrite meaning-carrying artifacts.

6. A large legacy compatibility mesh remains live outside the desired target path.
- `_legacy.py`, `decision.py`, `context_manager.py`, `response.py`, `booking.py`, `info.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`

7. Growth architecture is not yet fully manifest/registry-centered.
- active semantic and orchestration logic still coexists with code-level heuristics and legacy domain branching residue.

8. Outbox and operational caller surfaces remain partially duplicated.
- service/admin/worker/console still keep wrapper/export seams alive around `_process_outbox_rows`.

Primary evidence:
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

## Proven Failure Classes
The target research must explicitly address these system-level failures.

1. Semantic meaning is distributed across multiple places.
2. Downstream stages can still reshape or reconstruct meaning after the owner boundary.
3. Multiple truth-carriers require reconciliation and create continuity debt.
4. Legacy compatibility paths still hold operational authority.
5. Core growth still tends to couple to code branching instead of manifests/registries.
6. Control paths and operational entrypoints are duplicated.
7. Runtime evolution and offline learning/improvement are not cleanly separated.
8. Current architecture is difficult to govern as a platform.

## Target System Properties
A strong proposal should produce a system with these properties.

1. One auditable semantic owner per user turn, or a rigorously justified equivalent that preserves the same guarantees.
2. One canonical semantic state with explicit projections and no hidden peer truths.
3. One clear online control path for runtime execution.
4. Growth through manifests, registries, policies, schemas, and data packs rather than core branching.
5. Separation between meaning selection, capability selection, tool binding, execution, persistence, and degrade.
6. Strong observability with turn-level causal traceability.
7. Proof-oriented evaluation and release gates, not only ad hoc tests.
8. Clean governance over agents, tools, capabilities, policies, versions, and access.
9. Safe extensibility across domains, tenants, channels, models, and workflows.
10. A realistic migration path from the current system without a blind rewrite.

## Non-Negotiables
Any research proposal that violates these should be rejected.

1. Deterministic layers must not become hidden semantic owners.
2. Core runtime must not rely on phrase/regex branching as the semantic engine.
3. Domain growth must not require core hardcoded branching as the default extension path.
4. The architecture must remain observable and auditable.
5. Degrade paths must be explicit, reason-coded, and non-default.
6. The architecture must not depend on inaccessible raw chain-of-thought as a production contract.
7. Multi-agent proposals must not create opaque co-ownership of meaning.
8. The proposal must include governance, not only runtime reasoning.
9. The proposal must include migration realism, not only greenfield elegance.
10. The proposal must reduce, not rename, the current failure classes.

## Open To Challenge
These are explicitly open to redesign.

1. Current module boundaries and filenames.
2. The current decomposition into planner/executor/state service.
3. Whether `turn_planner` survives as a distinct long-term boundary.
4. Whether `turn_executor` survives as a distinct long-term boundary.
5. Whether `consultant_core_v2` remains the right top-level package shape.
6. How much of the legacy webhook stack is salvaged versus deleted.
7. Which agent topology is best, provided semantic and governance invariants remain satisfied.
8. Which framework stack is best, provided it is migration-realistic and avoids lock-in traps.

## Architectural Lens Required From Research
The research must reason about the system as at least three separate planes.

1. Online Runtime Plane
- what lives on the hot path of each user turn
- semantic owner
- canonical state
- capability selection
- tool binding
- execution
- degrade/handoff
- turn trace

2. Control Plane / Governance Plane
- capability registry
- agent/tool catalog
- policy registry
- identity and authorization
- versioning/lifecycle
- rollout rules
- approval and inventory
- quotas and governance

3. Offline Improvement Plane
- evaluation
- synthetic data
- simulation
- critique/review loops
- prompt/context optimization
- model-routing experiments
- red-teaming and stress testing
- offline multi-agent experimentation

Research should explain what belongs to each plane and why.

## Required Scalability Axes
The proposal must explain how the architecture scales along these axes without forcing recurring core rewrites.

1. new domain
2. new capability/tool
3. new tenant/branch/geography/regulatory envelope
4. new model or model-routing strategy
5. new channel or UI mode
6. new agent topology
7. new safety/policy regime
8. new observability/proof requirements
9. new load/cost profile
10. new human workflow or escalation pattern

## Key Research Questions
The response should answer these directly.

1. What target runtime architecture best satisfies one owner / one state / one control path while remaining extensible?
2. What is the minimal sufficient level of agenticity for the online runtime?
3. Where, if anywhere, is multi-agent collaboration appropriate without violating semantic ownership and auditability?
4. How should orchestration be modeled: state machine, workflow engine, event-driven runtime, supervisor, or another form?
5. What should the canonical semantic state look like in a scalable system?
6. How should meaning, capability selection, tool binding, execution, persistence, and degrade be separated?
7. What should the control plane look like for capabilities, tools, agents, policies, and lifecycle governance?
8. How should dynamic context assembly replace giant prompt growth over time?
9. What should the proof/evaluation architecture look like for online and offline safety?
10. What migration strategy is most realistic from the current repo-backed state?
11. What first extraction block would produce the highest architectural leverage?
12. Which current components are salvage, adapter-only, shadow-only, or delete candidates?

## Mandatory External Research Coverage
The research must include real current-world patterns and implementations, not only abstract reasoning.

Cover at least these areas:
- agent/runtime orchestration patterns
- event-sourced or canonical-state patterns
- capability/tool registry patterns
- control plane and governance patterns
- observability and causal tracing for agentic systems
- evaluation/proof systems for LLM/agent runtime
- progressive rollout and migration patterns
- security and policy enforcement patterns
- multi-agent coordination patterns and their failure modes
- offline simulation / agent gym / synthetic stress systems

## Evaluation Standard For Research Output
A strong response must:
- use our repo facts correctly,
- add new external knowledge we do not already have,
- compare multiple target architectures,
- explain trade-offs clearly,
- propose a concrete migration path,
- explain where multi-agent helps and where it harms,
- define governance/control-plane implications,
- and specify a first extraction block.

A weak response will:
- merely repeat our own documents,
- ignore governance/control-plane concerns,
- recommend a full rewrite without migration strategy,
- recommend opaque multi-agent sprawl,
- or fail to map design choices back to proven failure classes.

## Deliverables Required From Researchers
Researchers must return output in the format defined by:
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`

At minimum the returned output must include:
- architecture option set,
- comparative trade-off matrix,
- recommended target architecture,
- plane separation,
- governance model,
- proof/evaluation model,
- migration strategy,
- first extraction block,
- delete/demote/salvage map,
- rejected alternatives,
- residual uncertainties.

## Primary Internal Evidence Pack
Start here:
- `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`

## External Framing Sources Already Selected
These are not the answer; they are framing material.

- `/home/zhan/career_prep/Career-prep-reserach1.md`
- `/home/zhan/career_prep/Introduction to Agents.pdf`

Why they matter:
- the first pushes production realism, standards, control planes, observability, rollout, SLOs, governance, and platform thinking;
- the second pushes the separation of model/tools/orchestration, agent ops, governance via control planes, and separation between runtime and self-improvement.
