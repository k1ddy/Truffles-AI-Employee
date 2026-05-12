# CONSOLE PLANE ACCEPTANCE MAP

**Status:** CANON
**Owner:** Жанбол / Top Architect
**Updated:** 2026-04-26
**Scope:** Console Plane readiness for Beauty Salon v1: roles, lifecycle rows, proof requirements, blockers, and no-go rules.
**Out of scope:** UI implementation details, runtime behavior fixes, provider canary execution, historical status claims.
**Links:** `docs/PRODUCT_SYSTEM_CANON.md`, `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md`, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.

---

## 1. Purpose

Console Plane is the main management GUI for Truffles.

For `Beauty Salon v1`, Console is ready only when a Platform Admin and tenant roles can operate the complete lifecycle:

`onboard -> provision -> configure -> validate -> publish -> activate -> monitor -> support -> audit -> recover`

Page existence is not enough. Console readiness requires role-correct actions, tenant-scoped state, visible diagnostics, go/no-go gates, and proof that operators do not need hidden DB/container/runtime bypasses.

Console must control business/configuration state. It must not become a second semantic owner for customer runtime meaning.

## 2. Role Acceptance

| Role | Must Be Able To | Must Not Be Able To | Minimum Proof |
|---|---|---|---|
| Platform Admin | manage companies/clients/branches, provisioning, capabilities, integrations, ops, audit, support diagnostics | bypass runtime contracts or silently edit live semantic meaning | cross-tenant scoped access, lifecycle actions, audit trail, ops visibility |
| Platform Support | diagnose issues read-only, inspect ops/inbox/audit/provisioning state | create/update tenant config unless explicitly authorized | read-only support surfaces, diagnostics, no write access |
| Owner | manage salon operations, knowledge, team, settings, inbox, calendar, business/status views | access other tenants or platform-wide controls | tenant-scoped write/read proof, owner-safe status language |
| Admin | operate salon setup and daily workflows except restricted commercial/platform controls | bypass owner/platform gates | role-gated navigation/actions, audit events |
| Manager | handle handoffs, bookings, customer replies, calendar within branch scope | edit tenant-wide knowledge/settings unless explicitly read-only | branch-scoped inbox/calendar proof |
| Specialist/Viewer | optional future limited visibility | mutate core business/system configuration | not required for Beauty Salon v1 unless explicitly enabled |

## 3. Lifecycle Acceptance Rows

| ID | Lifecycle Row | Required Console Surface | Required Proof | Blocks Go-Live If |
|---|---|---|---|---|
| CPA-01 | Tenant context | Company/Client/Branch selector and fail-closed gates | `/console/v1/me` selection states, `X-Company-Id`/`X-Client-Id`/`X-Branch-Id` propagation, no implicit context | user can act without required tenant/branch context |
| CPA-02 | Platform onboarding | Tenants / Provisioning Wizard / Autopilot | create/link company, client, branch, agent; draft branch protection; audit event | branch activation depends on manual DB/container edits |
| CPA-03 | Capability configuration | Settings / Capabilities | channel/provider/feature capability visible and persisted with effective view | runtime enabled without matching capability state |
| CPA-04 | Integration setup | Integrations / webhook secret / provider status | phone + instance/provider ids + secret/status visible and scoped | provider config hidden in env/session notes only |
| CPA-05 | Knowledge authoring | Knowledge Studio | draft, validate, preview, publish, history, rollback, invalid draft blocked | salon facts edited manually outside publish/audit path |
| CPA-06 | Knowledge activation status | Knowledge + Ops | live version, published candidate, activation job/status, retry path | owner sees stale/false activation status |
| CPA-07 | Team setup | Team / Users | users, roles, branch access, Telegram linking, disable/re-scope where required | manager access cannot be controlled from Console |
| CPA-08 | Specialist/calendar setup | Team / Calendar | specialists, services, working hours/availability, booking visibility | masters/services/availability only live in prompt/code |
| CPA-09 | Inbox handoff workflow | Inbox / Case Detail | queue, chat, context, actions, take/resolve/return, diagnostics tab | handoff exists but manager lacks context/actions |
| CPA-10 | Customer reply from human | Inbox composer / media where allowed | manager outbound creates auditable provider/outbox path | support must use external/manual channel to reply |
| CPA-11 | Ops/status | Ops page / health cards | API, provider, outbox, workers, knowledge activation, release/build status visible | Platform Admin cannot locate failure from Console/Ops |
| CPA-12 | Audit | Audit page / audit events | config changes, destructive actions, publish/rollback, lifecycle actions logged | important changes leave no audit evidence |
| CPA-13 | Business status | Business/Data Trust/Team Performance/Subscription if enabled | owner/admin sees business-readable readiness, risks, queue/team/data status | status only exists in engineering/session artifacts |
| CPA-14 | Safe destructive actions | Confirmations / rollback/deactivate flows | confirmation id, reason, TTL where required, audit event | destructive actions are one-click or shell-only |
| CPA-15 | Support diagnostics | gated diagnostics in Inbox/Ops/Audit | support/admin can inspect trace/status enough to route problem | debugging requires direct DB/container access by default |
| CPA-16 | Go/No-Go summary | readiness view or explicit checklist | maps data, provider, runtime, handoff, observability, release blockers | product readiness is inferred from page availability |

