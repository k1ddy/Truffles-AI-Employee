# Code Topology Deep Audit

Status: `open_first_pass`
Purpose: map the live consultant-core topology by authority concentration, not by file count alone, so outside researchers can see why good audits and bad local implementations were able to coexist.

## What this document covers
This is the fresh primary deep audit for code topology and authority concentration.
It answers:
- which files are real authority hotspots,
- which responsibilities still overlap,
- which modules look salvageable versus split/delete candidates,
- and why topology itself keeps inviting local patching.

## Main hotspot table
| File | Approx LOC | Why it is a hotspot | Current classification |
| --- | ---: | --- | --- |
| `truffles-api/app/routers/webhook/decision.py` | 7463 | legacy compatibility megafile, ingress residue, helper warehouse, live delegate surface | freeze, drain, then delete |
| `truffles-api/app/core/dialog_state_service.py` | 6661 | canonical continuity writer plus projections, session memory, pending resume, carryover, style/reference state, consult state bridges | split from inside, keep canonical core |
| `truffles-api/app/routers/webhook/booking.py` | 3855 | booking-domain orchestration, prompts, interrupts, confirmation, escalation side effects | split and narrow around booking mechanisms |
| `truffles-api/app/routers/webhook/response.py` | 3434 | reply shaping, fallback behavior, transport-facing compatibility residue | split and constrain |
| `truffles-api/app/services/intent_service.py` | 3281 | owner gateway mixed with snapshots, overrides, policy-core interaction shaping, semantic helpers | split into owner IO, prompt/context builder, parser |
| `truffles-api/app/services/ai_service.py` | 2863 | adjacent LLM/error-classification authority and fallback policy near the runtime core | split by provider IO vs error taxonomy |
| `truffles-api/app/routers/webhook/info.py` | 2626 | info classification, fact carryover, combined reply shaping, pack helper imports | drain into fact resolver/renderer |
| `truffles-api/app/services/reasoning_core.py` | 677 | small now, but still a compatibility shim with synthetic preflight/degrade artifact authority | shrink to pure adapter or delete |
| `ops/diagnose.py` | 29890 | quality runner, audit, trends, artifact indexing, gates, summaries, and status logic all in one tool | split into workflow modules over time |

## Why line count is not the real issue
A large file is not automatically bad.
The real smell is mixed authority inside the same file.
In the hotspot set above, the same module often mixes several of these roles:
- runtime orchestration
- continuity/state repair
- reply shaping
- domain behavior
- compatibility export surface
- fallback/degrade logic
- observability/meta writing
- test or governance policy

That is what keeps local patching cheap.

## Current overlapping authority clusters
### Cluster 1. Ingress and runtime dispatch overlap
Live consultant execution still involves several caller surfaces:
- `app/main.py`
- `routers/webhook/http.py`
- `routers/public_entrypoint_contract.py`
- `app/webhook.py`
- `services/reasoning_core.py`
- `routers/webhook/decision.py`
- `core/consultant_core_v2.py`
- `core/consultant_runtime.py`
Meaning:
- the typed spine exists,
- but the old compatibility mesh is still live enough that there is no one simple ingress story.

### Cluster 2. Continuity/state authority overlaps across core and webhook-era bridges
`dialog_state_service.py` is the canonical continuity center.
But continuity still touches:
- `routers/webhook/context_manager.py`
- `routers/webhook/session_memory.py`
- `services/state_service.py`
- timeout boundary services
- `consultant_runtime.py`
Meaning:
- the intended single writer exists,
- but the operational story is still wider than one file.

### Cluster 3. Fact behavior overlaps across owner, executor, pack, and legacy helper layers
Fact-side behavior currently spans:
- `intent_service.py`
- `policy_tool_projector.py`
- `turn_executor.py`
- `pack_runtime_service.py`
- `pack_runtime_default.py`
- `demo_salon_knowledge.py`
- `routers/webhook/info.py`
Meaning:
- topology mirrors the missing fact contract.
- that is why fact-side fixes are so easy to misplace.

### Cluster 4. Degrade and fallback authority overlaps across runtime and service helpers
Boundary/degrade control currently spans:
- `consultant_runtime.py`
- `turn_executor.py`
- `reasoning_core.py`
- `policy_core_guard_orchestration_service.py`
- timeout boundary services
- `dialog_state_service.py`
Meaning:
- degrade is not one narrow seam.
- it is a family of live helpers that still carry continuity and reply authority.

### Cluster 5. LLM authority is split between core-semantic and adjacent service layers
Semantic control is not only in the typed core:
- `services/intent_service.py`
- `services/ai_service.py`
- legacy `routers/webhook/decision.py`
Meaning:
- the repo has a clearer hot path than before,
- but adjacent service layers still carry LLM prompt, parsing, error, and fallback policy that is large enough to behave like additional semantic authority.

### Cluster 6. Quality governance is also topology-heavy
`ops/diagnose.py` centralizes:
- llm-quality runs
- audit artifact generation
- status updates
- trend aggregation
- index maintenance
- failure-family extraction
Meaning:
- the governance stack has become stronger,
- but it is also concentrated enough to become its own patch magnet.

## Salvage versus split/delete classification
### Keep and narrow
- `core/consultant_runtime.py`
  - keep as orchestration shell
- `core/turn_planner.py`
  - keep as planner seam
- `core/turn_executor.py`
  - keep as execution seam, but constrain fact and boundary side-authority
- `core/dialog_state_service.py`
  - keep canonical state role, but split the compatibility/projection bulk around it

### Split aggressively
- `services/intent_service.py`
  - split owner transport/prompt assembly/output parsing from legacy helper residue
- `services/ai_service.py`
  - split provider transport, retry/error taxonomy, and higher-level decision helpers
- `routers/webhook/booking.py`
  - split booking mechanism slices from compatibility helpers
- `routers/webhook/info.py`
  - split fact classification/rendering out of webhook-era helper logic
- `routers/webhook/response.py`
  - split reply shaping from compatibility and fallback residue
- `ops/diagnose.py`
  - split runner, audit, status/index, and trend logic

### Freeze then delete
- `routers/webhook/decision.py`
- `routers/webhook/_legacy.py`
Meaning:
- these modules should be treated as controlled compatibility shells, not as places for new business logic.

## Main verdicts
### Verdict 1. Authority concentration is the main topology problem
The repo no longer looks random, but several live modules still aggregate too much runtime or governance authority.

### Verdict 2. Legacy compatibility is still topologically live
`decision.py`, `info.py`, `booking.py`, `response.py`, and `context_manager.py` are not just archive residue.
They still shape behavior, continuity, or reply outcomes.

### Verdict 3. The target topology is not one giant rewrite
The typed core already exists.
The right move is authority draining:
- freeze legacy authorities,
- split overloaded core helpers,
- and re-home behavior behind narrower contracts.

### Verdict 4. Good docs alone could not stop bad implementations because the topology still made local edits feel cheap
This is the bridge between governance failure and code reality.
Even with better audits, the hotspot topology still encouraged one more local branch.

## Main blockers surfaced by this audit
- `decision.py` remains a major live compatibility surface
- `dialog_state_service.py` is still overloaded even though it is also the canonical state center
- fact behavior and degrade behavior still cut across too many modules
- `ops/diagnose.py` is a governance monolith in the quality lane

## Evidence anchors
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `ops/diagnose.py`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_services_intent_service.md`
