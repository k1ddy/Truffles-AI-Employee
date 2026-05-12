# PRODUCT SYSTEM CANON — What Truffles Must Become

**Status:** CANON
**Owner:** Жанбол / Top Architect
**Updated:** 2026-05-09
**Scope:** human-facing product and system front door: what we sell, who uses it, how the system works, what must work, what must not be built/claimed, and which documents are authoritative.
**Out of scope:** code implementation details, historical session status, per-block evidence, marketing copy.
**Links:** `STRATEGY/VISION.md`, `STRATEGY/PRODUCT.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/INFRASTRUCTURE.md`, `docs/CONSOLE_GUIDE.md`.

---

## 1. What Truffles Sells

Truffles sells a managed virtual consultant platform for service businesses.

The business does not buy "a chatbot". The business buys a controlled operating system for customer conversations:

- answers customer questions using only business facts;
- collects booking or lead details without losing context;
- hands off to a human with status and context when automation must stop;
- gives the business and Truffles team a Console Plane to onboard, configure, support, audit, and operate the system;
- provides operational proof through health, traces, metrics, logs, alerts, build fingerprints, and release discipline.

The first commercial vertical is `Beauty Salon v1`: beauty salons, barbershops, and similar appointment-based service businesses. Expansion to other businesses must happen through `packs + tools + capabilities`, not by rewriting the core for every niche.

## 2. Business Value

For the business owner:

- fewer missed leads in WhatsApp and other channels;
- faster answers to repetitive customer questions;
- higher booking conversion through structured slot collection;
- less manual load on managers;
- visible status for conversations, handoffs, integrations, and system health;
- safer scaling across branches and tenants.

For managers/operators:

- fewer low-value repetitive replies;
- one Inbox with context, status, customer history, and actions;
- clear handoff state instead of silent bot failure.

For end customers:

- quick factual answers;
- a clear next step;
- transparent transfer to a human when needed.

For Truffles as platform operator:

- repeatable onboarding;
- support without ad-hoc container surgery;
- evidence-driven debugging;
- scalable multi-tenant operations.

## 3. Product Outcomes

Every customer-facing runtime turn must move toward exactly one product outcome:

- `FACT` — answer with a grounded business fact from packs/tools.
- `COLLECT` — collect missing booking/lead slots.
- `HANDOFF` — transfer to a human with explicit status and context.

A green-looking final message is not enough. Behavioral closure requires:

- `raw owner = green`
- `final runtime = green`
- `rescue = no`

If `final runtime = green` but `rescue = yes`, the system is still not fixed. That is a workaround/degrade path, not closure.

## 4. System Planes

Truffles must be understood as four connected planes.