Current product corrections for CPA rows:

- CPA-04 must show Chatflow/WhatsApp commercial/provider blocked state when access is unpaid or disabled; hidden logs/session notes are not enough.
- CPA-08 must treat internal Console Calendar/Postgres `appointments` as the primary salon booking source of truth.
- CPA-08 must show whether Google Calendar is disabled, optional projection, busy source, or active external sync. Google must not be implied as required for local booking.
- CPA-16 must separate internal booking readiness from external channel/provider readiness.

## 4. Beauty Salon v1 Console Rows

For the first salon target, the minimum Console proof must cover these product capabilities from `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md`:

| Beauty Capability | Console Responsibility |
|---|---|
| `BSV1-02 Tenant/branch routing` | selection gates and scoped branch context |
| `BSV1-06 Handoff` | inbox queue, case detail, manager actions, context, audit |
| `BSV1-07 Onboarding/provisioning` | wizard, draft protection, go/no-go validation |
| `BSV1-08 Knowledge publish/rollback` | validate/publish/history/rollback and activation status |
| `BSV1-09 Team and calendar setup` | users, specialists, working hours, service links, calendar visibility |
| `BSV1-10 Inbox/support workflow` | support diagnostics and operator actions |
| `BSV1-11 Tenant isolation/RBAC` | role and tenant context enforcement |
| `BSV1-12 Observability/Ops` | health, outbox, provider, worker, release/build status surfaces |
| `BSV1-15 Business status and trust` | owner/platform readiness summary and risk language |

## 5. Known Canon-Vs-Implemented Gaps

This document does not prove current Console readiness. It records acceptance target and known blocker classes from current docs.

Known gaps from `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`:

| Gap | Impact |
|---|---|
| `integrations_rbac_scope` | Integrations page exists, but owner/admin access is narrower than canon. Decide whether Beauty v1 requires tenant owner/admin integration visibility or Platform Admin-only is acceptable. |
| `team_users_invite_disable` | Users list exists, but invite/disable is incomplete. Blocks self-serve team lifecycle if owner/admin must manage users without Platform Admin. |
| `team_specialists_availability` | Specialists list exists, but working-hours/availability management is incomplete. Blocks full salon calendar/team setup if availability must be managed in Console. |
| `canon_ia_drift_business_pages` | Business/Data Trust/Team Performance/Subscription exist ahead of canon. Blocks clean acceptance unless canon either adopts or explicitly excludes these pages. |
| `canon_ia_drift_company_workspace` | Company Workspace exists ahead of canonical IA. Blocks clean Platform Admin acceptance until classified. |

These gaps are not runtime defects. They are Console acceptance blockers or scope decisions.

### 5.1 Reality-First Console Correction — 2026-04-26

Console Plane is the main management GUI, but Console work must not become disconnected UI side-work.

Current runtime facts:

