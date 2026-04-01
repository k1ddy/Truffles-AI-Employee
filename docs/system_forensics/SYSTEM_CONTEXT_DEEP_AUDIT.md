# System Context Deep Audit

Status: `open_first_pass`
Purpose: describe the real live consultant-core system context, control paths, and operational entrypoints from fresh repo inspection.

## What this document covers
This is not a product-family audit.
It is a system-context audit answering:
- where requests enter,
- which runtime path is primary,
- which compatibility mesh remains live,
- which operational entrypoints duplicate one another,
- and why the architecture is still hard to govern.

## Level 1. System entry surfaces
### Primary application composition root
`truffles-api/app/main.py`
Evidence:
- mounts `message.router`, `callback.router`, `reminders.router`, `webhook.router`, `provider_gateway.router`, `knowledge_gateway.router`, `telegram_webhook.router`, `alerts.router`, `admin.router`, `console.router`, and `calendar.router`.
Meaning:
- the main product/control-plane process still exposes both product ingress and admin/console surfaces from one composition root.
- consultant-core does not live in a fully isolated service boundary yet.

### Dedicated service composition roots
- `truffles-api/app/outbox_service_app.py`
- `truffles-api/app/routers/decision_core.py`
- `truffles-api/app/provider_gateway_app.py`
- `truffles-api/app/knowledge_gateway_app.py`
- `truffles-api/app/knowledge_activation_service_app.py`
- `truffles-api/app/decision_core_app.py`
Meaning:
- the repo contains multiple service-shaped roots, but consultant behavior is not fully cleanly separated by those roots.
- some dedicated services are narrow; others preserve duplicate operational seams.


### Public webhook ingress
- `truffles-api/app/routers/webhook/http.py`
  - active HTTP ingress for `POST /webhook` and `POST /webhook/{client_slug}`
  - runs preflight and forwards into the core runtime through the public entrypoint contract
- `truffles-api/app/routers/public_entrypoint_contract.py`
  - materialization gate and single forwarder into the core runtime
Meaning:
- the real entry story is one step larger than the narrow consultant spine; public ingress and entrypoint gating must be understood too.

### Legacy wrapper still mounted
- `truffles-api/app/webhook.py`
  - still mounted by `app/main.py`
  - delegates to `app.routers.webhook.http`
Meaning:
- older ingress shape still exists as a live compatibility surface, not just dead archive code.

## Level 2. Primary consultant turn path
### Current hot path
Fresh repo-backed current spine:
1. `truffles-api/app/core/consultant_core_v2.py`
2. `truffles-api/app/core/consultant_runtime.py`
3. `truffles-api/app/core/turn_planner.py`
4. `truffles-api/app/services/intent_service.py`
5. `truffles-api/app/core/boundary_validator.py`
6. `truffles-api/app/core/turn_executor.py`
7. `truffles-api/app/core/dialog_state_service.py`
8. `truffles-api/app/core/response_realizer.py`

### Why this path matters
- `consultant_runtime.py` is still the live orchestration shell that prepares context, plans the turn, applies boundary validation, executes, writes state, handles handoff activation, and realizes the reply.
- `turn_planner.py` is the typed adaptation seam between runtime context and owner/boundary decision carriers.
- `intent_service.py` is the policy-core owner gateway.
- `turn_executor.py` is not only execution; it still participates in meaning-adjacent payload handling.
- `dialog_state_service.py` is not only persistence; it is also the normalization seam for projections and compatibility views.

## Level 3. Still-live legacy compatibility mesh
The repo still keeps real behavior in modules outside the narrow spine:
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/dedup.py`

### Why this matters
Even after hot-path narrowing, these files still matter because they keep:
- domain-specific booking/info behavior,
- continuity helpers,
- fallback and reply shaping,
- compatibility exports,
- guard/debounce preflight behavior,
- and response assembly side effects.

This means the architecture still has two realities:
- a cleaner typed spine,
- and a live mesh of mixed-authority compatibility surfaces.


## Level 4. Additional ingress and background callers into the same consultant path
Beyond the public webhook route, the same consultant runtime is reached through several other paths:
- `truffles-api/app/routers/message.py`
  - internal `/message` API that builds a webhook-style payload and forwards it
- `truffles-api/app/routers/decision_core.py` + `truffles-api/app/decision_core_app.py`
  - decision-core service ingress when enabled
- `truffles-api/app/routers/provider_gateway.py`
  - provider inbound ingress that translates provider payloads into the same consultant pipeline
- `truffles-api/app/services/outbox_runtime_service.py`
  - background/outbox processing calls the consultant core directly for durable action-plane work
- `truffles-api/app/services/console_consultant_verification.py`
  - console simulation/verification path that also calls the consultant core directly

### Why this matters
The consultant runtime is not only a public webhook handler.
It is a shared execution kernel behind webhook, message API, provider inbound, outbox replay, and console verification surfaces.
Any outside researcher must understand that the runtime is a reusable core with many callers, not just one HTTP endpoint.

## Level 5. Operational duplicate entrypoints
### Outbox process duplication
There is one operational seam with multiple live callers:
- `truffles-api/app/routers/outbox_service.py`
  - exposes `POST /outbox/process`
  - calls `run_default_outbox_process(...)`
- `truffles-api/app/routers/admin.py`
  - exposes `POST /admin/outbox/process`
  - also calls `run_default_outbox_process(...)`
- `truffles-api/app/routers/console.py`
  - defines ops-job `outbox_process`
  - claims rows and calls `process_claimed_outbox_rows(...)`
- `truffles-api/app/workers/outbox.py`
  - runs worker cycle through `run_outbox_worker_cycle(...)`
- `truffles-api/app/services/outbox_runtime_service.py`
  - contains the real durable processing helpers, including `_process_outbox_rows(...)`

### Why this matters
This is not a semantic path, but it is architecturally important because it proves the system still tolerates duplicated operational authority surfaces.
That same structural habit appears elsewhere in consultant-core: not one clean seam, but several live access paths around one underlying capability.

## Level 6. Main context verdicts
### Verdict 1. The spine is real, but not singular
The hot path is no longer imaginary. The typed consultant spine exists in code.
But it is not yet the only place where product behavior lives.

### Verdict 2. Composition roots are still mixed
`app/main.py` mounts product, admin, console, and calendar surfaces together.
This is operationally convenient, but it weakens clear system boundaries for outside explanation.

### Verdict 3. Legacy compatibility remains architecturally live
The webhook mesh is not dead archive code. It is still part of the behavior story.
Any external researcher must understand both the typed spine and the live compatibility mesh.

### Verdict 4. Duplicate operational seams are a first-class architecture smell
The outbox caller graph proves the codebase still accepts several live paths to one operational capability.
That weakens governance and makes “one true path” harder to enforce elsewhere.

## Main blockers surfaced by this audit
- many ingress/caller surfaces converge on one consultant kernel
- no single runtime ingress story yet
- live compatibility mesh outside the narrow spine
- mixed product/control-plane composition at the main root
- duplicate operational entrypoints around durable outbox dispatch

## Evidence anchors
- `truffles-api/app/main.py`
- `truffles-api/app/outbox_service_app.py`
- `truffles-api/app/routers/decision_core.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `docs/system_forensics/files/app_core_consultant_runtime.md`
- `docs/system_forensics/files/app_routers_outbox_service.md`
- `docs/system_forensics/files/app_routers_admin.md`
- `docs/system_forensics/files/app_workers_outbox.md`
- `docs/system_forensics/files/app_routers_console.md`