| Plane | Purpose | Main Users / Owners | Canon |
|---|---|---|---|
| Consultant Runtime Plane | Customer conversation, policy-core owner, tools, booking/fact/handoff behavior | End customer, AI consultant, manager via handoff | `SPECS/CONSULTANT.md`, `SPECS/ARCHITECTURE.md` |
| Console Plane | Main web GUI for onboarding, provisioning, knowledge, inbox, support, ops, audit | Platform Admin, Platform Support, Owner, Admin, Manager | `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `docs/CONSOLE_AUDIT/*` |
| Knowledge / Data Plane | Tenant-scoped facts, capabilities, published packs, provider config, isolation | Platform Admin, Owner/Admin, runtime tools | `SPECS/MULTI_TENANT.md`, `docs/GO_LIVE_DATA_READINESS.yaml` |
| Observability / Ops Plane | Health, readiness, logs, traces, metrics, alerts, fingerprints, deploy proof | Platform Admin, Platform Support, engineering/ops | `SPECS/INFRASTRUCTURE.md`, `docs/OBSERVABILITY_SURFACES.yaml`, `docs/RELEASE_TOPOLOGY_TRUTH.yaml` |

None of these planes is optional for a working product. A runtime bot path can be green while the product is still not ready if Console, data readiness, provider integration, or observability are not proven.

## 5. Console Plane Is The Main Management GUI

Console Plane is the main operating surface from onboarding to technical support.

For `Platform Admin`, Console must cover:

- company/client/branch onboarding;
- provisioning and activation;
- tenant and branch selection gates;
- capabilities and integration configuration;
- knowledge validation, publish, rollback;
- go/no-go checks;
- provider/webhook readiness;
- Ops/status dashboards;
- audit and diagnostics;
- support investigation and safe intervention.

For tenant roles, Console must cover:

- Owner/Admin: inbox, calendar, knowledge, team, settings, integrations, audit, business/status views;
- Manager: inbox, calendar, limited team/knowledge visibility;
- Support: read-only diagnostics and support surfaces.

Telegram is paging/fallback. It is not the main source of truth and must not become a hidden bypass around Console or runtime contracts.

## 5.1 Current Binding Product Corrections

These facts override stale session notes and stale gap lists until live evidence proves they changed.

- Console Plane is the main control plane for Platform Admin, Platform Support, Owner, Admin, and Manager.
- Console Calendar/Postgres `appointments` is the canonical booking calendar for offline salon bookings.
- Google Calendar is optional external projection, sync, or busy-source integration. It is not the required core calendar.
- Chatflow/WhatsApp is currently commercially unavailable because access is not paid/enabled. Do not plan near-term closure around fixing Chatflow in code unless commercial access is restored first.
- External channel/provider readiness and internal booking readiness are separate gates. A blocked WhatsApp provider can block customer-channel go-live, but it must not block proof that internal Console Calendar booking works.
- If logs should show provider billing/commercial block but do not, that is an observability/provider-readiness defect, not proof that the channel is healthy.

## 6. Observability And Platform Stack Are Product Requirements

Prometheus, Grafana, OpenTelemetry, Tempo/Loki-class telemetry, health checks, worker heartbeats, release topology truth, and build fingerprints are part of the product system.

They are not "nice to have" monitoring tools. They are required because Truffles must be operated and debugged quickly for many businesses.

Minimum observability requirement:

- every important turn/action has correlated identifiers such as `message_id`, `trace_id`, `outbox_id`, and tenant context;
- runtime, workers, provider paths, Console actions, and outbox delivery expose health and proof surfaces;
- alerts show critical degradation before the customer reports it;
- dashboards and traces help Platform Admin/Support understand what happened;
- deploys are immutable and verifiable by runtime fingerprint.

The official OpenTelemetry model supports using traces, metrics, and logs as correlated telemetry signals. In Truffles, this means observability must be tied to product go/no-go evidence, not maintained as separate dashboard theater.

## 7. Beauty Salon v1 Must Work

The first go-live target is not "any possible business". It is a beauty-salon operating slice on a business-agnostic platform.

`Beauty Salon v1` must prove these capabilities:

| Capability | Must Work | Minimum Proof |
|---|---|---|
| Fact answers | address, hours, services, prices, durations, masters, rules | exact runtime proof, pack/tool grounding, trace/meta |
| Booking intake | collect service, date/time, name, contact if needed | representative booking matrix with `raw owner = green`, `final runtime = green`, `rescue = no` |
| Booking commit | confirm exact appointment only through real calendar/CRM provider | provider/tool-backed commit proof; no fake slot promises |
| Handoff | transfer to manager with status and context | visible handoff state, manager context, outbox/provider proof |
| Onboarding/provisioning | new customer/branch can move to active state without manual magic | Console wizard/go-no-go proof, published pack, rollback path |
| Knowledge publish | draft -> validate -> publish -> rollback | fail-closed validation, history, rollback proof |
| Inbox/support | managers/support see conversations, status, diagnostics | role-based Console proof and audit trail |
| Tenant isolation/RBAC | no cross-tenant access or implicit tenant context | selection gates and scoped API/data access evidence |
| Production readiness | deploy, health, workers, traces, metrics, alerts, fingerprints | release topology truth, observability truth, worker/outbox proof |

## 8. What Not To Build Or Claim Now

Do not build or claim:

- a universal assistant for every topic;
- medical/legal/payment advice or operations;
- discounts/payment methods unless explicit in pack/policy;
- exact free slots without a real availability provider;
- hidden rescue paths as closure;
- phrase-by-phrase core fixes as the main strategy;
- a second semantic owner in state, executor, planner, boundary, legacy, or Console;
- new verticals by adding hardcoded core branches;
- production readiness without Console, data, provider, runtime, workers, observability, and release proof.

## 9. Why The Current System Has Not Been Working Reliably

The main failure is not one model, one prompt, or one case.

The proven systemic causes are:

- semantic meaning has been distributed across owner, boundary, state, executor, legacy, and runtime seams;
- prompt, snapshot, schema, and runtime repair have repeated the same semantic rules as separate truth surfaces;
- downstream rescue/rewrite paths could make final output look green while raw owner was wrong;
- `STATE.md` and active gap lists can be stale or too local to serve as the product/system compass;
- previous work optimized bounded path repair instead of full mechanism closure;
- Console, provider integration, observability, release topology, and data readiness were not consistently treated as one go-live system;
- monitoring tools existed in pieces, but go/no-go decisions were not always tied to correlated end-to-end proofs.

Therefore the correct work mode is:

`product/system canon -> capability map -> mechanism-level consolidation -> full acceptance evidence`

not:

`one surfaced defect -> one patch -> one path green -> next defect`.

## 9.1 Reality Architecture Recovery Finding — 2026-04-26

The current repository already contains meaningful architecture and product recovery work. The failure mode is not absence of documents; it is that future work can still read the wrong layer, treat history as truth, or start implementation from a local symptom.

Read the existing work by intent:

| Existing Work | Meaning | How To Use It |
|---|---|---|
| `docs/PRODUCT_SYSTEM_CANON.md` | product/system front door | decide what Truffles sells and what a working system means |
| `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md` | first vertical acceptance map | decide which Beauty Salon v1 capability a block advances |
| `docs/CONSOLE_PLANE_ACCEPTANCE_MAP.md` | human GUI acceptance map | prove Console lifecycle rows; do not infer readiness from page existence |
| `docs/system_forensics/*` | consultant-core deep architecture forensics | understand root causes, authority seams, and migration direction |
| `docs/RELEASE_TOPOLOGY_TRUTH.yaml` | deploy/runtime cohort contract | verify active runtime services and shadow services |
| `docs/OBSERVABILITY_SURFACES.yaml` | ops proof contract | verify metrics/traces/health/dashboard surfaces |
| `docs/GO_LIVE_DATA_READINESS.yaml` | target tenant data readiness contract | verify target salon data; do not infer provider/runtime closure |
| `docs/PROVIDER_INTEGRATION_READINESS.yaml` | channel/provider readiness contract | separate commercial provider blockage from internal booking readiness |
| `TECH.md` | operational/server map | find active containers, DB, release commands, and runtime probes |
| `STATE.md` | history/evidence | useful background only; not the product oracle |

Live recovery probes on 2026-04-26 showed this connected reality:

- required release cohort is valid: `truffles-api`, `truffles-outbox`, `truffles-knowledge-activation`, `truffles-sentinel`, `truffles-console-web`;
- API/runtime commit matches the active worktree: `9db031ee967999545f8a9673e7e57cf4d7202e73`;
- active API database is `truffles_postgres_1` / `chatbot`, with `appointments` as the internal booking calendar table;
- separate `truffles-console-postgres` is not the current Console API source of truth for appointments;
- observability truth is valid for required surfaces, but product observability still needs correlated end-to-end turn proof before go-live;
- target `demo_salon/main` data readiness is valid, but data readiness does not prove booking, provider, or Console lifecycle closure;
- provider integration readiness is not valid because Chatflow/WhatsApp is commercially unavailable; this blocks external channel go-live, not internal Console Calendar booking proof;
- shadow services are intentionally present as disabled or sidecar residue and must not become business-logic owners.
- internal Console Calendar / active DB kernel has Platform Admin API-level proof as of 2026-04-26: Console API created, read, and cancelled proof appointment `b92ca518-1cee-4a8c-b8a0-5ed47de21cd8` in active `truffles_postgres_1/chatbot.appointments`; evidence bundle `/tmp/truffles_console_calendar_kernel_proof_20260426`.
- internal Console Calendar GUI proof has Platform Admin browser-level evidence as of 2026-04-26 after the `/calendar/slots` UUID runtime fix: Console Web created appointment `79a9eca5-18ce-48ba-b925-1b32925f71b1`, displayed it in Calendar, and cleanup cancellation was written to `appointment_audit`; evidence bundle `/tmp/truffles_reality_architecture_recovery_20260426/console_calendar_slots`.
- internal Console Calendar role lifecycle proof has Manager browser-level evidence as of 2026-04-26: Manager created and displayed appointment `7bca5973-bf85-49ad-a951-a7ec3dbf6d3e`; Support was correctly denied by API and GUI; evidence bundle `/tmp/truffles_console_role_lifecycle_proof_20260426`.
- these proofs do not close full Console Plane or runtime booking readiness; they prove that the internal calendar kernel, Platform Admin GUI path, Manager GUI path, and Support denial path are not blocked by WhatsApp or Google Calendar.

Current connected process chain for Beauty Salon v1:

`Console onboarding/data -> published knowledge/data readiness -> Consultant Runtime FACT/COLLECT/HANDOFF -> internal Postgres appointments -> Console Calendar visibility -> outbox/provider if channel available -> observability/release proof`

This chain is the only valid lens for implementation planning. A task that improves only one local code path but does not move a named link in this chain is not a valid next product-system block.


## 9.2 Decision Constitution — 2026-04-26

Future work must not treat the current implementation as the system to repair by default.

The current implementation is evidence of past intent. It may contain useful mechanisms, accidental complexity, wrong architecture, legacy/shadow behavior, or tests that preserve bad design.

Before changing code, use this decision chain:

`Intent -> Target -> Reality -> Gap -> Decision -> Action -> Proof`

Implementation classification:

| Class | Meaning | Default Action |
|---|---|---|
| `KEEP` | correct and needed for the Beauty Salon v1 spine | rely on it and prove it |
| `REPAIR` | correct concept, flawed implementation | fix the mechanism, not one symptom |
| `STRANGLE` | useful behavior, wrong architecture | wrap, prove through spine, replace gradually |
| `REPLACE` | wrong design for target architecture | build the correct mechanism |
| `SHADOW` | may run but must not own product/business logic | isolate and drain after dependency proof |
| `LATER` | valid capability but outside Beauty Salon v1 | defer explicitly |
| `KILL` | not needed and unsafe/noisy | remove only after dependency proof |
| `UNKNOWN` | not understood enough | investigate before relying on it |

Rules:

- A failed check is a signal, not a task.
- A stale document is a witness, not truth.
- A green test is not product readiness.
- An admin-only proof is not role readiness.
- A local patch is invalid if the implementation should be strangled or replaced.
- Time, token, budget, or session pressure may change sequence, but not the target architecture or acceptance bar.

This document is the product truth ledger. Durable updates should preserve these categories:

- `truth`: proven product/system facts;
- `assumption`: accepted but not yet fully proven;
- `unknown`: important missing knowledge;
- `blocked`: current blocker and blocker surface;
- `no-go`: work that must not be done;
- `next decision`: the next architecture/product decision, not just the next command.


## 9.3 Beauty Salon v1 Target Architecture And Recovery Decision Map — 2026-04-26

This section is the current recovery map after reality probes, DB archaeology, code topology review, and one focused web search on correlated observability. Evidence bundle:

- `/tmp/truffles_beauty_salon_v1_arch_recovery_20260426`

Target Beauty Salon v1 architecture:

`Console Plane -> Knowledge/Data Plane -> Consultant Runtime Plane -> Scheduling/appointments -> Outbox/provider -> Observability/Ops Plane`

Expanded target flow:

`Platform Admin/Owner/Admin configures tenant in Console -> data is published as client/domain pack plus branch capabilities -> policy-core handles customer turn as FACT/COLLECT/HANDOFF -> boundary validates or explicitly degrades -> state stores canonical projection -> executor calls tools/SchedulingService -> Postgres appointments records booking -> Console Calendar/Inbox shows state -> outbox/provider delivers only when channel is available -> traces/logs/metrics/fingerprint prove the path`

Target invariants:

- `appointments` is the primary source of truth for salon bookings.
- `bookings` is legacy/residual unless a later migration explicitly reclassifies it.
- Knowledge `client_pack` is the source for customer-facing facts, but operational scheduling tables must be branch-consistent with it.
- Services, specialists, working hours, booking settings, and branch capabilities must be tenant/branch-scoped and must not cross-link to another client's branch.
- Every meaningful customer turn must be audited as `decision path + data ownership path`: a correct control-flow trace is insufficient if pack facts, capabilities, operational DB, RAG projection, or policy-core context disagree.
- Customer Data Contract ownership: Packs / Knowledge own customer-facing facts and rules; Capabilities own allowed channels/providers/features/tools/fact scopes/handoff policy; Operational DB owns executable services, specialists, links, and `appointments`; RAG / Qdrant is retrieval projection only; Policy-core context is a governed projection into the LLM owner, not a new truth source.
- `calendar_provider=local` means internal Console Calendar/Postgres booking. Google Calendar is optional projection or busy-source later.
- Chatflow/WhatsApp is an external provider gate and remains blocked until billing/access is restored; it is not a near-term code repair target.
- Release proofs are invalid if the required runtime cohort is on different immutable images, even when git commit labels match.
- Observability readiness requires correlated traces/logs/metrics with tenant context, not only running Prometheus/Grafana/Tempo containers. OpenTelemetry is the current standard framework for correlated traces, metrics, and logs.

Current verified recovery facts from 2026-05-01 work-map audit:

| Surface | Fact | Meaning |
|---|---|---|
| Worktree/runtime commit | HEAD and `/admin/version.git_commit` are `9db031ee967999545f8a9673e7e57cf4d7202e73` | API code identity matches the active worktree commit label |
| API build | `/admin/version.build_time=2026-04-30T17:23:07Z` in the latest recorded inventory | API/workers were rebuilt after booking-matrix and observability proof work |
| Release topology | drift was found, then reconciled; later `release_topology_truth.valid=true` artifacts exist for console, observability, and booking-matrix blocks | API and required workers share one image cohort when fresh topology truth is green; shadow services remain non-authoritative |
| Observability surfaces | `observability_truth.valid=true` and correlated E2E turn proof exists | infrastructure plus runtime/outbox/log/metric/Console correlation are proven internally; external provider canary remains separate |
| Target data | final `go_live_data_truth.valid=true` after branch-scoped operational service integrity repair | target data is ready for internal Console Calendar/booking acceptance; fleet residuals remain report-only for non-target packs |
| Provider | `provider_integration_truth.valid=false` | Chatflow/WhatsApp commercially unavailable; internal booking is not blocked by this |
| Internal Calendar | Platform Admin and Manager GUI/API kernel proofs plus later lifecycle proof created/read/cancelled appointments | internal Console Calendar kernel is useful and should be kept |
| Console lifecycle | Owner/Admin/Manager/Support/Platform Admin lifecycle proof is `PROVEN` | do not rerun Console lifecycle as the next block unless a fresh role/GUI/RBAC regression appears |
| Booking runtime | D1 matrix proof remains `PARTIAL_MECHANISM_PROVEN` for five scripted rows only; `Realistic Booking Matrix Closure` is downgraded to `SCRIPTED_TECHNICAL_PROOF` by decision ledger entry `DL-2026-05-03-001` | internal Console Calendar booking has useful live technical evidence, but real-world salon product proof is not closed until the Real-World Salon Acceptance Pack runs on owner-approved messy dialogs |
| DB service integrity | repaired: target branch `b7f75692...` has 15 active `services`, 15 target `specialist_services` links, and 0 cross-client/cross-branch service links | operational service catalog is now branch-consistent for `demo_salon/main`; guard must stay green |
| Knowledge catalog | active `client_pack` contains 14 service catalog entries plus prices/durations/promotions/policies | customer fact source exists; operational DB catalog for scheduling is now branch-consistent, while knowledge sync status remains report-only pending |
| Data ownership path | `/tmp/truffles_data_ownership_snapshot_20260505.json` classifies Packs / Knowledge, Capabilities, Operational DB, RAG / Qdrant, and Policy-core context for `demo_salon/main` | data exists and ownership surfaces are identifiable; Pack-vs-DB service differences must be handled as a contract, not as hidden semantic rescue |
| Google Calendar | token exists but expired; branch uses `calendar_provider=local`, `availability_provider=none` | Google must stay optional/later, not core booking |
| Go/No-Go | Console readiness separates internal booking from payment/provider/business blockers | readiness is partially meaningful; it must keep catching provider/access, business status, release cohort drift, and service/branch integrity regressions |

Implementation classification for future work:

| Surface | Decision | Reason | Next Action |
|---|---|---|---|
| Product canon and boot protocol | `KEEP` | now encodes product intent, no-go rules, and decision protocol | keep concise and update only with durable truth |
| FastAPI as main API boundary | `KEEP / REPAIR` | active API owns Console and runtime entrypoints, but modules are oversized and mixed | keep as boundary; repair through seams, not rewrite first |
| Console Web | `KEEP / REPAIR` | real GUI lifecycle is proven across Owner/Admin/Manager/Support/Platform Admin; surfaces remain broad | keep lifecycle regression evidence and consolidate only when a touched surface requires it |
| Keycloak/Auth/RBAC | `KEEP / REPAIR` | controlled real roles and least-privilege denials are proven | keep role provisioning/proof path; do not fake roles with platform admin |
| Postgres `appointments` + `SchedulingService` | `KEEP / REPAIR` | correct primary booking spine is useful; service/branch integrity is repaired; Console lifecycle, scripted matrix, and realistic matrix use it | keep realistic matrix regression evidence and Console visibility proof fresh when booking semantics change |
| `bookings` table | `STRANGLE` | residual table has no target branch rows and is not the declared booking SoT | do not build acceptance on it; migrate/drain only with dependency proof |
| `services` + `specialist_services` | `KEEP / REPAIR` | branch-scoped demo data was repaired and now has a readiness guard; future writes still need stronger prevention | keep guard green and later add write-time/composite ownership constraints |
| `knowledge_versions` / `client_pack` | `KEEP / REPAIR` | pack has useful salon truth; sync status is report-only pending; operational scheduling projection is repaired for target | keep pack as fact source; later make activation/projection truth first-class |
| Consultant Runtime / policy-core | `REPAIR` | target owner model is correct; implementation still has repeated semantic normalization surfaces | consolidate mechanisms, not phrases or local families |
| TurnPlanner / Boundary / State / Executor | `REPAIR / STRANGLE` | these layers should project, validate, persist, execute; evidence shows past semantic ownership leakage | passivate layer by layer under canonical contract |
| Legacy webhook/provider/knowledge side services | `REMOVED` | stopped side-service residue was removed after dependency proof | do not recreate without fresh architecture decision; keep canonical API/workers as authority |
| Outbox / workers | `KEEP / REPAIR` | required responsibilities exist, heartbeats are observable, and correlated outbox proof exists | keep release topology and observability guards green before each live acceptance |
| Observability stack | `KEEP / REPAIR` | required surfaces and correlated internal turn proof are green | keep repeatable proof tooling; external provider canary remains separate |
| Provider / Chatflow / WhatsApp | `LATER / BLOCKED` | commercial access is unavailable | expose blocker and run external canary only after access returns |
| Google Calendar | `LATER` | optional projection/busy-source, token expired, not core | do not make it a dependency for local booking |
| n8n, website, Gemini proxy, pgAdmin | `LATER / UNRELATED` | may be useful outside Beauty Salon v1 kernel, not go-live spine | do not touch without dependency decision |
| Marketing/compliance/fleet advanced Console surfaces | `LATER / UNKNOWN` | present in API/Console but not required for first working salon spine | classify before expanding scope |

Verified recovery order after the 2026-05-01 work-map audit:

1. `Console Lifecycle Acceptance Proof` — `PROVEN`.
2. `Booking Matrix Closure` — `PARTIAL_MECHANISM_PROVEN`.
3. `Realistic Booking Matrix Closure` — `SCRIPTED_TECHNICAL_PROOF`.
4. `Observability End-To-End Turn Proof` — `PROVEN`.
5. `External Provider Canary` — `BLOCKED_NON_CODE`; run only after Chatflow/WhatsApp commercial access is restored.

Next work must not continue booking fixes directly from scripted rows. Keep no-repeat governance green, keep provider/channel blocker visible, and build the Real-World Salon Acceptance Pack before claiming runtime product proof or repairing more booking mechanisms.

No-go from this map:

- Do not repair Chatflow/WhatsApp in code while access is unpaid/disabled.
- Do not make Google Calendar the core booking calendar.
- Do not add another local booking patch before release/data ownership blockers are addressed.
- Do not rely on `services` table or `specialist_services` as clean truth unless `go_live_data_truth` proves branch integrity remains green.
- Do not claim product readiness from `go_live_data_truth.valid=true`, `/health`, or Calendar proof alone.

## 9.4 Beauty Salon v1 Recovery Master Plan — 2026-04-28

This is the durable execution plan for turning the current recovery state into a working, scalable Beauty Salon v1 product. It is a product/system plan, not a local bug list.

The plan must be executed in dependency order. A later phase may be investigated early, but it must not be claimed closed until every earlier dependency that affects its proof is green.

### Operating rule for every block

Every nontrivial block must produce:

- one Task Package with scope, intent, exact target, no-go list, touched areas, and proof commands;
- one RCA if runtime behavior is broken: symptom, minimal reproduction, evidence, broken invariant, shared mechanism, open-world envelope, exact path map, and one classification;
- focused external research only when it affects a nontrivial technical decision;
- exact live proof on the active worktree/runtime, not on `/home/zhan/truffles-main`;
- validation artifacts in a dated `/tmp/truffles_*` bundle;
- a concise durable update only if it changes product truth, architecture, acceptance, or operational procedure.

Default classification before implementation:

| Surface | Required Decision |
|---|---|
| Business/product capability | map to `BSV1-*` or defer |
| Runtime mechanism | `KEEP / REPAIR / STRANGLE / REPLACE / LATER / KILL / UNKNOWN` |
| Data source | prove active DB/table/tenant/branch ownership |
| GUI claim | prove with real role, tenant context, API state, and screenshot/structured GUI evidence |
| Provider claim | separate internal booking from external WhatsApp/Chatflow status |
| Observability claim | prove correlated trace/log/metric/status, not just dashboard presence |

### Phase 0 — Reality baseline and freeze line

Intent: prevent work on the wrong runtime, wrong DB, stale docs, or accidental branch.

Actions:

1. Run the required boot probes from `docs/SESSION_START_PROMPT.txt`.
2. Confirm active worktree, HEAD, `/admin/version`, `/health`, release topology, data truth, observability truth, and provider truth.
3. Record whether Chatflow/WhatsApp is still commercially blocked.
4. Check dirty worktree before touching files; inspect exact diffs in files to edit.
5. Stop if runtime commit, required cohort, active DB, or target tenant data are incoherent.

Exit criteria:

- release topology is valid for the active commit;
- target `demo_salon/main` data truth is valid or data repair is explicitly selected as the current blocker;
- provider blocker is visible and does not block internal Calendar booking proof;
- no implementation starts from stale docs alone.

### Phase 1 — Architecture and component classification

Intent: know which current parts are product assets, which are legacy/shadow, and which must not own business meaning.

Actions:

1. Classify modules: Consultant Runtime, `policy-core`, planner, boundary, state, executor, booking runtime, Console API, Console Web, SchedulingService, outbox, provider layer, observability, auth/RBAC.
2. Classify containers: required cohort, shadow services, sidecars, unrelated/later services.
3. Classify storage: active Postgres `appointments`, residual `bookings`, knowledge versions, service/specialist tables, Console/Auth DBs.
4. Classify OSS/libs only by product role: FastAPI, Postgres, Redis, Qdrant, OpenTelemetry, Prometheus/Grafana/Tempo, Keycloak, provider SDKs.
5. Produce an architecture map showing which components are in the Beauty Salon v1 hot path and which are not.

Exit criteria:

- every required component has `KEEP / REPAIR / STRANGLE / REPLACE / LATER / KILL / UNKNOWN`;
- no shadow/legacy service is allowed to own semantic meaning;
- `appointments` remains booking source of truth unless a later explicit migration changes this.

### Phase 2 — Minimal Beauty Salon v1 product kernel

Intent: define the smallest product spine that can be made production-credible quickly.

Kernel:

`Console setup -> business data -> policy-core FACT/COLLECT/HANDOFF -> SchedulingService -> Postgres appointments -> Console Calendar/Inbox -> outbox/provider if available -> observability/release proof`

Required kernel capabilities:

1. FACT answers: services, prices, duration, address, hours, masters, rules.
2. COLLECT booking slots: service, date/time, name, contact if required, specialist when needed.
3. Appointment commit: internal Console Calendar/Postgres `appointments` with idempotency and audit.
4. HANDOFF: explicit manager transfer with context and visible Console state.
5. Console roles: Platform Admin, Owner, Admin, Manager, Support.
6. Readiness: internal booking not blocked by WhatsApp, provider blockage shown honestly.
7. Ops: release fingerprint, health, metrics, logs, traces, alerts, worker status.

Exit criteria:

- each kernel capability has a named acceptance row and proof command;
- anything outside this kernel is `LATER`, `SHADOW`, or `UNKNOWN`, not silently in scope.

### Phase 3 — Console Plane lifecycle closure

Intent: prove the main GUI is usable by humans, not just that pages or APIs exist.

Actions:

1. Audit and provision real Owner/Admin/Manager/Support credentials or a controlled test provisioning path.
2. Prove role-scoped tenant context: company/client/branch selection, no implicit tenant leaks.
3. Prove Calendar create/read/cancel visibility by Owner/Admin/Manager; prove Support denial for writes.
4. Prove Inbox/Handoff lifecycle visibility: queue, case detail, context, take/resolve/retry where allowed.
5. Prove Knowledge lifecycle: validate, publish/history/rollback or classify remaining gaps.
6. Prove Readiness/Go-No-Go: internal booking pass, provider blocked, observability/release/data status visible.
7. Prove Audit: mutations create audit rows with actor, channel, before/after, target tenant.

Exit criteria:

- real roles, real tenant context, real API calls, real DB state, GUI evidence;
- no Platform Admin proof used as fake Owner/Admin proof;
- Console lifecycle status is `PASS`, `PARTIAL`, or `BLOCKED` per row with evidence.

### Phase 4 — Consultant Runtime semantic kernel consolidation

Intent: remove repeated semantic ownership and make the hot path controllable.

Target hot path:

`Ingress -> policy-core owner -> planner projection -> boundary validate/degrade -> canonical state write -> executor/render -> outbox/provider`

Actions:

1. Define the owner output contract for `FACT`, `COLLECT`, `HANDOFF`, slots, referents, capability, tool action, and pending question relation.
2. Keep `policy-core` as the only semantic owner; remove or strangle downstream semantic invention.
3. Make planner a projection layer only: owner output to typed runtime contract and binding plan.
4. Make boundary validate, reject, or explicitly degrade with reason code; no silent meaning rewrite.
5. Make state persist canonical contract and projections only; no business meaning recovery from legacy fields.
6. Make executor call tools/render only; no intent reinterpretation.
7. Keep compatibility surfaces as adapters until dependency proof allows removal.

Exit criteria:

- `single_semantic_owner_guard` passes;
- owner, planner, boundary, state, executor traces expose the same contract;
- rescue/degrade is observable and never counted as closure.

### Phase 5 — Booking Matrix Closure

Intent: prove booking as a mechanism, not as one happy path.

Required rows:

1. missing service + exact time -> collect service while preserving time;
2. direct service/date/time -> collect name -> create appointment;
3. fact question during booking -> answer fact -> resume correct slot;
4. master/specialist question during booking -> answer grounded master info -> resume correct slot;
5. name fill after interrupted booking -> commit or safe next step;
6. specialist preference carryover;
7. restart/resume from persisted state;
8. booking manage: get/cancel/reschedule where in scope;
9. human request -> handoff with context.

Exit criteria for every row:

- `raw owner = green`;
- `final runtime = green`;
- `rescue = no`;
- appointment rows are created only through tool/SchedulingService when commit is expected;
- created appointment is visible in Console Calendar and has audit/trace evidence.

No-go:

- no phrase/regex hardcode in core semantic path;
- no local patch unless the shared mechanism is classified and repaired;
- no success claim when final response is green through handoff/rescue after owner failure.

### Phase 6 — Observability end-to-end proof

Intent: make the platform operable by support/engineering without shell archaeology.

Actions:

1. Prove one correlated FACT turn.
2. Prove one correlated COLLECT/booking commit turn.
3. Prove one correlated HANDOFF turn.
4. Link tenant, branch, conversation/message, trace id, decision meta, state transition, tool action, appointment/outbox/provider status where relevant.
5. Surface proof through logs, metrics, traces, health/readiness, Console/Ops, and artifacts.

Exit criteria:

- Platform Admin/Support can answer what happened, why, tenant scope, outcome, failure stage, and next action from observability surfaces;
- worker/outbox/provider states are visible;
- release/runtime fingerprint is attached to every proof bundle.

### Phase 7 — Release and operational hardening

Intent: keep the working product reproducible and safe to operate.

Actions:

1. Keep immutable release image and cohort parity for API, workers, and Console Web.
2. Keep runtime fingerprint endpoint reliable.
3. Keep DB migrations explicit and reversible where possible.
4. Add or enforce data ownership guards for services, specialists, branch links, and appointments.
5. Add rollback/restart playbooks only in existing operational docs.
6. Keep arch/semantic/contract guards in validation.

Exit criteria:

- release topology truth is green before live proof;
- data truth is green before booking proof;
- known stale generated artifacts are the only accepted arch guard exception, if still present.

### Phase 8 — Provider/channel readiness

Intent: prove external customer-channel go-live only when commercial access exists.

Actions:

1. Do not repair Chatflow/WhatsApp in code while billing/access is unavailable.
2. Keep provider readiness blocker visible in Console/Ops.
3. After access returns, run real inbound/outbound canary.
4. Prove outbox status, provider send status, webhook mapping, tenant isolation, and error surfaces.

Exit criteria:

- external channel has real canary proof;
- provider failure does not corrupt internal booking state;
- provider is not semantic owner.

### Phase 9 — Scale beyond salons

Intent: expand to other service businesses without rewriting core.

Actions:

1. Keep core unchanged for new niches unless a true platform gap is proven.
2. Add vertical differences through packs, capability manifests, tool registry entries, policies, onboarding schemas, and data contracts.
3. Require each new vertical to define its own capability map and acceptance matrix.
4. Reuse the same semantic hot path, Console lifecycle, observability, release, and provider gates.

Exit criteria:

- new niche onboarding does not require hardcoded core branches;
- core remains business-agnostic;
- pack/capability/tool changes have validation and rollback.

### Historical short-term dependency order — superseded

The order below was the near-term plan after the 2026-04-26/2026-04-27 recovery work. It is preserved as history only.

Do not use it as the current next-work list. Current work selection is defined by:

- `9.9 Verified Product Work Map — 2026-05-01`;
- `9.16 Architecture Consolidation / Handoff Closure — 2026-05-02`;
- section `12. Immediate Execution Blocks After This Canon`.

Historical order:

1. Re-run Phase 0 baseline because runtime was changed during Booking Matrix work.
2. Close or explicitly mark Console lifecycle residuals from Phase 3.
3. Stabilize Phase 4 semantic kernel only where Phase 5 proves repeated mechanism failure.
4. Finish Phase 5 Booking Matrix Closure; do not count rescue/handoff after owner failure.
5. Run Phase 6 correlated observability proof.
6. Run Phase 7 final guards.
7. Keep Phase 8 blocked until Chatflow/WhatsApp commercial access returns.

## 9.5 Delivery Track — Short Path To A Usable Beauty Salon v1 — 2026-04-28

This section overrides an overly broad "architecture archaeology" working style. The target is a usable product spine first, with strict evidence, not exhaustive analysis of every legacy surface.

Delivery target:

`Beauty Salon v1 usable demo = Console + business data + AI consultant FACT/COLLECT/HANDOFF + internal appointment + Console Calendar/Handoff visibility + honest Ops/readiness`

The delivery track must still obey the architecture laws. It changes sequencing and focus, not the acceptance bar.

### Delivery principles

- Work only on blockers that affect the demo spine.
- Treat non-spine findings as backlog unless they block the current demo flow.
- Prefer a thin canonical kernel over deep legacy repair when the existing path is too complex.
- Do not build a bypass that violates the target hot path.
- Use short decision tables: `fix now / isolate / defer / kill`.
- End every block as `DONE`, `PARTIAL`, or `BLOCKED`; never imply closure from activity.
- Keep validation narrow during implementation, then run full guards at closure.

### Usable demo script

The first product demo must prove these flows in one coherent tenant/branch:

1. Platform Admin or Owner sees tenant readiness, internal booking state, and provider blocker.
2. Customer asks a business fact: price, duration, address/hours, master, or rule.
3. Consultant answers from business data as `FACT`, with source/trace evidence.
4. Customer starts booking with service/date/time; consultant collects missing name/contact as `COLLECT`.
5. Consultant creates appointment through internal calendar/SchedulingService into Postgres `appointments`.
6. Owner/Admin/Manager sees the appointment in Console Calendar.
7. Customer asks for a human; consultant creates visible `HANDOFF`/Inbox state with context.
8. Platform Support sees diagnostics/readiness without forbidden write access.
9. Ops surfaces show release fingerprint, health, trace/log/metric/status for the same run.

Minimum demo acceptance:

- real role and tenant context;
- real runtime turn;
- real DB state;
- real Console GUI/API visibility;
- no hidden rescue counted as success;
- Chatflow/WhatsApp blocker visible but not blocking internal booking.

### Delivery blocks

| Block | Goal | Work | Exit |
|---|---|---|---|
| `D0 Reality Baseline` | know the live system before delivery | run boot probes, verify release/data/provider/observability truth, inspect dirty files before edits | active runtime and active worktree are coherent, or blocker is explicit |
| `D1 Demo Gap Table` | stop guessing what is broken | run the usable demo script live; classify every failing flow as product/data/runtime/console/ops/provider | one table: flow, expected, actual, owner status, rescue, decision |
| `D2 Console Control Spine` | make humans able to operate the salon | prove/provision Owner/Admin/Manager/Support paths for readiness, calendar, handoff/inbox, audit | Console demo rows are `DONE/PARTIAL/BLOCKED` with role evidence |
| `D3 Runtime Customer Spine` | make customer-facing AI useful | close representative FACT, booking COLLECT, handoff, and interrupted booking rows | each row has `raw owner=green`, `final runtime=green`, `rescue=no`, or blocker is classified |
| `D4 Appointment Visibility Spine` | make booking real | appointment create/read/cancel through tools/Console, DB row, audit, Calendar visibility | no shell/DB direct step is the product success path |
| `D5 Ops Proof Spine` | make support possible | correlate trace/log/metric/health/release/outbox/provider status for demo turns | support can explain what happened from product surfaces |
| `D6 Strangle Backlog` | avoid future drag | list legacy/shadow/complex parts to drain after demo spine works | backlog has owner, risk, dependency, and defer reason |

### Decision rules during delivery

Use these rules instead of open-ended investigation:

| Finding | Default Decision |
|---|---|
| Owner timeout/schema failure on demo flow | repair owner envelope/contract mechanism, not downstream rescue |
| Planner/boundary changes owner meaning | fix projection/validation contract or strangle that seam |
| State recovers business meaning from legacy fields | move meaning back to owner contract; state stores/projects only |
| Executor invents intent/follow-up | move decision into owner/planner; executor executes/render only |
| Console role missing | provision real controlled test role or mark blocked; do not fake with Platform Admin |
| Data ownership mismatch | fix target tenant/branch data and guard it before runtime proof |
| Provider/WhatsApp blocked | show blocker; do not repair provider code until commercial access returns |
| Non-demo module/container issue | classify and defer unless it breaks the demo spine |
| Existing path too tangled | create thin canonical kernel path, then strangle legacy after proof |

### Thin kernel rule

If a current implementation is too unstable to repair quickly, build the smallest correct kernel through the target architecture:

`policy-core owner contract -> planner projection -> explicit boundary -> canonical state -> tool execution -> Console/Ops proof`

Allowed:

- reduce owner envelope to the capability needed by the demo row;
- add typed contracts, guards, and projections;
- isolate legacy behavior behind adapters;
- use existing tools like `SchedulingService` and Console APIs when they are correct.

Not allowed:

- hardcode phrases in core semantic path;
- make state/executor a second semantic owner;
- create a hidden direct DB success path;
- claim success when a planner/boundary handoff hides owner failure.

### Session working mode

Every session should follow this order:

1. Run `D0 Reality Baseline`.
2. If no current gap table exists for the active runtime, run `D1 Demo Gap Table`.
3. Pick the first blocker that prevents the usable demo.
4. Make the smallest mechanism-level change or controlled provisioning step.
5. Prove only the affected demo row first.
6. Run required guards for touched code.
7. Update durable docs only if product truth, architecture, acceptance, or operating procedure changed.

### Current next move

Because later proof artifacts closed Console lifecycle and Observability E2E, and reclassified Booking Matrix as partial mechanism proof, the next session must not continue from this historical phase text alone. It must:

1. run the relevant D0 reality probes;
2. read the `Verified Product Work Map — 2026-05-01`;
3. avoid repeating Console Lifecycle or Observability E2E unless a fresh dated regression artifact proves the status changed;
4. continue booking only as `Realistic Booking Matrix Closure`, not as the old synthetic BM-01..BM-05 proof;
4. continue with no-repeat governance, shadow removal dependency proof, or provider/channel proof only after commercial access is restored.

## 9.6 Architecture Operating Model — 2026-05-01

This section is the durable work process. It exists because the main product risk is no longer only a failing booking path; it is uncontrolled architecture/process growth.

All nontrivial work must follow:

`Business capability -> architecture layer -> inventory lookup -> decision record -> implementation -> proof -> impacted docs/inventory update`

### Mandatory gates

1. **Business capability gate** — state which Beauty Salon v1 capability or platform capability the work advances; otherwise classify it `LATER`, `UNKNOWN`, or stop.
2. **Layer gate** — assign the work to exactly one primary layer: `Ingress`, `Policy Core`, `Planner`, `Boundary`, `State`, `Executor/Tools`, `Booking/Calendar`, `Handoff/Inbox`, `Console`, `Knowledge/Data`, `Observability/Ops`, or `Provider`.
3. **Inventory gate** — before creating or relying on a new development tool, script, architecture test, runtime worker, router, provider adapter, or external dependency, register owner, inputs, outputs, run conditions, proof value, and limits in `TECH.md` or `STRUCTURE.md`.
4. **Decision gate** — classify the current implementation as `KEEP / REPAIR / STRANGLE / REPLACE / SHADOW / LATER / KILL / UNKNOWN` before coding.
5. **Implementation gate** — change the smallest mechanism that moves the working spine; do not patch a phrase/path/test as the main solution.
6. **Proof gate** — prove the affected product row with runtime/API/DB/GUI/observability evidence as applicable.
7. **Durable memory gate** — update only impacted durable docs after proof; docs without proof are assumptions, not closure.

### Enforcement

- `scripts/tool_inventory_guard.py` blocks unregistered scripts and architecture tests.
- `scripts/arch_guard.py` includes the tool inventory guard in the architecture gate.
- Any failure in this process is a stop-the-line signal, not permission to bypass the process.

### Current process priority

Before further feature expansion, future work must keep this operating model green while continuing the Beauty Salon v1 delivery track. A task that improves runtime behavior but adds unregistered tools, unclear layers, or undocumented process surfaces is not complete.

## 9.7 System Inventory Baseline — 2026-05-01

The current architecture inventory baseline is a classification map, not product closure proof.

Artifact bundle:

- `/tmp/truffles_process_governance_20260501/system_layer_inventory_20260501.md`
- `/tmp/truffles_process_governance_20260501/keep_repair_strangle_plan_20260501.md`
- `/tmp/truffles_process_governance_20260501/system_surface_inventory_raw_20260501.json`

Layer decisions:

| Layer | Primary Surfaces | Classification | Direction |
|---|---|---|---|
| `Ingress` | FastAPI main app, webhook routers, message/provider/telegram entrypoints | `REPAIR / STRANGLE` | keep FastAPI boundary; drain legacy webhook mesh into canonical hot path |
| `Policy Core` | `intent_service.py`, policy prompt/context/vocabulary snapshots, LLM provider | `REPAIR` | single semantic owner; reduce repeated semantic rules |
| `Planner` | `turn_planner.py`, `binding_plan.py`, `policy_tool_projector.py` | `REPAIR` | typed projection only |
| `Boundary` | boundary validator and policy timeout/degrade services | `REPAIR` | explicit validate/reject/degrade only |
| `State` | dialog state, conversation projection, turn journal, DB projections | `REPAIR / STRANGLE` | canonical state with derived compatibility carriers |
| `Executor/Tools` | turn executor, tool registry, scheduling/catalog/outbox execution | `KEEP / REPAIR` | execute accepted contracts, no semantic recovery |
| `Booking/Calendar` | Calendar API/UI, `SchedulingService`, `appointments` and audit tables | `KEEP / REPAIR` | `appointments` remains booking SoT |
| `Handoff/Inbox` | handovers, escalation, inbox/queue/Console surfaces | `KEEP / REPAIR` | visible human lifecycle and audit |
| `Console` | Console API, Console Web, auth/RBAC, readiness/audit/business surfaces | `KEEP / REPAIR` | main GUI; split oversized surfaces only when touched |
| `Knowledge/Data` | knowledge runtime, pack runtime, capabilities, published packs | `KEEP / REPAIR / STRANGLE` | facts/capabilities as data, no core domain branching |
| `Observability/Ops` | logs, metrics, traces, health, alerts, fingerprints, truth scripts | `KEEP / REPAIR` | required surface; surface truth and correlated E2E proof are internally proven |
| `Provider` | Chatflow/Telegram/provider gateway/outbox delivery | `KEEP / LATER / BLOCKED` | delivery/status only; Chatflow commercial blocker remains non-code |
| `Shadow services` | removed decision/inbox/outbox/provider/knowledge side apps | `REMOVED` | dependency proof and side-service removal are closed; guard against reintroduction |

Structural risks that remain:

- oversized mixed-authority files remain in runtime and Console surfaces;
- removed shadow side services can be reintroduced accidentally if topology/inventory guards are bypassed;
- `STRUCTURE.md` is still broad and partly historical, but new script/test surfaces are now guarded by inventory;
- runtime claims still require fresh probes because stored docs can age quickly;
- proven product blocks must not be rerun as the next work unless a fresh regression artifact changes the work map.

## 9.8 Observability End-To-End Turn Proof — 2026-05-01

This is a correlated turn proof, not full product closure.

Artifact bundle:

- `/tmp/truffles_process_governance_20260501/tp_observability_e2e_turn_proof_20260501.md`
- `/tmp/truffles_process_governance_20260501/observability_e2e_turn_rca_20260501.md`
- `/tmp/truffles_process_governance_20260501/observability_e2e_path_map_20260501.md`
- `/tmp/truffles_process_governance_20260501/observability_e2e_turn_truth_20260501_final.json`

Live proof result:

- `valid=true`;
- input `message_id=obs-e2e-20260501T041742Z-1af921aa37`;
- `conversation_id=6b860169-d180-4651-9367-9fb4d63ffb64`;
- `outbox_id=e59b7e68-ea4e-4421-8798-d071f922e299`;
- `trace_id=19f1071d0ecb737890671329bec504dd`;
- outcome `FACT`, action `fact`, source `llm_policy_core`;
- `outbox_messages.meta.timing` and `outbox_messages.meta.correlation` contain the same inbound message and trace;
- Tempo has `truffles-outbox` spans including `outbox.process`;
- logs contain `outbox_id`, inbound `message_id`, and `trace_id`;
- `/metrics` exposes API webhook metric and healthy `truffles-outbox` heartbeat;
- `/console/v1/health` is `ok`;
- provider truth remains `valid=false` only because `CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE`, and `internal_booking_blocked_by_provider=false`.

Decision:

- keep current OTel/log/metric/state mechanisms;
- keep `scripts/observability_e2e_turn_truth.py` as the repeatable proof tool;
- do not treat external WhatsApp provider proof as closed until commercial access is restored.

## 9.9 Verified Product Work Map — 2026-05-01

This is the durable no-repeat map for zero-memory sessions. It records which product blocks are proven, downgraded, or blocked by artifact bundles and what work may start next.

Artifacts:

- `/tmp/truffles_process_governance_20260501/tp_verified_product_work_map_20260501.md`
- `/tmp/truffles_process_governance_20260501/focused_web_search_work_map_governance_20260501.md`
- `/tmp/truffles_process_governance_20260501/verified_product_work_map_rca_20260501.md`
- `/tmp/truffles_process_governance_20260501/verified_product_work_map_20260501.md`

| Block | Status | Evidence | Decision |
|---|---|---|---|
| Console Lifecycle Acceptance Proof | `PROVEN` | `/tmp/truffles_delivery_track_20260428/console_lifecycle_acceptance_summary_20260429.json` | Do not rerun unless fresh role/GUI/RBAC regression appears. |
| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` | `/tmp/truffles_delivery_track_20260428/booking_matrix_20260430_after_fix_i_full2/booking_matrix_semantic_audit_20260430i_full2.json` | Keep as narrow scripted evidence only; product-level booking proof requires section `9.23`. |
| Realistic Booking Matrix Closure | `SCRIPTED_TECHNICAL_PROOF` | `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/realistic_booking_matrix_product_summary_20260503g_fresh.json`; Console visibility `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/console_calendar_visibility_product_summary_20260503g_fresh.json`; decision ledger `DL-2026-05-03-001` | Keep as live technical evidence only; real-world product proof requires the Real-World Salon Acceptance Pack. |
| Observability End-To-End Turn Proof | `PROVEN` | `/tmp/truffles_delivery_track_20260428/observability_e2e_turn_summary_20260430.json` plus `/tmp/truffles_process_governance_20260501/observability_e2e_turn_truth_20260501_final.json` | Keep proof tool; do not repeat as product block. |
| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` | `provider_integration_truth.valid=false` with `CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE` | Wait for commercial access; keep blocker visible and keep internal booking unblocked. |
| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` | combined Console, booking, observability, data, release, provider map | Internal spine has major proofs; external channel remains blocked; shadow dependency/removal blocks are closed. |

Next allowed work:

1. No-repeat governance closure: keep this map, `docs/DECISION_LEDGER.yaml`, `scripts/decision_ledger_guard.py`, and `scripts/product_work_map_guard.py` green.
2. Provider/channel proof only after commercial access is restored.
3. Final Beauty Salon v1 Go-Live Review only after fresh combined proof and provider status are resolved.
4. Real-World Salon Acceptance Pack: use owner-approved messy dialogs before any further booking mechanism repair.
5. No-repeat governance maintenance: keep proven and downgraded work guarded; do not reopen closed blocks without fresh regression evidence.

No-repeat rule: do not select Console Lifecycle or Observability E2E as the next product block unless a fresh dated regression artifact proves the corresponding status changed. Do not treat scripted booking evidence as real-world product readiness. Do not claim Beauty Salon v1 go-live while provider/channel readiness remains commercially blocked.

## 9.10 Architecture Consolidation / Handoff Baseline — 2026-05-01

Status: `CLOSED_BY_9.16`.

This block starts the next valid work after no-repeat governance: make the proven Beauty Salon v1 spine understandable for future agents, humans, and third-party architecture review without reopening already-proven product blocks.

Artifacts:

- `/tmp/truffles_process_governance_20260501/tp_architecture_consolidation_handoff_20260501.md`
- `/tmp/truffles_process_governance_20260501/focused_web_search_architecture_handoff_20260501.md`
- `/tmp/truffles_process_governance_20260501/architecture_consolidation_handoff_rca_20260501.md`
- `/tmp/truffles_process_governance_20260501/architecture_consolidation_handoff_20260501.md`
- `/tmp/truffles_process_governance_20260501/architecture_authority_surface_audit_20260501.md`
- `/tmp/truffles_process_governance_20260501/shadow_authority_drain_selection_20260501.md`

Decision:

- use a lightweight C4/arc42-inspired handoff artifact, not a new permanent docs framework yet;
- map product capability -> plane -> layer -> service/container -> code surface -> source of truth -> proof artifact -> decision/backlog;
- keep Console and Observability E2E statuses as proven unless fresh dated regression evidence changes them;
- keep Booking Matrix status as `PARTIAL_MECHANISM_PROVEN` until realistic rows are proven;
- continue consolidation by reducing mixed-authority/legacy/shadow ambiguity, not by rewriting working core paths;
- first consolidation target was `Shadow/Authority Drain Closure`; it is now repaired, guarded, and stopped-or-disabled by sections 9.11-9.15.
- next consolidation target after closure is dependency proof for full shadow removal, not runtime/booking patching.

## 9.11 Shadow/Authority Drain Closure — Provider Gateway First Slice — 2026-05-01

Status: `REPAIRED_AND_GUARDED`.

Artifacts:

- `/tmp/truffles_process_governance_20260501/tp_shadow_authority_drain_provider_gateway_20260501.md`
- `/tmp/truffles_process_governance_20260501/shadow_authority_drain_provider_gateway_rca_20260501.md`

Decision:

- Superseded by section `9.19`: the Provider Gateway side app and restart script were removed after dependency proof.
- keep canonical product provider routes on `truffles-api /provider/*`;
- keep `truffles-provider-gateway` side app as shadow residue, not product authority;
- side-app `/provider/inbound` and `/provider/status` now return `503 shadow_authority_blocked` when provider flags are enabled without `SHADOW_RUNTIME_AUTHORITY_ALLOW=1`;
- `scripts/restart_provider_gateway.sh` refuses to start an enabled Provider Gateway side app unless `SHADOW_RUNTIME_AUTHORITY_ALLOW=1` is explicitly set;
- this does not close external provider/channel readiness; Chatflow/WhatsApp remains `BLOCKED_NON_CODE`.

## 9.12 Shadow/Authority Drain Closure — Remaining Side Services — 2026-05-01

Status: `REPAIRED_AND_GUARDED`.

Artifacts:

- `/tmp/truffles_process_governance_20260501/tp_shadow_authority_drain_remaining_side_services_20260501.md`
- `/tmp/truffles_process_governance_20260501/shadow_authority_drain_remaining_side_services_rca_20260501.md`

Decision:

- Superseded by section `9.19`: the Knowledge Gateway, Inbox Service, Decision Core, and Outbox Service side apps/restart scripts were removed after dependency proof.
- keep `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, and `truffles-outbox-service` as shadow residue, not product authority;
- canonical product authority remains in `truffles-api`, canonical workers, and Console/runtime state;
- side-app routes `/knowledge/snapshot`, `/inbox/event`, `/decision/handle`, and `/outbox/process` now return `503 shadow_authority_blocked` when their enable flag is set without `SHADOW_RUNTIME_AUTHORITY_ALLOW=1`;
- restart scripts for those side services refuse to start enabled shadow authority unless `SHADOW_RUNTIME_AUTHORITY_ALLOW=1` is explicitly set;
- this is an architecture safety closure only; it does not remove the side services and does not close external provider/channel readiness.

## 9.13 Shadow/Authority Drain Closure — Static Guard — 2026-05-02

Status: `GUARDED`.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_shadow_authority_static_guard_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_authority_static_guard_rca_20260502.md`

Decision:

- Superseded by section `9.19`: the shadow authority guard was removed with the side-service surfaces; `scripts/shadow_removal_dependency_truth.py` now guards reintroduction/dependency drift.
- freeze the shadow side-app authority contract with `scripts/shadow_authority_runtime_guard.py`;
- guard app middleware, route block response, health payload, restart-script hard stop, and durable docs/inventory together;
- wire the guard into `scripts/arch_guard.py` before the known generated packet check;
- this prevents future zero-memory sessions from silently reopening shadow authority while Product/Booking/Console/Observability remain proven.

## 9.14 Shadow Service Lifecycle Decision — 2026-05-02

Status: `STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN`.

Artifact:

- `/tmp/truffles_process_governance_20260502/shadow_service_lifecycle_decision_20260502.md`

Decision:

- `truffles-provider-gateway`, `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, and `truffles-outbox-service` remain `SHADOW`, not product authority;
- the valid Beauty Salon v1 lifecycle is now explicit `stopped_or_disabled`: either container stopped, or running with disabled health flags and no authority;
- do not remove these containers/code yet; full removal still requires dependency proof and a separate strangler/removal block;
- product traffic must remain on `truffles-api`, canonical workers, Console, and internal Postgres/calendar paths.

## 9.15 Shadow Stopped-Or-Disabled Observability — 2026-05-02

Status: `STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN`.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_shadow_stopped_or_disabled_observability_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_stopped_or_disabled_observability_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_stopped_or_disabled_observability_closure_20260502.md`

Decision:

- `docs/OBSERVABILITY_SURFACES.yaml` now models shadow services through `shadow_state_check`;
- `scripts/observability_truth.py` accepts `running_disabled` or `stopped` for shadow residue instead of forcing active health endpoints;
- this permits stopping non-authoritative shadow containers without creating false observability failure;
- release topology and observability truth remain the guards against accidentally reintroducing shadow authority.

## 9.16 Architecture Consolidation / Handoff Closure — 2026-05-02

Status: `ARCHITECTURE_HANDOFF_CLOSED`.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_architecture_consolidation_handoff_closure_20260502.md`
- `/tmp/truffles_process_governance_20260502/focused_web_search_architecture_handoff_closure_20260502.md`
- `/tmp/truffles_process_governance_20260502/architecture_consolidation_handoff_closure_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/architecture_consolidation_handoff_closure_20260502.md`
- `/tmp/truffles_process_governance_20260502/zero_context_understanding_audit_20260502.md`

Third-party review map:

| View | Active truth |
|---|---|
| Product spine | `Console setup -> business data -> FACT -> COLLECT -> internal appointment -> Console Calendar visibility -> HANDOFF -> Ops/readiness` |
| Runtime semantic owner | `policy-core LLM`; downstream layers must not silently rewrite meaning |
| Required runtime cohort | `truffles-api`, `truffles-outbox`, `truffles-knowledge-activation`, `truffles-sentinel`, `truffles-console-web` |
| Core data stores | active API Postgres `truffles_postgres_1/chatbot`; `appointments` is internal booking SoT; Redis/Qdrant support runtime state/knowledge |
| Console owner | Console Plane is the main GUI for Platform Admin, Support, Owner, Admin, and Manager |
| Provider status | Chatflow/WhatsApp is `BLOCKED_NON_CODE`; external provider canary is not closed and does not block internal booking |
| Shadow status | five legacy side services were removed after dependency proof; canonical API/workers remain the runtime surfaces |
| Scaling model | future verticals use packs/capabilities/tools and tenant data, not core rewrites |

Canonical scenario map:

| Scenario | Path | Current status |
|---|---|---|
| Fact answer | inbound -> policy-core `FACT` -> pack/data truth -> executor/render -> outbox | internally proven by booking/observability evidence; keep raw/final/rescue guard |
| Booking intake/commit | policy-core `COLLECT` -> SchedulingService -> Postgres `appointments` -> Console Calendar | `PROVEN` for realistic Beauty Salon v1 rows by section `9.21`; old BM-01..BM-05 remains narrow evidence only |
| Handoff | policy-core `HANDOFF` -> handoff/inbox state -> Console Inbox/manager/support visibility | `PROVEN` for Console lifecycle slice |
| Console lifecycle | real role -> tenant context -> Console API/Web -> active DB -> audit/readiness | `PROVEN` |
| Ops/readiness | release/data/observability/provider truth scripts -> Console/Ops evidence | internal ops proof `PROVEN`; provider remains commercial blocker |

Current next valid work:

1. `Provider/Channel Readiness Proof`: run only after Chatflow/WhatsApp commercial access is restored.
2. `Final Beauty Salon v1 Go-Live Review`: combine fresh release/data/observability/Console/booking/provider evidence; cannot be `GO_LIVE_READY` while provider is commercially blocked unless there is an explicit product waiver.
3. `No-Repeat / Process Governance Maintenance`: keep product-work-map, tool inventory, and semantic-owner guards green; do not reopen closed product blocks without fresh dated regression evidence.

## 9.17 Process Optimization Closure — 2026-05-02

Status: `PROCESS_OPTIMIZED_AND_GUARDED`.

This closes the process-governance gap for zero-memory sessions. It does not close Beauty Salon v1 go-live and does not replace runtime proof.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_process_optimization_closure_20260502.md`
- `/tmp/truffles_process_governance_20260502/focused_web_search_process_optimization_20260502.md`
- `/tmp/truffles_process_governance_20260502/process_optimization_closure_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/process_optimization_closure_20260502.md`

Optimized execution contract:

| Rule | Decision |
|---|---|
| Work selection | Select work from the verified work map or fresh dated regression evidence, not from stale blocker text. |
| Work unit | One active product block at a time; do not mix product delivery, broad cleanup, and documentation-only work in one closure claim. |
| Pre-code gate | State `Intent -> Target -> Reality -> Gap -> Decision -> Action -> Proof` before nontrivial implementation. |
| Tool gate | Look up existing registered tools/tests before creating or relying on a new tool; repair inventory first if unclear. |
| Docs gate | Docs update is an output of proof, not a substitute for proof; update only impacted durable docs. |
| Validation tiers | Use narrow touched-slice checks, governance guards, live truth probes, and architecture gate in that order. |
| Stop-line | Stop if runtime/docs disagree, a fake role/tenant is needed, a provider commercial blocker is treated as code, or downstream layers invent meaning. |

Validation tiers:

| Tier | Purpose | Typical checks |
|---|---|---|
| `T0 Reality` | Prove active worktree/runtime before claims. | `git status`, `git rev-parse HEAD`, `/admin/version`, `/health`. |
| `T1 Touched Slice` | Prove changed code/docs/tests are syntactically and behaviorally coherent. | `python3 -m py_compile`, targeted pytest, `git diff --check`. |
| `T2 Governance` | Prevent architecture/process drift. | `product_work_map_guard`, `tool_inventory_guard`, `single_semantic_owner_guard`, `shadow_removal_dependency_truth` when relevant. |
| `T3 Live Truth` | Prove runtime/data/ops facts. | `semantic_preflight`, `release_topology_truth`, `go_live_data_truth`, `observability_truth`, `provider_integration_truth || true`. |
| `T4 Architecture Gate` | Prove broad guardrail health. | `arch_guard`; the only accepted current independent blocker is stale `docs/_generated/AGENT_PACKET.json`. |

Durable process decision:

- keep `docs/PRODUCT_SYSTEM_CANON.md` as product truth and decision log;
- keep `TECH.md` / `STRUCTURE.md` as technical reference and inventory;
- keep `docs/SESSION_START_PROMPT.txt` as the zero-memory boot protocol;
- keep dated `/tmp/...` artifacts for RCA, task package, focused research, and proof;
- do not create duplicate permanent process docs unless the existing durable locations cannot hold the knowledge.

Current next valid work remains:

1. `Provider/Channel Readiness Proof` only after commercial access is restored;
2. `Final Beauty Salon v1 Go-Live Review` only after fresh combined proof and provider status are resolved.

## 9.18 Shadow Removal Dependency Proof — 2026-05-02

Status: `SHADOW_REMOVAL_DEPENDENCY_PROVEN`.

This proves removal readiness for stopped shadow side-service surfaces. It does not delete the surfaces by itself.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_shadow_removal_dependency_proof_20260502.md`
- `/tmp/truffles_process_governance_20260502/focused_web_search_shadow_removal_dependency_proof_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_removal_dependency_proof_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_removal_dependency_truth_static_probe_20260502.json`
- `/tmp/truffles_process_governance_20260502/shadow_removal_dependency_truth_live_20260502.json`

Live proof result:

- `scripts/shadow_removal_dependency_truth.py --include-runtime` returned `valid=true`;
- decision `removal_ready_for_later_block`;
- blocking static production references: `0`;
- live dependency hits from running containers: `0`;
- proof-time runtime state showed `truffles-provider-gateway`, `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, and `truffles-outbox-service` existed but were stopped with Docker status `exited`; the subsequent removal block is closed in section `9.19`;
- `/home/zhan/infrastructure/docker-compose.truffles.yml` was included as an external static dependency input and had no blocking shadow service dependency.

Decision:

- it is now safe to start a separate `Shadow side-service removal block`, which is closed in section `9.19`;
- the removal block may delete side-app entrypoints, restart scripts, stopped containers, and shadow topology/docs entries only if it keeps canonical `truffles-api`, `truffles-outbox`, Console, and provider blocker truth green;
- do not delete canonical API routers such as `provider_gateway` or `knowledge_gateway` just because side-service containers are removable;
- provider/channel readiness remains `BLOCKED_NON_CODE` until Chatflow/WhatsApp commercial access is restored.

## 9.19 Shadow Side-Service Removal — 2026-05-02

Status: `SHADOW_SIDE_SERVICES_REMOVED`.

This removes the stopped/non-authoritative side-service residue after dependency proof. It does not remove canonical `truffles-api` routes, canonical workers, Console, or provider readiness truth.

Artifacts:

- `/tmp/truffles_process_governance_20260502/tp_shadow_side_service_removal_20260502.md`
- `/tmp/truffles_process_governance_20260502/focused_web_search_shadow_side_service_removal_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_side_service_removal_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/shadow_removal_dependency_truth_after_removal_20260502.json`
- `/tmp/truffles_process_governance_20260502/release_topology_truth_after_shadow_removal_20260502.json`
- `/tmp/truffles_process_governance_20260502/observability_truth_after_shadow_removal_20260502.json`
- `/tmp/truffles_process_governance_20260502/shadow_side_service_removal_closure_20260502.md`

Removed side-service residue:

- side app entrypoints for Provider Gateway, Knowledge Gateway, Inbox Service, Decision Core, and Outbox Service;
- side-service restart scripts for the five removed side services;
- side-service-only routers for Inbox Service, Decision Core, and Outbox Service;
- shadow authority guard and tests that only existed to keep removed side services non-authoritative;
- release topology and observability shadow side-service entries.
- Docker containers for the five removed side services were removed; the after-removal dependency truth reports `exists=false` for each and `blocking_references=0`.

Preserved canonical surfaces:

- `truffles-api` remains the runtime API;
- `truffles-outbox`, `truffles-knowledge-activation`, and `truffles-sentinel` remain canonical workers;
- Console remains the management GUI;
- canonical `/provider/*` and `/knowledge/snapshot` routes on `truffles-api` remain available according to their existing enable/config contracts;
- Chatflow/WhatsApp remains `BLOCKED_NON_CODE` and still does not block internal Console Calendar booking.

Current next valid work:

1. `Provider/Channel Readiness Proof` only after Chatflow/WhatsApp commercial access is restored.
2. `Final Beauty Salon v1 Go-Live Review` only after fresh combined proof and provider status are resolved.
3. `No-Repeat / Process Governance Maintenance` to keep proven blocks guarded.

## 9.20 Booking Matrix Reclassification — 2026-05-02

Status: `BOOKING_MATRIX_PARTIAL_MECHANISM_PROVEN`.

Current live result: section `9.21` is downgraded to `SCRIPTED_TECHNICAL_PROOF`; the 2026-05-02 blocked result below is historical evidence.

Why this exists:

- the previous `Booking Matrix Closure = PROVEN` status overstated what was proven;
- the final passing artifact contains BM-01..BM-05 scripted dialogs only;
- BM-06 duplicate/retry and BM-07 human-needed rows were in the task package but are absent from the final passing matrix;
- the recorded dialogs do not represent realistic salon WhatsApp behavior such as vague time/service, corrections, contact delays, cancel/reschedule, slot negotiation, and handoff pressure.

Artifacts:

- `/tmp/truffles_real_booking_matrix_20260502/tp_booking_matrix_reclassification_20260502.md`
- `/tmp/truffles_real_booking_matrix_20260502/focused_web_search_booking_conversation_20260502.md`
- `/tmp/truffles_real_booking_matrix_20260502/booking_matrix_reclassification_rca_20260502.md`
- `/tmp/truffles_real_booking_matrix_20260502/realistic_booking_matrix_spec_20260502.json`
- `/tmp/truffles_real_booking_matrix_20260502/live_matrix_20260502a/realistic_booking_matrix_evaluation_20260502a.json`
- `/tmp/truffles_real_booking_matrix_20260502/live_matrix_20260502a/realistic_booking_matrix_live_failure_rca_20260502.md`

Decision:

- keep the old matrix as a narrow mechanism proof for BM-01..BM-05;
- do not use it as product-level booking closure;
- historically opened `Realistic Booking Matrix Closure` as the next valid product block; section `9.21` supersedes this only with scripted technical evidence, not real-world product proof;
- closure requires realistic rows for vague service/time, corrections, fact interruptions, specialist preference, contact/name order changes, duplicate/retry, no-slot negotiation, cancel/reschedule, and human-needed handoff;
- every runtime behavior row still requires `raw owner = green`, `final runtime = green`, and `rescue = no`;
- appointment claims must be backed by internal Postgres `appointments` and Console Calendar visibility.

Live probe result on 2026-05-02:

- 16 realistic rows ran through live runtime for `demo_salon/main`;
- historical critical pass rate was `2/12`;
- stretch pass rate is `1/4`;
- 3 appointments were created in active Postgres `appointments` with `source=bot` and `appointment_audit` create rows;
- realistic closure is blocked by shared booking semantic failures: fact-interruption continuity, correction handling, pre-supplied contact retention, multi-service/approximate-time continuity, cancel/reschedule intent, duplicate retry UX, and fallback handoff not owned by policy-core in some rows.

Next action:

- superseded by section `9.21 Realistic Booking Matrix Closure — 2026-05-03` and decision ledger entry `DL-2026-05-03-001`;
- do not run more booking repairs until the Real-World Salon Acceptance Pack produces capability/layer-classified failures.

## 9.21 Realistic Booking Matrix Closure — 2026-05-03

Status: `SCRIPTED_TECHNICAL_PROOF`.

What was proven:

- 16 scripted Beauty Salon v1 rows ran through live runtime for `demo_salon/main`;
- every turn had `source=llm_policy_core` and owner source `llm_policy_core`;
- `boundary_normalization_used=false`, `structured_output_fallback_used=false`, `contract_repair_retry_used=false`, and `rescue=false` for all turns;
- scripted rows covered vague service/time, fact interruption resume, date correction, specialist preference relaxation, identity-first booking, slang service alias, multi-service handoff, approximate time, complaint/medical handoff, duplicate retry, cancel/reschedule lookup, mixed-language Kazakh/transliterated date, nearest-slot clarification, and unavailable service;
- 9 appointment rows created internal `calendar.book_slot` appointments;
- Console Calendar API showed all 9 created appointments for `platform_admin` with real Keycloak token and explicit `demo_salon/main` tenant headers.
- product summary and Console visibility summary both report `valid=true`.

What was not proven:

- the corpus was still generated/selected inside Truffles proof tooling, not owner-approved messy salon dialogs;
- the result is not `REAL_WORLD_PRODUCT_PROOF`;
- it does not prove production data completeness beyond the existing `go_live_data_truth.valid=true` minimum data contract;
- it does not prove external WhatsApp/Chatflow canary because provider access remains commercially blocked.

Artifacts:

- `/tmp/truffles_real_booking_matrix_20260503/tp_realistic_booking_matrix_mechanism_repair_20260503.md`;
- `/tmp/truffles_real_booking_matrix_20260503/rca_realistic_booking_matrix_continuity_20260503.md`;
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/realistic_booking_matrix_product_summary_20260503g_fresh.json`;
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/console_calendar_visibility_product_summary_20260503g_fresh.json`;
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/summary.json`;
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/result.json`.

Decision:

- keep the 2026-05-03 matrix as `SCRIPTED_TECHNICAL_PROOF`;
- keep old scripted `Booking Matrix Closure` as `PARTIAL_MECHANISM_PROVEN` evidence only;
- keep external provider/channel readiness separate and blocked until Chatflow/WhatsApp commercial access is restored;
- next product runtime closure requires the Real-World Salon Acceptance Pack and decision ledger entry `DL-2026-05-03-001`;
- next product closure cannot be Beauty Salon v1 go-live until provider/channel status is resolved or explicitly waived by product decision.

## 9.22 Decision & Action Ledger — 2026-05-03

Status: `LEDGER_PROCESS_ACTIVE`.

Durable file:

- `docs/DECISION_LEDGER.yaml`

Guard:

- `python3 scripts/decision_ledger_guard.py --repo-root .`

Memory model:

- Canon = current truth.
- Ledger = why truth changed.
- Artifacts = raw evidence.
- Inventory = tools/modules/scripts.
- Session prompt = agent boot protocol.

Ledger entries are required only for mechanism changes, architecture decisions, blocker open/close/reclassification, tool/script creation or change, product status changes, and proof downgrade/invalidation. The ledger must not log every command or micro-step.

Current binding entries:

- `DL-2026-05-03-001` downgrades the 2026-05-03 booking proof to `SCRIPTED_TECHNICAL_PROOF` and blocks `REAL_WORLD_PRODUCT_PROOF` claims until a Real-World Salon Acceptance Pack runs with owner-approved messy dialogs.
- `DL-2026-05-03-002` defines the Internal Pilot Proof path: owner-reviewed synthetic messy corpus, non-blocking Exploration lane, invalid-run stop conditions, failure-family map before repairs, and strict Acceptance after mechanism-level fixes.
- `DL-2026-05-03-003` repairs quality-runner transport evidence separation: rendered assistant evidence is allowed only for dev Exploration; strict Acceptance still requires delivery evidence and full DB/Console/audit/trace proof.
- `DL-2026-05-03-004` records Pack v0 Tranche B as diagnostic only and sets the next repair order: booking-manage/admin-confirm, handoff contact/context continuity, then handoff lifecycle/oracle contract.
- `DL-2026-05-04-005` repairs and focused-proves Pack v0 P0 `FAM-B1` and `FAM-B3`: customer cancel/reschedule/admin-confirmation routes to admin-confirmation `HANDOFF`, and name/phone after handoff updates handoff context instead of reopening booking collect.
- `DL-2026-05-04-006` repairs and focused-proves Pack v0 P0 `FAM-B2`: pending handoff lifecycle is accepted as the correct runtime state, booking-manage follow-ups stay handoff context, manager simulation no longer resolves before remaining customer context, and manager `take` is race-tolerant.
- `DL-2026-05-04-007` records the after-P0 Pack v0 diagnostic rerun as `DIAGNOSTIC_AFTER_P0_NOT_ACCEPTANCE`, repairs the residual generic handoff-context oracle, and makes `FAM-C0` evidence reliability the next P0 blocker before Acceptance.
- `DL-2026-05-05-008` repairs focused `FAM-C0` evidence reliability in the proof runtime: no-response pending handoff timeouts are soft only with runtime evidence, pending ACK waits until scripted customer turns finish, manager `take` timeout can be advisory when `resolve` follows, and manual audit backlog ignores soft/recovered/advisory runtime classifications.
- `DL-2026-05-05-009` records the broader after-FAM-C0 Tranche B diagnostic as `DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE`: infra/evidence reliability is stable in the current diagnostic, but Pack v0 remains semantic-invalid; next work is contract definition for `FAM-C2` unsupported-service and `FAM-C3` fact-interruption before runtime repair.
- `DL-2026-05-05-010` makes single-turn work auditable in two dimensions: `decision path + data ownership path`. Before runtime repairs, define the Customer Data Contract for Beauty Salon v1 fields and prove which surface owns each business datum used by the turn.
- `DL-2026-05-07-011` repairs and focused-proves `FAM-C2/FAM-C3` mechanisms as `FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE`: unsupported-service availability stays grounded as `FACT`, fact-interruption continuity is preserved, planner-boundary state containment is explicit, and range-time rendering asks for exact time. This is not Pack v0 Acceptance.
- `DL-2026-05-07-012` records the broader Pack v0 diagnostic after focused repairs as `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE`: the first 10-dialog / 44-turn run reached `strict_pass_rate=1.0` and zero failure families, but remained diagnostic-only.
- `DL-2026-05-07-013` records the quality-governance/replay-isolation repair: `--jid-mode unique` now creates run-scoped unique JIDs, false info-answer inference from handoff/human wording is blocked, and the current 20260507m Pack v0 diagnostic has `infra_valid=true` and `info_answer_rate=1.0` but still remains not Acceptance because of one scenario/oracle mismatch and one `policy_core_invalid_schema` runtime family.

## 9.23 Real-World Salon Acceptance Pack — 2026-05-03

Status: `OWNER_REVIEWED_CORPUS_V0_AFTER_FAM_C0_DIAGNOSTIC_COMPLETE`.

Purpose:

- prove Beauty Salon v1 runtime behavior on customer-like salon conversations, not on scripted scenario coverage;
- use existing quality tooling instead of creating a new runner unless an inventory decision proves a gap;
- produce capability/layer-classified failures before any mechanism repair.

Execution decision:

- Internal Pilot Proof is the near-term product-readiness path until raw production salon transcripts exist.
- Candidate dialogs may be generated by existing tools, but they are not acceptance rows until the owner selects, edits, and approves the sample.
- Approved synthetic reconstructions become an owner-reviewed synthetic messy corpus: a pilot proxy, not raw production transcripts.
- Exploration lane must run with continue-on-error behavior: behavioral failures do not stop run execution.
- Invalid-run conditions stop the run: wrong runtime/version/tenant, broken scenario contract, missing trace/meta, missing owner output, harness contamination, or evidence that cannot classify the layer.
- Triage lane groups all failures into a failure-family map before implementation starts.
- Repair lane changes shared mechanisms only after capability and architecture layer are known.
- Acceptance lane is strict: no hidden rescue, no semantic owner drift, exact DB/Console/audit/trace proof.
- Pack v0 is owner-reviewed and approved as an Internal Pilot Proof proxy only. It is not a raw production transcript corpus and not product acceptance proof.
- Dev Exploration may use rendered assistant evidence (`--transport-evidence-policy rendered`) only to decouple semantic diagnosis from blocked provider delivery. Strict Acceptance must use delivery transport evidence.

Required corpus:

- owner-approved messy dialogs from salon operations or owner-reviewed synthetic reconstructions;
- RU, KZ, mixed RU/KZ, and translit;
- short and fragmented messages;
- voice transcript style with punctuation loss, filler words, and partial phrases;
- cancellation/reschedule requests that collect identity/context and require admin confirmation when pack policy says the bot cannot confirm;
- complaint, medical/legal, refund/payment confirmation, and unsafe policy paths that create `HANDOFF`;
- price/duration interruptions during booking, with booking continuity preserved;
- multiple services, vague time, date/time correction, no-slot negotiation, missing contact/name, duplicate/retry, unavailable service, and human request rows.

Required proof per accepted row:

- top-level outcome remains `FACT`, `COLLECT`, or `HANDOFF`, with sub-outcome/effect such as `fact_answer`, `slot_collect`, `booking_request_created`, `booking_manage_request`, `handoff_requested`, or `handoff_created`;
- `raw owner = green`, `final runtime = green`, and `rescue = no`;
- owner output, boundary verdict, state write/load, executor/tool action, final response, trace/meta;
- data ownership evidence for every business fact/action: active knowledge version or pack ref, capabilities source/verdict, operational DB row or absence, RAG/Qdrant projection status if used, and policy-core context card/ref that exposed the datum to the owner;
- internal Postgres `appointments` row for booking commits, Console Calendar visibility, appointment audit row for mutations, and role/tenant context for Console claims;
- provider truth remains separate, with Chatflow/WhatsApp `BLOCKED_NON_CODE` not blocking internal Console Calendar proof.

Tool reuse:

- generate or adapt corpus with `scripts/booking_dialog_scenarios.py` only when owner approval is recorded;
- execute with `ops/diagnose.py llm-quality` or `scripts/booking_quality_matrix_resumable.sh`;
- use `ops/diagnose.py llm-quality-matrix` when multiple packs/branches are in scope;
- close human semantic audit with `ops/diagnose.py llm-quality-audit`;
- aggregate families with `ops/diagnose.py llm-quality-trends`;
- run static gates with `ops/diagnose.py llm-quality-gates`;
- use `scripts/focused_family_proof.py` only after a classified mechanism repair;
- summarize artifacts with `scripts/quality_artifact_report.py`.

Current Pack v0 evidence:

- Owner-reviewed Pack v0 artifacts: `/tmp/truffles_real_world_salon_pack_20260503/real_world_salon_acceptance_pack_v0_20260503.json` and `/tmp/truffles_real_world_salon_pack_20260503/real_world_salon_acceptance_pack_v0_20260503.md`.
- Static validation: `/tmp/truffles_real_world_salon_pack_20260503/static_scenario_contract_pack_v0_20260503.json` and `/tmp/truffles_real_world_salon_pack_20260503/llm_quality_gates_pack_v0_20260503.json` are valid for pack shape/gates only.
- Invalid attempts are marked do-not-use: `/tmp/truffles_real_world_salon_pack_20260503/exploration_run_v0_20260503/INVALID_RUN_DO_NOT_USE.md` and `/tmp/truffles_real_world_salon_pack_20260503/exploration_smoke_outbox_v0_20260503/INVALID_RUN_DO_NOT_USE.md`.
- Corrected Tranche A diagnostic: `/tmp/truffles_real_world_salon_pack_20260503/exploration_smoke_rendered_v0_20260503/summary.json` with 3 dialogs / 14 turns, `strict_pass_rate=0.6429`, `expected_reply_rate=1.0`, `decision_meta_coverage=1.0`, and `decision_trace_coverage=1.0`.
- Failure-family map: `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_a_20260503.md` classifies P0 booking-manage under-escalation, P0 vague/daypart reschedule schema reject, P1 calendar-tool oracle review, and the repaired quality-runner transport evidence gap.
- Corrected Tranche B diagnostic: `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/summary.json` with 10 dialogs / 44 turns, `strict_pass_rate=0.6136`, `hard_fail_rate=0.0682`, `expected_reply_rate=1.0`, `decision_meta_coverage=1.0`, and `decision_trace_coverage=1.0`.
- Tranche B manual audit: `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/manual_audit.json` is `status=done`, `human_semantic_valid=false`; Tranche B remains diagnostic evidence only.
- Tranche B failure-family map: `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_b_20260503.md` classifies `FAM-B1` booking-manage/admin-confirm under-escalation, `FAM-B2` handoff lifecycle/oracle mismatch, `FAM-B3` handoff contact follow-up reclassified as booking collect, `FAM-B4` calendar-tool oracle ambiguity, `FAM-B5` fact-interruption copy ambiguity, and `FAM-B6` unsupported-service clarification weakness.
- Focused P0 repair proof: `/tmp/truffles_real_world_salon_pack_20260504/p0_handoff_repair_20260504a/p0_handoff_repair_summary_20260504a.json` is `valid=true` for 5 exact-family dialogs covering `FAM-B1` cancel/reschedule/admin-confirmation handoff and `FAM-B3` handoff contact continuation. Runtime image: `truffles-local:real-world-p0-handoff-20260504a`; release topology truth: `/tmp/truffles_real_world_salon_pack_20260504/release_topology_truth_p0_handoff_20260504a.json` is `valid=true`.
- Focused FAM-B2 lifecycle/oracle proof: `/tmp/truffles_real_world_salon_pack_20260504/fam_b2_lifecycle_repair_20260504a/fam_b2_lifecycle_repair_summary_20260504a.json` is `valid=true` with `strict_pass_rate=1.0`, `state_transition_pass_rate=1.0`, `manager_actions_total=4`, `manager_actions_ok=4`, and `expected_state_mismatch_count=0`. Scope: handoff lifecycle/oracle/manager simulation only; dev rendered evidence with `--skip-outbox`, not provider delivery or Pack v0 Acceptance.
- Invalid full-pack after-P0 attempt: `/tmp/truffles_real_world_salon_pack_20260504/pack_v0_exploration_after_p0_20260504a/INVALID_RUN_DO_NOT_USE.md`; a 48-dialog / 511-turn one-shot run was aborted and must not be reused as evidence.
- After-P0 Tranche B diagnostic: `/tmp/truffles_real_world_salon_pack_20260504/exploration_tranche_b_after_p0_20260504a/summary.json` completed 10 dialogs / 44 turns with `strict_pass_rate=0.9091`, `hard_fail_rate=0.0`, `expected_reply_rate=0.9474`, `info_answer_rate=0.5`, `handoff_correct_rate=0.8889`, `decision_meta_coverage=1.0`, and `decision_trace_coverage=1.0`; it remains `semantic_valid=false` and `infra_valid=false`.
- After-P0 failure-family map: `/tmp/truffles_real_world_salon_pack_20260504/failure_family_map_pack_v0_tranche_b_after_p0_20260504a.md` classifies `FAM-C0` evidence reliability/timeouts, `FAM-C1` generic handoff-context oracle noise, `FAM-C2` unsupported-service policy, `FAM-C3` fact-interruption copy contract, and `FAM-C4` full-pack runtime economy.
- Focused FAM-C1 oracle proof: `/tmp/truffles_real_world_salon_pack_20260504/fam_c_handoff_oracle_repair_20260504a/fam_c_handoff_oracle_repair_summary_20260504a.json` has `oracle_valid=true` for 2 dialogs / 6 turns with `strict_pass_rate=1.0`, `state_transition_pass_rate=1.0`, `failure_family_count=0`, and manager actions 4/4 OK. Scope: generic complaint/medical handoff-context scenario-oracle sanitation only; not Acceptance.
- Focused FAM-C0 evidence reliability proof: `/tmp/truffles_real_world_salon_pack_20260505/fam_c0_evidence_reliability_20260505a/fam_c0_evidence_reliability_summary_20260505a.json` is `FOCUSED_EVIDENCE_RELIABILITY_PROOF_NOT_ACCEPTANCE`; the handoff-only run has `infra_valid=true`, `strict_pass_rate=1.0`, `pass_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `webhook_errors=0`, `infra_errors=0`, `decision_meta_errors=0`, `decision_trace_errors=0`, and manager actions 4/4 OK. Scope: proof-runtime reliability only; not provider delivery, not Pack v0 Acceptance.
- Broader after-FAM-C0 Tranche B diagnostic: `/tmp/truffles_real_world_salon_pack_20260505/pack_v0_tranche_b_after_fam_c0_diagnostic_summary_20260505b.json` is `DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE`; the complete 10-dialog / 44-turn run has `infra_valid=true`, `run_integrity_valid=true`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0`, `expected_reply_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, zero webhook/infra/decision-meta/decision-trace errors, and manager actions 14/14 OK. Scope: diagnostic only; `semantic_valid=false`.
- Invalid after-FAM-C0 partial run: `/tmp/truffles_real_world_salon_pack_20260505/exploration_tranche_b_after_fam_c0_20260505a/INVALID_RUN_DO_NOT_USE.md`; it stopped after 4/44 turns and must not be reused as evidence.
- Broader after-FAM-C2/FAM-C3 Pack v0 diagnostic: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/summary.json` is the first `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE` artifact: 10 dialogs / 44 turns reached `strict_pass_rate=1.0`, but manual audit remained `human_semantic_valid=false`; it is now historical diagnostic evidence superseded for current acceptance-governance by `DL-2026-05-07-013`.
- Invalid quality-governance replay attempt: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507l/run/summary.json` must not be used as product proof or current diagnostic proof because `--jid-mode unique` still reused allowlist JIDs round-robin before replay isolation was repaired.
- Current Pack v0 quality-governance diagnostic: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/summary.json` completed 10 dialogs / 44 turns with `infra_valid=true`, `run_integrity_valid=true`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `info_answer_rate=1.0`, `handoff_correct_rate=1.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `semantic_override_rate=0.0`, `stale_state_leak_rate=0.0`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0227`, and `failure_family_count=3`; manual audit is `status=done` and `human_semantic_valid=false`.

Current limits:

- Tranche A, pre-repair Tranche B, and after-P0 Tranche B are diagnostic only; none ran strict Acceptance.
- Tranche B used dev lane rendered evidence, `--allow-judge-off`, and run-economy `warn`; it cannot update canonical quality baseline.
- Rendered transport evidence proves internal final-response observability for Exploration only; it does not prove provider delivery.
- The 2026-05-04 focused P0 repair proof is mechanism evidence only. It does not close Pack v0 Acceptance, provider delivery, Console Inbox lifecycle, or Beauty Salon v1 go-live.
- The 2026-05-04 focused FAM-B2 proof closes the pending-state lifecycle/oracle mechanism, but the llm-quality diagnostic summary still carries global dev-lane warnings (`reply_rate` threshold and skipped provider/outbox evidence). Treat the custom FAM-B2 summary as focused mechanism proof only.
- The 2026-05-04 focused FAM-C1 proof closes residual generic handoff oracle noise only. It does not close Pack v0 Acceptance or any runtime product contract.
- The 2026-05-05 focused FAM-C0 proof closes the handoff-only proof-runtime reliability slice only. It does not prove provider delivery, full Pack v0 Acceptance, or Beauty Salon v1 product readiness.
- The 2026-05-05 broader after-FAM-C0 Tranche B diagnostic clears the current infra/evidence blocker but remains semantic-invalid and diagnostic-only. `infra_valid=true` is not Acceptance.
- The 2026-05-07 focused FAM-C2/FAM-C3 repair proof closes only the focused unsupported-service availability / fact-interruption continuity slice. It does not prove broader Pack v0 Acceptance, provider delivery, appointment creation, Console Calendar visibility, or Beauty Salon v1 product readiness.
- The 2026-05-07 quality-governance repair closes the false `info_answer_rate=0.5` blocker and the expected no-response payment/media handoff evidence-timeout blocker for current diagnostics. It also invalidates 20260507l because replay isolation was not yet true unique-JID isolation.
- The current 20260507m blocker set is two actionable families: a scenario/oracle mismatch where a multi-service first turn should expect service-choice collection before time, and a runtime owner/planner contract bug where booking commit confirmation degraded with `policy_core_invalid_schema`.
- Current next blocker is mechanism-level runtime acceptance: repair the scenario/oracle expectation first, then repair the `policy_core_invalid_schema` action/tool schema mismatch without row-specific regex or semantic override.
- Full `truffles-api/tests/test_intent.py` still has broad stale/failing expectations outside the focused P0 slice; those failures must be classified by capability/layer before repair.
- Booking mechanisms must not be repaired from a single row; repairs must target the classified failure families.

Go/no-go metrics must map existing llm-quality signals to product decisions: reply rate, strict pass rate, info answer rate, degraded fallback rate, booking slot progress, handoff correctness, fact without evidence, irrelevant fact, booking commit without contact, semantic override, and stale state leak.

Run interpretation:

- Exploration lane output is a diagnostic artifact, not a product closure claim.
- P0 failures are capability-breaking or architecture-law-breaking failure families; they block Acceptance but must not stop Exploration collection.
- P1 failures are important customer-quality or Console/Ops proof gaps; they are repaired by family, not by single row.
- P2 failures are coverage, copy, or oracle-quality issues; they are queued unless they mask a P0/P1 mechanism.
- Product go/no-go is decided only after the failure-family map, repair decisions, strict Acceptance rerun, provider blocker status, and explicit ledger update.

Current repair order after 2026-05-07 Pack v0 diagnostic:

1. Do not claim Pack v0 Acceptance or Beauty Salon v1 product proof from any diagnostic Pack v0 run.
2. Repair the Pack v0 scenario/oracle expectation for multi-service service-choice collection before time collection.
3. Repair the policy-core booking commit action/tool schema mismatch that produced `policy_core_invalid_schema` on dialog `rwsp-v0-008` turn 7.
4. Rerun focused proof for that family, then broader Pack v0 diagnostic, before strict Acceptance or product-readiness claims.
5. Triage broad unit-test failures by capability/layer; do not batch-patch stale expectations as product proof.

Candidate artifacts:

- `/tmp/truffles_real_world_salon_pack_20260503/owner_review_candidate_dialogs_20260503.md` — 112 owner-review candidates, including 12 handcrafted coverage anchors plus 100 generated variants.
- `/tmp/truffles_real_world_salon_pack_20260503/owner_review_candidate_dialogs_20260503.json` — review/edit source; status `candidate_corpus_pending_owner_review`.
- `/tmp/truffles_real_world_salon_pack_20260503/exploration_scenarios_20260503.json` — candidate replay file for future Exploration; not acceptance proof.
- `/tmp/truffles_real_world_salon_pack_20260503/static_scenario_contract_20260503.json` — static scenario contract `valid=true`; proves only candidate-pack shape/coverage.
- `/tmp/truffles_real_world_salon_pack_20260503/llm_quality_gates_exploration_candidates_20260503.json` — static gates `valid=true` with warning `run_economy_gate:replay_without_baseline_summary`.
- `/tmp/truffles_real_world_salon_pack_20260503/surface_realism_audit_20260503.json` — surface realism audit after regeneration: phone formats use compact/digit-spaced variants without `+` or parentheses; time formats avoid `17:45`/`17.45`-style notation and include `17 30`, `5 30 вечера`, `вечером`, `после шести` style rows.

Do not use `/tmp/truffles_real_world_salon_pack_20260503/dry_run_contract_20260503/` as evidence; it is explicitly marked invalid because a `llm-quality --dry-run` attempt entered runtime replay/progress and was stopped before completion.

## 9.24 Single-Turn Decision/Data Ownership Audit — 2026-05-05

Status: `PROCESS_ACTIVE`.

Purpose:

- prevent a correct-looking one-message control flow from hiding wrong customer-data ownership;
- force every mechanism repair to state which data surface owns the business datum being used;
- keep scaling to other service verticals in packs/capabilities/tools/data contracts instead of core hardcode.

Required audit dimensions:

| Dimension | Required Evidence |
|---|---|
| Decision path | customer input, policy-core owner output, planner/binding, boundary verdict, state write/load, executor/tool action, final response, trace/meta, rescue/degrade flag |
| Data ownership path | Packs / Knowledge active version and refs, Capabilities source and allow/deny/fact-scope/handoff verdict, Operational DB rows for executable actions, RAG / Qdrant projection status if used, Policy-core context cards/allowed payload |

Customer Data Contract v1 must be defined before runtime repair when behavior depends on customer data:

| Data Surface | Owns | Must Not Own |
|---|---|---|
| Packs / Knowledge | customer-facing facts, prices/rules/hours/address/service taxonomy, safety/complaint/cancel/reschedule policy | executable appointment creation or semantic decision ownership |
| Capabilities | tenant/branch domain, channels, providers, features, tool allow/deny, fact scopes, handoff policy | customer facts or appointment records |
| Operational DB | branch services, specialists, specialist-service links, working booking rows, `appointments` source of truth | marketing copy or policy-core semantic meaning |
| RAG / Qdrant | retrieval/index projection for knowledge evidence | primary truth, semantic owner, or core booking calendar |
| Policy-core context | governed projection of allowed tools/refs/cards into the LLM owner | new business truth invented outside packs/capabilities/DB |

Current target facts from `/tmp/truffles_data_ownership_snapshot_20260505.json`:

- Packs / Knowledge runtime source is `knowledge_active_version`, active version `033ba3b8-a19a-4887-8587-aa761243f29c`, with 14 pack service catalog rows.
- Capabilities source is `client_capabilities`; target branch capability exists with `domain_slug=beauty`, WhatsApp/Telegram disabled, and no tool-policy records.
- Operational DB has 15 active branch services, 5 active specialists, and 15 active specialist-service links.
- RAG / Qdrant is classified as projection only and not blocking for core internal booking.

Known split-brain risk:

- Pack service catalog rows and DB bookable service rows are different surfaces and counts. This is not automatically wrong, but every acceptance row must prove whether it used pack fact truth, DB executable truth, or an explicit mapping between them.

Next allowed action:

- keep the Customer Data Contract requirement for any future data-dependent runtime repair, including broader Pack v0 diagnostics after `FAM-C2/FAM-C3`;
- reject any repair that makes regex, alias, RAG, state fallback, or executor logic the hidden semantic owner.

## 9.25 FAM-C2/FAM-C3 Focused Repair Proof — 2026-05-07

Status: `FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE`.

Decision:

- classify unsupported-service availability / booking continuation and fact-interruption continuity as shared mechanism repairs, not row-specific fixes;
- keep policy-core as the semantic owner; regex/lexicon/state/executor logic may normalize, validate, clear stale state, or render, but must not invent supported service meaning;
- treat planner timeout/degrade as explicit degraded runtime state, not as hidden success;
- treat range/daypart time constraints as partial slots requiring exact time.

Evidence:

- runtime image `truffles-local:fam-c2-c3-unsupported-focus-20260507h`, `/admin/version.build_time=2026-05-07T00:25:00Z`;
- release topology truth `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/release_topology_truth_20260507h.json` is `valid=true`;
- focused run `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/run/summary.json` has `semantic_valid=true`, `infra_valid=true`, `run_integrity_valid=true`, `strict_pass_rate=1.0`, `hard_fail_rate=0.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `fact_without_evidence_rate=0.0`, `semantic_override_rate=0.0`, and `stale_state_leak_rate=0.0`;
- manual audit `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/run/manual_audit.json` is `status=done`, `human_semantic_valid=true`;
- after canonical runtime-profile restart, `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/observability_truth_after_runtime_profile_20260507h.json` is `valid=true`; `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/provider_integration_truth_after_runtime_profile_20260507h.json` remains `valid=false` only for commercial Chatflow/WhatsApp unavailability;
- focused replies show unsupported service stays `FACT` until a supported service is selected, and vague/range time asks for an exact slot.

Known limits:

- this is a focused scripted technical proof over 2 dialogs / 10 turns, not Real-World Salon Pack v0 Acceptance;
- rendered transport evidence does not prove provider delivery;
- these rows do not create appointments and do not prove Console Calendar visibility;
- broader Pack v0 diagnostic and strict Acceptance remain pending.
- direct runtime restarts must use `scripts/restart_release.sh` runtime profile or equivalent `OUTBOX_WORKER_MODE=local_debug`; otherwise worker heartbeat/observability truth can regress.

Next allowed action:

- run a broader Pack v0 diagnostic tranche with this repair included;
- do not add another mechanism repair until remaining failures are grouped by capability/layer and audited against decision path + data ownership path.

## 9.26 Pack v0 Broader Diagnostic After FAM-C2/FAM-C3 — 2026-05-07

Status: `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE`.

Decision:

- keep the Pack v0 run as diagnostic evidence, not Acceptance, even though `strict_pass_rate=1.0`;
- preserve the repaired mechanisms: handoff semantic axes stay in semantic contracts/memory, booking-manage context updates require existing handoff memory, and unsupported-service booking continuation stays grounded `FACT` until supported service selection;
- treat the remaining blockers as acceptance-governance/evidence classification first, not as permission for row-level runtime patching.

Evidence:

- runtime image `truffles-local:booking-manage-continuity-20260507k`, `/admin/version.build_time=2026-05-07T14:10:31Z`;
- release topology truth `/tmp/truffles_real_world_salon_pack_20260507/booking_manage_continuity_20260507k/release_topology_truth_20260507k.json` is `valid=true`;
- Pack v0 diagnostic `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/summary.json` completed 10 dialogs / 44 turns with `run_integrity_valid=true`, `strict_pass_rate=1.0`, `pass_rate=1.0`, `hard_fail_rate=0.0`, `failure_family_count=0`, `blocking_reason_count=0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `handoff_correct_rate=1.0`, `post_llm_semantic_rewrite_rate=0.0`, `keyword_override_rate=0.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `booking_commit_without_required_contact=0.0`, `semantic_override_rate=0.0`, and `stale_state_leak_rate=0.0`;
- manual audit `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/manual_audit.json` is `status=done`, `evidence_handoff_valid=true`, and `human_semantic_valid=false` because this is scripted owner-proxy diagnostic evidence only.

Known limits:

- `infra_valid=false` remains because one expected no-response payment/media handoff-context turn has an unclassified decision-meta timeout;
- `semantic_valid=false` remains because `info_answer_rate=0.5` breaches the current threshold;
- the corpus is an owner-proxy synthetic pack, not raw production salon transcripts;
- rendered transport and simulated manager mode are not provider delivery proof;
- this run does not prove fresh appointment creation, Console Calendar visibility, or appointment audit lifecycle.

Next allowed action:

- run acceptance-governance before more runtime repairs: define product go/no-go mapping for llm-quality metrics, classify the one evidence timeout, and then decide whether strict Acceptance, scenario/oracle repair, or runtime mechanism repair is the next block.

## 9.27 Pack v0 Quality Governance / Replay Isolation Repair — 2026-05-07

Status: `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE`.

Decision:

- keep `DL-2026-05-07-012` as historical diagnostic evidence, but do not use it as current acceptance-governance proof;
- repair the existing quality oracle instead of weakening product gates: handoff/human wording no longer creates false info-answer expectations, pending payment/media handoff no-response evidence is soft only with handoff context, and `--jid-mode unique` creates run-scoped unique JIDs even when allowlists exist;
- classify `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507l/run` as invalid diagnostic evidence because it was produced before replay isolation was repaired;
- use `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run` as the current diagnostic evidence only, not Acceptance.

Evidence:

- Pack v0 20260507m diagnostic `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/summary.json` completed 10 dialogs / 44 turns with `infra_valid=true`, `run_integrity_valid=true`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `info_answer_rate=1.0`, `handoff_correct_rate=1.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `semantic_override_rate=0.0`, `stale_state_leak_rate=0.0`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0227`, and `failure_family_count=3`;
- manual audit `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/manual_audit.json` is `status=done`, `human_semantic_valid=false`, and separates the backlog into one product runtime family, one scenario/oracle family, and no infra/evaluator family;
- targeted quality-governance tests prove pending payment/media handoff timeout classification, handoff/human text suppression from info inference, plain master info inference, and run-scoped unique JID behavior.

Known limits:

- `semantic_valid=false` remains because dialog `rwsp-v0-008` turn 7 produced `policy_core_invalid_schema`;
- dialog `rwsp-v0-008` turn 1 is a scenario/oracle mismatch: multiple-service input should collect service choice before asking time;
- the corpus is still owner-proxy synthetic evidence, not raw production salon transcripts;
- the run does not prove provider delivery, fresh appointment creation, Console Calendar visibility, or appointment audit lifecycle.

Next allowed action:

- repair the Pack v0 scenario/oracle expectation for multi-service service-choice, then repair the policy-core booking commit action/tool schema mismatch at the owner/planner contract level and rerun focused proof plus broader Pack v0 diagnostic.

## 9.28 Business Capability Platform Constitution — 2026-05-09

Status: `CANONICAL_PLATFORM_CONTRACT_REPAIRED_DOC_ONLY`.

Decision:

- define Truffles as a business capability platform, not a universal chatbot and not a Beauty-Salon-only bot;
- keep `Beauty Salon v1` as the first proof vertical, while requiring future niches to extend the platform through packs, capabilities, tool/data contracts, operational DB rows, and governed retrieval projections;
- keep the canonical runtime hot path as the product contract: `Ingress -> policy-core owner -> planner projection -> boundary validate/degrade -> canonical state write -> executor/render -> outbox/provider`;
- treat external orchestration frameworks such as LangChain or LangGraph as optional workflow/runtime tools only, not as product architecture, semantic owner, tenant authority, booking calendar, or proof substitute;
- keep lexicons, regex, aliases, normalizers, and RAG retrieval as evidence/candidate-fact layers only; they may normalize or retrieve, but must not decide intent, invent business meaning, confirm bookings, or override the policy-core owner;
- require every meaningful turn to produce a typed business effect that can be audited through decision path, data ownership path, state diff, tool action, final reply, trace/meta, and rescue/degrade flag.

Platform scaling contract:

| Surface | Core Owns | Vertical / Tenant Owns | Forbidden |
|---|---|---|---|
| Semantics | one policy-core owner and typed owner output | domain instructions exposed through governed context | second semantic owner in regex, executor, state, or tool code |
| Business data | contracts, isolation, publication, readiness gates | services/products, prices, rules, aliases, policies, masters, inventory | hardcoded business facts in core |
| Actions | tool contract, idempotency, audit, boundary validation | capability-specific tools such as booking, order, lead, ticket, payment-handoff | direct tool execution from guessed meaning |
| State | canonical state write/load/projection | capability-specific slots and lifecycle contracts | state-layer semantic recovery |
| Observability | correlated logs, metrics, traces, health, readiness, fingerprints | per-capability go/no-go dashboards and proof bundles | green status without raw owner/final/rescue evidence |

Technology adoption gate:

- before adopting LangChain, LangGraph, another agent framework, or a new external dependency, create a Decision Ledger entry and register owner, inputs, outputs, run conditions, proof value, limitations, rollback path, and acceptance criteria in `TECH.md` / `STRUCTURE.md`;
- prove the framework on a bounded capability spike before it can enter the canonical hot path;
- reject any framework use that hides decision trace, weakens boundary validation, stores business state outside canonical contracts, or makes replay/proof harder.

Known limits:

- this section is a durable architecture/process repair, not runtime product proof;
- current code may still contain inline regex, forced-field logic, legacy compatibility projections, and fallback/degrade paths that must be classified by capability/layer before repair;
- no new framework has been adopted by this decision.

Next allowed action:

- use this platform contract as the filter before any runtime repair, dependency addition, or vertical expansion;
- classify current implementations as `KEEP / REPAIR / STRANGLE / REPLACE / SHADOW / LATER / KILL / UNKNOWN`;
- repair the remaining Pack v0 scenario/oracle and owner/planner contract blockers only after the decision path and data ownership path are explicit.

## 10. Source-Of-Truth Hierarchy

Use this reading order when deciding what to do.

| Question | Source Of Truth |
|---|---|
| What is Truffles and why does it exist? | `docs/PRODUCT_SYSTEM_CANON.md`, then `STRATEGY/VISION.md` |
| What do we sell and what is in/out of Beauty Salon v1? | `STRATEGY/PRODUCT.md`, `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md`, with this document as front door |
| How do future niches scale without core rewrites? | section `9.28`, `SPECS/ARCHITECTURE.md`, `TECH.md`, and capability/tool/data contracts |
| How should consultant runtime behave? | `SPECS/CONSULTANT.md`, `SPECS/ARCHITECTURE.md` |
| Who owns semantic meaning? | `SPECS/ARCHITECTURE.md`, runtime contracts, semantic-owner guards |
| Who owns customer data used by a turn? | section `9.24`, active DB probes, `docs/GO_LIVE_DATA_READINESS.yaml`, knowledge/capability runtime code |
| How does Console Plane work? | `docs/CONSOLE_PLANE_ACCEPTANCE_MAP.md`, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `docs/CONSOLE_AUDIT/*` |
| What infrastructure/observability is required? | `SPECS/INFRASTRUCTURE.md`, `TECH.md`, `docs/OBSERVABILITY_SURFACES.yaml`, `docs/RELEASE_TOPOLOGY_TRUTH.yaml` |
| What data/provider readiness is required? | `docs/GO_LIVE_DATA_READINESS.yaml`, `docs/PROVIDER_INTEGRATION_READINESS.yaml` |
| What is the current evidence/history? | `STATE.md`, live probes, artifact bundles |
| What changed in a specific block? | Task Package, RCA, exact proof, narrow remeasure, manual audit |

Important: `STATE.md` is evidence/history, not the product oracle. If `STATE.md` conflicts with live truth or current canon, verify with direct probes/artifacts before planning work.

## 11. Working-System Acceptance

There are two levels of acceptance.

### Behavioral Runtime Acceptance

For a runtime behavior row, success requires:

- matching runtime fingerprint;
- raw owner output is semantically correct;
- downstream layers preserve owner meaning;
- data ownership path is explicit for every business fact/action used by the turn;
- final response is correct;
- rescue is not used as the success path;
- trace/meta proves the path.

### Product Go-Live Acceptance

For `Beauty Salon v1`, success requires all required planes to be green:

- Consultant Runtime Plane: FACT/COLLECT/HANDOFF and booking matrix closure;
- Console Plane: onboarding, provisioning, inbox, support, ops, audit usable by intended roles;
- Knowledge/Data Plane: target tenant data is complete enough and published fail-closed;
- Provider Integration: webhook/provider paths are configured and externally proven;
- Observability/Ops Plane: metrics, traces, logs, alerts, workers, release topology, fingerprints are proven;
- Release Process: immutable image deploy and rollback/recovery discipline.

A single green dialog path is not product readiness.

## 12. Immediate Execution Blocks After This Canon

The next work must be selected from the verified work map, not from stale open-blocker text.

Current allowed order:

1. `No-Repeat / Process Governance Maintenance`
   - Process optimization is closed in section `9.17`; keep product work-map status, boot protocol, inventory, and deterministic guards green, but do not reopen it as a product block without fresh regression evidence.
2. `Provider/Channel Readiness Proof`
   - Only run when Chatflow/WhatsApp commercial access is restored; until then, keep the blocker visible and keep internal Console Calendar booking independent.
3. `Final Beauty Salon v1 Go-Live Review`
   - Only after fresh combined proof and provider status are resolved.

Architecture handoff is closed in section `9.16`. Process optimization is closed in section `9.17`. Shadow removal dependency proof is closed in section `9.18`. Shadow side-service removal is closed in section `9.19`. Realistic booking matrix is closed in section `9.21`. Console Lifecycle, Observability E2E, and Realistic Booking Matrix Closure are not valid next blocks unless fresh dated regression evidence changes their status.

## 9.29 Primary Pain Lock + Cordon-And-Rebuild Strategy — 2026-05-12

This section locks the single primary pain the platform must close, the operational definition of "works", and the strategy for how the platform reaches that state. It is referenced by `docs/DECISION_LEDGER.yaml` entry `DL-2026-05-12-024`, by section 13 of `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md`, and by section 11 of `STRATEGY/TECH_ROADMAP.md`. Future supersession requires a new ledger entry, not silent edits here.

`AGENTS.md` is intentionally not modified. The architectural laws restated below are already encoded in `AGENTS.md` sections 2, 8, and 10. Duplicating them in `AGENTS.md` would violate `AGENTS.md` section 12 (no duplicate docs).

### 9.29.1 Primary Pain (locked)

Truffles must not lose any incoming lead 24/7. The platform must answer, qualify, drive to a confirmed appointment, and hand off to the owner or admin where needed. Scope includes both new leads and repeat contacts from existing clients.

This is the single first-priority pain. All other pains (upsell, reactivation, revenue analytics, multi-channel) are `LATER` until this is proven closed.

### 9.29.2 Target Operating Mode

The target operating mode is autonomous. The platform conducts typical dialogs end-to-end without owner participation.

Stages on the way to autonomous (shadow, assist) are leashed-only modes used during ramp-up. They are not the product; they are gated transitions toward the product.

### 9.29.3 First Channel

WhatsApp is the first and only channel at start. The commercial WhatsApp provider blocker does not block development or integration testing. Until commercial access is restored, a mock provider with identical ingress and outbox contracts is used. Switching from mock to live provider is a Pack/adapter change, not a business-logic change.

### 9.29.4 Operational Definition of "Works" (Acceptance Gates)

All five gates are required. None may be waived for time, budget, or session pressure (per `AGENTS.md` section 13).

1. **Latency gate.** p95 reply time to a new incoming message. Threshold `TBD-after-first-batch`. Final threshold defended as "not worse than a live admin".
2. **Capture gate.** Percentage of incoming leads driven to a confirmed appointment OR an explicit qualified refusal / handoff. Threshold `TBD-after-first-batch`. Measured against the current manual owner workflow, not an absolute target.
3. **Architecture gate.** Zero violations of `single_semantic_owner`, `tool_inventory`, `decision_ledger`, `pack_is_single_source_of_truth`, `layer_isolation` guards in main.
4. **Owner self-service gate.** The owner can update price, service, specialist, and working-hours through the Pack. The mechanism (Console GUI vs. YAML) is determined by an audit of `truffles-api/app/pack_v1/*` and `console-web/*`. The gate is locked; the implementation mechanism is pending audit.
5. **Corpus gate.** Every intent enabled in autonomous-mode must have a gold set of dialogs with `owner_approved=true` on which 100% of production reactions match expected outcomes. Hard gate for autonomous-mode. Soft guideline (warn, do not block) for assist-mode.

Thresholds for gates 1 and 2 will be set in a follow-up ledger entry after the realistic corpus from `DL-2026-05-11-023` is in place.

### 9.29.5 Architectural Contract (restated from AGENTS sections 8 and 10)

These are not new laws. They are existing laws made explicit at the strategy layer so future work cannot silently violate them:

- `policy-core` LLM is the only semantic owner.
- Pack is the only source of business knowledge. Services, prices, specialists, policies, working hours, scripts come from the Pack only, not from code, prompts, or DB fixtures.
- Canonical hot path is six nodes: `Ingress -> policy-core -> planner -> boundary -> state -> executor/render -> outbox/provider`. Pack/RAG/Capabilities and Console/Ops are support planes, not pipeline nodes.
- Layer isolation is enforced. Boundary does not invent business meaning. Executor does not invent intent. State does not recover semantics from legacy fields in the live hot path.
- Corpus discipline (gate 5 above) applies to every autonomous reaction.
- Every nontrivial architectural change requires a `docs/DECISION_LEDGER.yaml` entry.

### 9.29.6 Strategy: Cordon-And-Rebuild

The legacy hot path is classified `STRANGLE` per `AGENTS.md` section 7. The v3 stack is classified `KEEP`. New behavior is built on v3 only.

`STRANGLE` set (no new behavior; deletion or projection only):
- `truffles-api/app/core/intent_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/policy_timeout_*_boundary_service.py` (four files)
- `truffles-api/app/core/pack_runtime_*_adapter.py` (seven files)
- related legacy semantic helpers

`KEEP` set (locus of all new development):
- `truffles-api/app/policy_core_v3/`
- `truffles-api/app/pack_v1/`
- `truffles-api/app/policy_core_v3_shadow/`
- `truffles-api/app/policy_core_v3_shadow_hook/`
- `truffles-api/app/policy_core_v3_corpus/`

Legacy removal occurs in a single PR after all acceptance gates in 9.29.4 pass.

### 9.29.7 Explicit Non-Goals

These are out of scope for the locked primary pain. Selecting any of them as a priority requires a superseding ledger entry first.

- Upsell, reactivation, revenue analytics.
- Multi-channel beyond WhatsApp at start.
- Google Calendar as the primary booking source.
- "Replace the administrator entirely" as a goal. Handoff to a human is a normal dialog outcome, not a failure mode.
- Investor demo as a priority driver.
- Chatflow repair while the WhatsApp provider is commercially blocked.

### 9.29.8 Phase Order

A. **Corpus.** Build 30-50 realistic owner-approved messy dialogs per `DL-2026-05-11-023`. Replace the DRAFT `truffles-api/tests/corpora/beauty_salon_pilot_v0.jsonl`. Rerun real-LLM aggregation. Carve a gold subset (~10 dialogs) that no PR may break.

B. **v3 stack to production.** No legacy edits. Boundary v2 (single service replacing four `policy_timeout_*_boundary_service.py`). Pack Runtime v1 (single adapter replacing seven `pack_runtime_*_adapter.py`). Executor v1 with decision-ledger-compatible action log. WhatsApp channel via Pack (mock provider until commercial restored). Observability v1 per-turn structured JSONL (`turn_id`, `intent`, `chosen_action`, `pack_ref`, `cost`, `latency`, `divergence_from_shadow`).

C. **Lead-24/7 product on v3.** Mira-specific Pack playbook (greeting -> qualification -> slot proposal -> confirmation -> fallback to owner). Run in shadow for 1-2 weeks. Use divergence vs. owner replies to grow the corpus. Promote to assist-mode (one-click draft for the owner). Promote to autonomous-mode per intent, each intent gated by 9.29.4 gate 5.

D. **Repo hygiene.** Background, non-blocking. `STRUCTURE.md` reduced to <= 300 lines containing only layer contracts and owner laws. Dead governance and legacy docs moved to `docs/archive/`. `# FROZEN` marker added to all STRANGLE files referencing `DL-2026-05-12-024`. Legacy deletion PR after gates pass.

Order constraint:

- A blocks everything. Gates 1, 2, and 5 are unmeasurable without A.
- B and D may run in parallel after A1.
- C may begin only after A1-A3 complete and the minimum B subset (Boundary v2 + Pack Runtime v1 + WhatsApp ingress) is in place.