- Console Web is part of the required release cohort and is running with build SHA `9db031ee967999545f8a9673e7e57cf4d7202e73`.
- Console Web uses `NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1`, so the intended path is `Console Web -> FastAPI /console/v1`.
- FastAPI Console routes read/write the core API database behind `DATABASE_URL`, currently `truffles_postgres_1` / `chatbot`.
- `truffles-console-postgres` exists, but it is not the current Console API source of truth for salon appointments.
- Internal Calendar acceptance must prove create/read/update visibility through `/console/v1/calendar/*` and the core `appointments` table.
- Chatflow/WhatsApp readiness must be visible as a provider blocker, but code-level Chatflow repair is not a valid Console readiness task while commercial access is unavailable.

Therefore the next Console proof must connect the full operator path:

`role/session -> tenant context -> Console API -> core DB state -> Calendar/Inbox/Ops UI -> audit/diagnostic evidence`

Do not claim Console readiness from:

- page existence;
- a separate local DB;
- direct shell/DB edits;
- provider configuration alone;
- a green `/health` endpoint without role, tenant, state, and audit proof.

### 5.2 Internal Calendar Kernel Proof — 2026-04-26

API-level Platform Admin proof is now available for the internal Console Calendar kernel.

Evidence bundle:

- `/tmp/truffles_console_calendar_kernel_proof_20260426`

Proven path:

`Keycloak token -> Platform Admin -> X-Company-Id/X-Client-Id/X-Branch-Id -> /console/v1 -> /calendar/* -> truffles_postgres_1/chatbot.appointments -> appointment_audit -> /business/go-no-go-readiness`

Observed results:

| Check | Result |
|---|---|
| Tenant context | `GET /console/v1/me` resolves `platform_admin` on `demo_salon/main` when explicit company/client/branch headers are sent |
| Specialists | `GET /console/v1/calendar/specialists` returns active specialists for the target branch |
| Create booking | `POST /console/v1/calendar/bookings` created appointment `b92ca518-1cee-4a8c-b8a0-5ed47de21cd8` |
| API readback | `GET /console/v1/calendar/bookings` found the created booking by target date |
| DB readback | active DB row exists in `appointments` with `source=console`, `confirmation_policy=client`, target client/branch, and proof marker |
| Cleanup | `POST /console/v1/calendar/bookings/{id}/cancel` changed status to `CANCELLED` |
| Audit | `appointment_audit` records `agent / console / cancel / CONFIRMED -> CANCELLED` |
| Readiness separation | `/business/go-no-go-readiness` reports `internal_booking_ready=true`, `external_channel_ready=false`, `provider_ready=false`, `runtime_ready=true` |

Current Console verdict from this proof:

- `CPA-01 Tenant context`: partial pass for Platform Admin API path with explicit headers.
- `CPA-08 Specialist/calendar setup`: partial pass for read/create/readback/cancel against internal `appointments`.
- `CPA-11 Ops/status`: partial pass for Console health and Go/No-Go readiness separation.
- `CPA-16 Go/No-Go summary`: partial pass for separating internal booking readiness from external provider blockage.

### 5.3 Internal Calendar Slots and GUI Proof — 2026-04-26

Follow-up evidence bundle:

- `/tmp/truffles_reality_architecture_recovery_20260426/console_calendar_slots`

Runtime blocker found and fixed:

- `GET /console/v1/calendar/slots` returned HTTP `500` for a valid UUID `specialist_id`;
- traceback showed `AttributeError: 'UUID' object has no attribute 'replace'`;
- root cause: FastAPI already converted `specialist_id: UUID`, but the endpoint wrapped it again with `UUID(specialist_id)`;
- fix: pass the UUID directly to `SchedulingService.get_available_slots` and serialize `specialist_id` as string in `SlotsResponse`.

Proven after deploy:

| Check | Result |
|---|---|
| Runtime fingerprint | `/admin/version.git_commit=9db031ee967999545f8a9673e7e57cf4d7202e73`, `/admin/version.build_time=2026-04-26T13:14:04Z` |
| Semantic preflight | `valid=true` |
| Slots API | HTTP `200`, `9` slots for Айгерим Болатова / Маникюр / `2026-05-01` |
| Browser GUI | Console Web created appointment `79a9eca5-18ce-48ba-b925-1b32925f71b1` through Calendar composer |
| GUI visibility | created appointment was visible in Calendar list screenshot |
| DB cleanup | appointment status is `CANCELLED`, `source=console` |
| Audit | `appointment_audit` records `agent / console / cancel / CONFIRMED -> CANCELLED` |
| API proxy errors | no failed `/api/proxy/calendar` or `/api/proxy/me` responses during successful proof |

