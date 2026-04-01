# Consultant Core Research Source Pack

Status: `open`
Purpose: tell external researchers exactly what to read first, why it matters, and how to avoid losing time in the full corpus.

## Reading Order

### Tier 1: Mandatory First Read
1. `docs/system_forensics/final/RESEARCH_BRIEF.md`
- defines the problem correctly
- defines non-negotiables and open design space

2. `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- gives the highest-level repo-backed synthesis
- shows what is already proven and what remains unknown

3. `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- shows the actual active and compatibility control paths

4. `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- shows where semantic authority currently lives and where it leaks

5. `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- shows current competing truth surfaces

6. `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- shows where deterministic layers still reshape meaning

7. `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- shows real blockers for migration and demotion

### Tier 2: Mandatory Hotspot Files
1. `docs/system_forensics/files/app_core_consultant_runtime.md`
- proves the active runtime still lives in `consultant_runtime.py`

2. `docs/system_forensics/files/app_core_dialog_state_service.md`
- proves state/continuity authority is concentrated in a megaservice and not yet canonicalized cleanly

3. `docs/system_forensics/files/app_services_intent_service.md`
- shows the owner gateway, context assembly, and residual semantic helper co-location

4. `docs/system_forensics/files/app_core_turn_planner.md`
- shows post-owner shaping at the planner seam

5. `docs/system_forensics/files/app_core_turn_executor.md`
- shows post-owner reconstruction at execution time

6. `docs/system_forensics/files/app_routers_webhook_legacy.md`
- shows the compatibility import bus that keeps frozen surfaces alive

7. `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- shows the state-side compatibility bridge

8. `docs/system_forensics/files/app_routers_webhook_response.md`
- shows user-visible fallback/orchestration residue

9. `docs/system_forensics/files/app_routers_webhook_booking.md`
- shows booking-domain compatibility authority

10. `docs/system_forensics/files/app_routers_webhook_info.md`
- shows info-domain compatibility authority

### Tier 3: Supplemental Repo Evidence
Use as needed.

- `docs/system_forensics/files/app_services_reasoning_core.md`
- `docs/system_forensics/files/app_core_booking_prompt_owner.md`
- `docs/system_forensics/files/app_webhook.md`
- `docs/system_forensics/files/app_main.md`
- `docs/system_forensics/files/app_routers_webhook_init.md`
- `docs/system_forensics/files/app_routers_webhook_pending.md`
- `docs/system_forensics/files/app_routers_webhook_policy.md`
- `docs/system_forensics/files/app_routers_webhook_guards.md`
- `docs/system_forensics/files/app_routers_webhook_dedup.md`
- outbox/admin/worker/console slices under `docs/system_forensics/files/`

## External Framing Sources
These are meant to expand the design space, not constrain it to our current decomposition.

### 1. Production/Platform Framing
- `/home/zhan/career_prep/Career-prep-reserach1.md`

Use it for:
- production realism
- control-plane/platform thinking
- standards-based design
- observability and SLOs
- progressive delivery
- governance
- operating a system as a product platform, not just a codebase

High-value themes already extracted from it:
- GitOps / declarative control
- OpenTelemetry as standard telemetry backbone
- control-plane thinking via Backstage/Crossplane analogy
- SLO/error-budget/chaos/progressive delivery
- measurable business/system outcomes instead of toy demos

### 2. Agent/Runtime Framing
- `/home/zhan/career_prep/Introduction to Agents.pdf`

Use it for:
- model / tools / orchestration separation
- levels of agenticity and when not to overbuild
- multi-agent design patterns and their risks
- agent ops and evaluation
- governance and control-plane thinking for agents
- separation between online runtime and offline improvement/self-evolution

High-value themes already extracted from it:
- minimal sufficient agenticity
- orchestration layer as central nervous system
- LM + tools + orchestration triad
- quality via metrics + LM judge + human feedback
- OpenTelemetry traces for debugging trajectories
- control plane instead of agent sprawl
- runtime versus offline improvement plane (`Agent Gym` idea)

## What Researchers Should Assume As Already Proven
1. The current system is not blocked by lack of local bugfixes; it is blocked by architecture.
2. The current active path is known well enough to start target-architecture work.
3. The main unresolved issue is not discovery of control paths; it is choosing the best target architecture and migration strategy.
4. Current module names are not sacred.
5. The final answer must be judged by future extensibility under governance, not only by short-term correctness.

## What Researchers Should Not Over-Index On
1. Current package names such as `consultant_core_v2`.
2. The assumption that planner/executor/state service must survive unchanged.
3. The assumption that multi-agent is automatically the best answer.
4. The assumption that multi-agent is forbidden everywhere.
5. The assumption that a single giant runtime file must remain the backbone.
6. The assumption that the current webhook compatibility mesh should be preserved.

## Suggested Review Path By Time Budget

### 30-45 Minutes
Read:
- `RESEARCH_BRIEF.md`
- `SYSTEM_FINAL_ANALYSIS.md`
- `CONTROL_PATHS.md`
- `SEMANTIC_OWNER_MAP.md`
- `TRUTH_CARRIER_MATRIX.md`

Goal:
- understand the failure classes and design problem

### 60-90 Minutes
Also read:
- `DETERMINISTIC_REWRITE_LEDGER.md`
- `CUTOVER_DEPENDENCY_GRAPH.md`
- the 5 core hotspot docs

Goal:
- understand where architecture is still impure and what extraction is blocked by

### 2-4 Hours
Also read:
- legacy webhook hotspot docs
- outbox/admin/worker/console slices
- selected code references from hotspot docs

Goal:
- propose concrete migration and demotion strategy, not just target architecture
