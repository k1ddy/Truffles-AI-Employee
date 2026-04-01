# Consultant Core External Research Prompt

Archive-layer note: do not send this archived prompt as the current outside packet. Current outside-send readiness is still blocked by `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`.

Use this prompt together with the attached/internal source pack only as archive material.

## Role
You are acting as an external principal architect and research analyst.

Your job is not to confirm our current direction. Your job is to challenge it where needed and propose the strongest target architecture and migration strategy for the system described below.

You must reason from two inputs at the same time:
- repo-backed forensic evidence about the current system,
- and current real-world architecture patterns, tooling, standards, and operating models for agentic systems, control planes, observability, governance, proof/evals, and scalable platform evolution.

## Mission
Design a target architecture and operating model for a production-grade semantic operating system that can scale and evolve in many directions without recreating the current failure classes.

The research must optimize for:
- semantic integrity,
- architectural changeability,
- control-plane governance,
- operational observability,
- proofability and release safety,
- and realistic migration from the current codebase.

Do not optimize only for “smarter runtime behavior”.
Optimize for long-term safe evolution under governance.

## Source Pack To Read First
Treat the following as required reading.

### Internal Forensic Corpus
1. `docs/system_forensics/final/RESEARCH_BRIEF.md`
2. `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`
3. `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`
4. `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
5. `docs/system_forensics/ledgers/CONTROL_PATHS.md`
6. `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
7. `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
8. `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
9. `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
10. the hotspot analyses listed in `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`

### External Framing Materials
1. `/home/zhan/career_prep/Career-prep-reserach1.md`
2. `/home/zhan/career_prep/Introduction to Agents.pdf`

Use these external framing materials to widen the design space, not to force a predetermined answer.

## Current System Context
The current system is a consultant runtime that historically accumulated too much semantic and control-path authority across multiple layers.

Repo-backed findings already show:
- the active runtime spine is currently `consultant_core_v2 -> consultant_runtime -> turn_planner -> intent_service -> turn_executor -> dialog_state_service`;
- `consultant_core_v2` is not yet a real extracted runtime module-set;
- one canonical semantic owner is not yet fully achieved;
- one canonical semantic state is not yet fully achieved;
- the deterministic layer is not yet a pure boundary layer;
- a large legacy compatibility mesh is still live (`_legacy.py`, `decision.py`, `context_manager.py`, `response.py`, `booking.py`, `info.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`);
- growth is not yet fully centered on manifests/registries/policies/data packs;
- operational and outbox surfaces still contain duplicated entrypoints and compatibility seams.

You should not spend your time rediscovering those facts from scratch. Use them as the starting point.

## Core Problem To Solve
We do not want a system that becomes correct only for the current set of surfaced failures.
We want a system that remains scalable, governable, and evolvable across many future dimensions.

The architecture must be able to grow safely across:
- new domains,
- new tools/capabilities,
- new tenants/branches/geographies/regulatory envelopes,
- new models and routing strategies,
- new channels and UI modes,
- new agent topologies,
- new safety and policy regimes,
- new proof/evaluation regimes,
- new load and cost profiles,
- new human workflows and escalation workflows.

The architecture is weak if growth along those axes forces repeated runtime-core rewrites or reintroduces semantic drift.

## What The Research Must Determine
You must determine:
1. what target runtime architecture best satisfies one owner / one state / one control path while remaining extensible;
2. what minimal sufficient level of agenticity is appropriate in the online runtime;
3. where multi-agent collaboration helps and where it should be forbidden or tightly bounded;
4. what the canonical semantic state should look like in a scalable system;
5. how meaning, capability selection, tool binding, execution, persistence, and degrade should be separated;
6. what the control plane should look like for capabilities, tools, agents, policies, identity, lifecycle, and governance;
7. how dynamic context assembly should work without giant-prompt sprawl;
8. what proof/evaluation/observability architecture should exist;
9. what migration strategy is realistic from the current codebase;
10. what first extraction block gives the highest architectural leverage.

## Required Architectural Lens
You must analyze the target system as at least three separate planes.

### 1. Online Runtime Plane
This is the hot path of each user turn.
It should cover:
- semantic owner,
- canonical semantic state,
- capability selection,
- tool binding,
- execution,
- degrade/handoff,
- turn-level trace.

### 2. Control Plane / Governance Plane
This is what allows the system to grow without sprawl.
It should cover:
- capability registry,
- agent/tool catalog,
- policy registry,
- identity and authorization,
- lifecycle/versioning,
- inventory/discovery,
- rollout and approval,
- quotas/guardrails.

### 3. Offline Improvement Plane
This is what allows the system to improve without corrupting the runtime path.
It should cover:
- evaluation datasets,
- synthetic data,
- simulation,
- critique/review loops,
- prompt/context optimization,
- model-routing experiments,
- red-teaming and stress,
- offline multi-agent experimentation,
- agent gym style optimization if justified.

Explain what belongs to each plane and why.

## Non-Negotiable Constraints
Any proposed architecture must respect these constraints.

1. Deterministic layers must not become hidden semantic owners.
2. Core runtime must not depend on phrase/regex branching as the semantic engine.
3. Domain growth must not require core hardcoded branching as the default model.
4. The architecture must stay observable and auditable.
5. Degrade paths must be explicit, reason-coded, and non-default.
6. The production contract must not depend on inaccessible raw chain-of-thought.
7. Multi-agent proposals must not create opaque co-ownership of meaning.
8. Governance is mandatory; runtime reasoning alone is insufficient.
9. Migration realism is mandatory; greenfield elegance alone is insufficient.
10. The proposal must reduce proven failure classes, not merely rename them.

## Open To Challenge
You are explicitly allowed to challenge:
- current module names,
- current package boundaries,
- the current planner/executor/state-service split,
- whether `turn_planner` should survive long-term,
- whether `turn_executor` should survive long-term,
- whether `consultant_core_v2` is the correct top-level shape,
- how much of the legacy webhook mesh should be salvaged versus deleted,
- which runtime and control-plane frameworks or patterns are better suited.

Do not assume current decomposition is correct merely because it exists.

## Required External Research Scope
Your work must include current real-world patterns and implementations, not only abstract ideas.

Cover at least:
- agent/runtime orchestration patterns,
- canonical-state or event-log patterns,
- capability/tool registry patterns,
- control-plane/governance patterns,
- observability and causal tracing patterns,
- proof/evaluation systems for LLM and agent runtimes,
- migration/cutover/strangler patterns,
- security and policy enforcement patterns,
- multi-agent coordination patterns and failure modes,
- offline simulation / agent gym / synthetic stress systems.

## Important Guidance On Multi-Agent And CoT
You should evaluate multi-agent seriously, but rigorously.

If you recommend multi-agent behavior:
- specify whether it belongs in the online runtime plane, control plane, or offline improvement plane;
- explain how semantic ownership remains auditable;
- explain how governance and observability remain tractable;
- explain how it avoids becoming agent sprawl.

Do not base the production architecture on raw chain-of-thought availability.
If deeper reasoning artifacts are needed, propose auditable substitutes such as:
- structured reasoning artifacts,
- decision summaries,
- reason codes,
- critique summaries,
- trajectory traces,
- typed planner/supervisor outputs.

## What A Strong Answer Must Provide
A strong answer must:
- use the repo-backed evidence correctly,
- add new external knowledge and options we do not already have,
- compare multiple target architectures,
- explain trade-offs clearly,
- propose a realistic migration strategy,
- identify where multi-agent helps and where it harms,
- define a governance/control-plane model,
- define proof/eval/observability expectations,
- and specify a first extraction block.

A weak answer will:
- repeat our own documents back to us,
- ignore governance/control-plane concerns,
- recommend a full rewrite without migration strategy,
- recommend opaque agent sprawl,
- or fail to map design choices back to proven failure classes.

## Output Format
Return your answer in the structure required by:
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`

At minimum your response must include:
1. executive verdict;
2. current-system interpretation check;
3. 2-4 architecture options;
4. comparative decision matrix;
5. recommended target architecture;
6. expansion matrix across major growth axes;
7. migration strategy;
8. first extraction block;
9. salvage / adapter / shadow / delete matrix;
10. governance and control-plane proposal;
11. observability / proof / agent-ops proposal;
12. rejected alternatives;
13. residual unknowns;
14. source discipline and citations.

## Decision Standard
We will judge your work by whether it improves the system’s ability to evolve safely under governance.

The winning architecture is not the one that sounds most advanced.
The winning architecture is the one that best preserves:
- semantic integrity,
- control integrity,
- proofability,
- governance,
- and future extensibility,
while still being realistically migratable from the current system.

## Final Instruction
Do not confirm our current assumptions unless the evidence and the external landscape justify them.
Bring us options, trade-offs, risks, and migration logic that we may not currently see.