Current Console verdict after this proof:

- `CPA-01 Tenant context`: partial pass for Platform Admin browser path with selected company/client/branch.
- `CPA-08 Specialist/calendar setup`: stronger partial pass for Platform Admin GUI slot-read/create/list proof against internal `appointments`.
- `CPA-11 Ops/status`: unchanged partial pass; this proof used runtime fingerprint and semantic preflight but does not prove full Ops UI lifecycle.

### 5.4 Calendar Role Lifecycle Proof — 2026-04-26

Evidence bundle:

- `/tmp/truffles_console_role_lifecycle_proof_20260426`

Why this proof exists:

- Console readiness cannot be claimed from Platform Admin alone.
- Calendar access must be proven through real roles, tenant context, API enforcement, GUI behavior, DB state, and audit.
- Following OWASP authorization guidance, denial for lower-privilege roles must be verified server-side, not only hidden in UI.

Proven:

| Role | API Result | GUI Result | Verdict |
|---|---|---|---|
| `manager` | `/me=200`, `/calendar/specialists=200`, `/calendar/bookings=200` | Calendar opened, booking composer worked, created appointment visible in list | pass |
| `support` | `/me=200`, `/calendar/specialists=403`, `/calendar/bookings=403` | Calendar route shows access denied | pass, least-privilege denial |
| `platform_admin` | baseline proof already exists | baseline proof already exists | pass |

Manager proof appointment:

- `7bca5973-bf85-49ad-a951-a7ec3dbf6d3e`;
- created through Console Web as `manager`;
- visible in Calendar list screenshot;
- cancelled through Console API cleanup;
- DB after cleanup: `status=CANCELLED`, `source=console`, marker `role_lifecycle_proof_20260426_ad7e5be1`;
- `appointment_audit`: `agent / console / cancel / CONFIRMED -> CANCELLED`.

Current Console verdict after this proof:

- `CPA-01 Tenant context`: partial pass for Platform Admin and Manager on `demo_salon/main`.
- `CPA-08 Specialist/calendar setup`: stronger partial pass for Platform Admin and Manager internal Calendar lifecycle.
- `CPA-03 Support tooling`: partial pass for explicit Calendar denial, but support diagnostics flow is not closed.

Later verified status:

- Owner/Admin/Manager/Support/Platform Admin lifecycle proof is now `PROVEN` in the 2026-04-29 Console lifecycle artifact bundle.
- Handoff/inbox lifecycle, readiness blocker visibility, support diagnostics, support write-denial, manager calendar create/read/cancel, and mutation audit evidence are proven for the acceptance slice.
- Invite/disable and specialist availability management remain scope decisions for broader self-serve Console maturity, not blockers to the recorded Console lifecycle proof.
- External provider canary remains blocked until Chatflow/WhatsApp commercial access is restored.


### 5.5 Target Architecture Recovery Correction — 2026-04-26

Reality recovery found repaired release/data issues that Console must surface if they recur instead of hiding:

| Blocker | Evidence | Console Meaning |
|---|---|---|
| Release cohort drift | drift was found and reconciled; final `release_topology_truth.valid=true` | Ops/Go-No-Go should surface this class of mismatch if it recurs |
| Calendar catalog ownership drift | repaired on 2026-04-26: `demo_salon/main` has 15 active services, 15 target-branch specialist-service links, and 0 cross-branch service links | Calendar/Team/Data Trust must keep failing or warning if branch-inconsistent services recur |

This does not invalidate the Platform Admin/Manager Calendar proof. It changes the interpretation: Calendar create/read/cancel works as an internal kernel, and the catalog ownership blocker is now repaired for `demo_salon/main`. The later 2026-04-29 lifecycle proof extends this to role/tenant/readiness/handoff/audit acceptance for the recorded slice.

### 5.6 Console Lifecycle Acceptance Proof — 2026-04-29

Evidence bundle:

- `/tmp/truffles_delivery_track_20260428/console_lifecycle_acceptance_summary_20260429.json`
- `/tmp/truffles_delivery_track_20260428/console_lifecycle_api_proof_20260429.json`
- `/tmp/truffles_delivery_track_20260428/console_lifecycle_gui_proof_20260429.json`

Status:

| Acceptance Area | Result |
|---|---|
| Product closure | `console_lifecycle_acceptance=PROVEN` |
| Real roles | `platform_admin`, `owner`, `admin`, `manager`, and `support` all proven as real roles |
| Calendar lifecycle | manager create/read/cancel works; support calendar write denied |
| Handoff/inbox | handoff case visible to manager; support inbox write denied |
| Readiness | Platform Admin and Owner/Admin see readiness; provider blocker visible; internal booking shown as not blocked |
| Audit | calendar mutation audit is recorded |
| GUI proof | Owner business/data trust, Manager calendar/inbox, Support ops/audit/denial, Platform Admin tenants/ops screenshots exist |

Current Console decision:

- keep Console Plane as the main GUI for Beauty Salon v1;
- do not rerun `Console Plane Acceptance Proof` unless fresh dated regression evidence changes this status;
- continue with architecture consolidation/handoff or specific Console capability closure only when a selected business capability requires it.

## 6. Proof Requirements

Console Plane acceptance proof should produce an artifact bundle with:

- role used for each row;
- selected company/client/branch;
- route/page/API exercised;
- before/after state where a mutation occurs;
- audit event or idempotency proof for mutations;
- screenshot or structured output for GUI proof if needed;
- API response or DB readback for state proof;
- explicit `pass/fail/blocked` verdict per row;
- blocker surface if failed: `rbac`, `tenant_context`, `missing_surface`, `stale_canon`, `implementation_gap`, `ops_visibility_gap`, `runtime_dependency`.

Minimum deterministic checks before claiming a row:

- Console API contract or targeted test for the row;
- role/RBAC assertion;
- tenant context assertion;
- audit/state readback for write paths;
- no hidden direct DB/container step as the success path.

## 7. No-Go Rules

Do not claim Console readiness if:

- readiness is based only on page existence;
- the happy path requires direct database edits or shell commands by default;
- Platform Admin cannot see why a branch is blocked;
- tenant roles can act without proper company/client/branch context;
- owner/admin status text hides activation/provider/runtime failures;
- Console changes customer runtime meaning downstream of policy-core;
- support diagnostics require unrestricted access to production internals instead of gated Console/Ops surfaces.

## 8. Readiness Levels

| Level | Meaning | Allowed Claim |
|---|---|---|
| C0 — Defined | row exists in this map | acceptance target defined |
| C1 — Implemented Surface | route/page/API exists | surface exists, not proven |
| C2 — Role-Scoped Proof | correct role can use it in selected tenant context | row internally proven |
| C3 — Lifecycle Proof | row works as part of onboarding/support flow | Console lifecycle ready for that row |
| C4 — Go-Live Console Ready | all required rows pass for target salon | Console Plane ready for Beauty Salon v1 |

No row may jump from C1 to C4 without role, tenant, state, and evidence proof.

## 9. Next Valid Blocks

After this map, valid follow-up work is one of:

1. `Console Canon/IA Drift Resolution`
   - decide and encode Business/Data Trust/Team Performance/Subscription and Company Workspace canon status if they block usability or handoff.
2. `Console Team/Calendar Capability Closure`
   - implement/prove invite/disable and specialist availability only if selected as required for Beauty v1 self-serve operation.
3. `Architecture Consolidation / Handoff Package`
   - make proven Console/runtime/data/ops paths readable for third-party review and future agent sessions.
4. `External Provider Canary Proof`
   - run only after the provider is commercially available; if Chatflow/WhatsApp is unpaid/disabled, the valid block is visible readiness/blocker evidence, not code-level provider repair.

Selection rule:

- If Calendar/Team data is branch-inconsistent, repair and surface data trust first.
- If the goal is to know whether the GUI is actually usable now, read the 2026-04-29 lifecycle artifact first; rerun only on fresh regression evidence.
- If acceptance fails because canon and implementation disagree, run `Console Canon/IA Drift Resolution`.
- If acceptance fails on team/calendar functionality, run `Console Team/Calendar Capability Closure`.
