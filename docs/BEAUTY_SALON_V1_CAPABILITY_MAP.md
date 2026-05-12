# BEAUTY SALON V1 CAPABILITY MAP

**Status:** CANON
**Owner:** Жанбол / Top Architect
**Updated:** 2026-05-09
**Scope:** first commercial vertical acceptance map: what must work for a beauty salon, which planes own it, what proof is required, and what is not in scope.
**Out of scope:** implementation, historical status, marketing copy, runtime proof artifacts.
**Links:** `docs/PRODUCT_SYSTEM_CANON.md`, `STRATEGY/PRODUCT.md`, `SPECS/CONSULTANT.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/INFRASTRUCTURE.md`, `docs/GO_LIVE_DATA_READINESS.yaml`, `docs/PROVIDER_INTEGRATION_READINESS.yaml`, `docs/OBSERVABILITY_SURFACES.yaml`.

---

## 1. Purpose

`Beauty Salon v1` is the first paid operating slice of Truffles.

The goal is not to prove that one bot response works. The goal is to prove that a beauty salon can be onboarded, configured, operated, monitored, and supported through Truffles with the minimum business functionality required to stop losing customer requests and convert conversations into clear outcomes.

This map is the business-level oracle for the first vertical. Future implementation blocks must map to one of these capabilities or explain why the map must change first.

## 2. Customer And User Scope

| Actor | Uses Truffles For | Required Surface |
|---|---|---|
| End customer | asks questions, starts booking, reaches manager when needed | active customer channel/runtime channel; WhatsApp only when commercially enabled |
| Salon Owner | controls business data, sees status, trusts operation | Console Plane |
| Salon Admin | manages knowledge, team, settings, integrations | Console Plane |
| Manager | handles handoffs, bookings, customer replies | Console Inbox/Calendar, paging fallback |
| Platform Admin | onboards, provisions, verifies, supports, troubleshoots | Console Plane + Ops Plane |
| Platform Support | diagnoses incidents safely without hidden runtime bypass | Console diagnostics + traces/logs/metrics |

## 3. Minimum Business Promise

For the first salon, Truffles may promise only this:

- customers receive grounded answers about the salon;
- customers can move into booking intake;
- exact booking confirmation happens only when a real provider/tool supports it;
- when automation cannot safely continue, handoff to a manager is explicit and visible;
- Platform Admin can operate onboarding, readiness, support, and go/no-go from Console/Ops surfaces;
- the system is observable enough to debug failures quickly.

### 3.1 Platform Scaling Boundary

`Beauty Salon v1` is the first proof vertical, not a reason to make the core salon-specific.

Reusable core mechanisms:

- tenant/branch routing;
- policy-core semantic ownership;
- typed planner/boundary/state/executor contracts;
- capability manifests and tool contracts;
- Console readiness, RBAC, audit, and support workflow;
- correlated logs, metrics, traces, health, readiness, and release proof.

Salon-owned extensions:

- service catalog, aliases, prices, durations, masters, booking rules, policies, and safety rules;
- appointment lifecycle through internal Console Calendar/Postgres `appointments`;
- salon-specific handoff and manager workflows.

Future verticals must replace or extend the vertical-owned layer through packs, capabilities, tools, and data contracts. They must not add hardcoded semantic branches to core.

## 4. Required Data Contract

A Beauty Salon v1 tenant is not go-live ready unless the target branch has enough published data for the runtime to avoid guessing.

Required data:

| Data Area | Minimum Required |
|---|---|
| Business identity | salon/client name, branch name, branch status |
| Address/location | address, location notes, parking if claimed |
| Working hours | regular hours, exceptions if available, after-hours behavior |
| Services | service catalog with names, aliases if available, active/inactive status |
| Prices | explicit price or safe price policy per service/category |
| Durations | explicit duration or safe duration policy per service/category |
| Specialists/masters | names, service links, availability policy if used |
| Booking rules | required slots, contact requirements, commit policy, cancellation/reschedule policy if allowed |
| Policies | guests, late arrival, deposits/payment policy if explicitly allowed, contraindication/medical escalation rule |
| Languages | RU required; KZ/mixed support only if proven by data and runtime evidence |
| Provider config | channel provider identifiers if channel is enabled, webhook secret/instance mapping, internal `calendar_provider=local`, external calendar/CRM only if used as projection or busy source |

If required data is missing, runtime safe-mode may protect the customer experience, but safe-mode is not go-live readiness.

## 5. Capability Map

| ID | Capability | Business Outcome | Required Planes | Minimum Proof | Not Ready If |
|---|---|---|---|---|---|
| BSV1-01 | Channel ingress/outbound | customer messages arrive and replies are delivered | Runtime + Provider + Ops | real inbound row, outbox row, provider/send status, correlated ids | only config exists, no real canary, or provider is commercially blocked |
| BSV1-02 | Tenant/branch routing | message reaches the correct salon/branch | Runtime + Data + Console | tenant/branch context in trace/meta, no implicit context, selection gates | branch inferred by fallback or wrong instance |
| BSV1-03 | Fact answers | customer gets grounded salon facts | Runtime + Knowledge/Data + Ops | exact proof for address/hours/services/prices/duration/masters/rules, fact source visible | answer uses guessed fact or broad ungrounded text |
| BSV1-04 | Booking intake | customer can give service, datetime, name, contact if required | Runtime + State + Ops | representative booking matrix with `raw owner = green`, `final runtime = green`, `rescue = no` | a fresh dated regression shows owner, runtime, rescue, appointment, or Console visibility failure |
| BSV1-05 | Exact booking commit | confirmed appointment is real | Runtime + Console Calendar/Data + Ops; external Provider only if used | Console Calendar/Postgres appointment row or tool-backed external provider commit, trace/tool outcome, idempotency | bot promises exact free slot without Console Calendar or configured provider |
| BSV1-06 | Handoff | manager receives context and customer sees status | Runtime + Console + Outbox + Ops | visible handoff state, manager context, provider/outbox proof, audit trail | silent drop, manager lacks context, or status hidden |
| BSV1-07 | Console onboarding/provisioning | Platform Admin can launch a branch without manual magic | Console + Data + Ops | wizard/go-no-go proof, draft protection, capability-aware validation | launch depends on shell-only/manual DB/container edits |
| BSV1-08 | Knowledge publish/rollback | salon facts can be safely updated | Console + Knowledge/Data + Runtime | validate -> preview -> publish -> sync -> rollback proof, invalid draft blocked | pack edited manually without publish/audit path |
| BSV1-09 | Team and calendar setup | managers/specialists can be configured and used | Console + Data + Provider | users/roles, specialists, services, working hours, branch scope evidence | masters/services live only in prompt or code |
| BSV1-10 | Inbox/support workflow | operators can work handoffs and support can diagnose | Console + Ops | queue/chat/details/diagnostics visible by role, take/resolve/retry/audit proof | support requires direct DB/container access |
| BSV1-11 | Tenant isolation/RBAC | one client cannot see or affect another | Console + Data + Runtime + Ops | company/client/branch selection gates, scoped queries, audit evidence | implicit tenant context or cross-tenant fallback exists |
| BSV1-12 | Observability/Ops | failures are detectable and explainable | Ops + Runtime + Console + Workers | Prometheus/Grafana/OTel-class traces/logs/metrics, health/readiness, worker heartbeat | dashboards exist but no end-to-end correlated proof |
| BSV1-13 | Release/runtime topology | deployed system matches intended build and services | Ops + Runtime + Console + Workers | immutable image, build fingerprint, release topology truth, worker/outbox proof | runtime commit mismatch or shadow service owns live behavior |
| BSV1-14 | Policy/no-go safety | bot does not make forbidden claims | Runtime + Knowledge/Data + Console | hard-law/policy proof for payments, medical/legal, discounts, availability, OOD | discounts/payments/medical advice are generated without explicit policy/tool |
| BSV1-15 | Business status and trust | owner/platform sees whether salon is ready | Console + Ops + Data | readiness summary maps data, provider, runtime, handoff, observability, release | readiness is scattered across session notes only |

## 6. Runtime Acceptance Matrix

The runtime subset of Beauty Salon v1 is not one scenario. It must include at least these rows:

| Runtime Row | Required Result |
|---|---|
| Missing service | collect or clarify service without losing booking intent |
| Exact datetime | preserve explicit date/time and continue to missing slot |
| Info interrupt | answer grounded fact and resume booking |
| Specialist carryover | preserve chosen/requested specialist when asking follow-up |
| Name fill | accept name as slot fill, not as unrelated text |
| Restart/resume | persisted state restores active booking correctly |
| Commit readiness | do not confirm exact appointment unless provider/tool proves it |
| Grounded fact interrupt | answer facts from pack/tool while preserving active booking context |
| Generic info after active booking | side question does not erase expected booking slot |
| Post-interrupt progression | after side answer, next prompt advances to the correct slot |
| Name to commit progression | after name/contact, either provider commit or explicit handoff/next step |
| Variants | promotions, duration, master, parking, location if present in salon data |

Each row requires `raw owner = green`, `final runtime = green`, and `rescue = no` before it can count as closed.

## 7. Console Acceptance Matrix

Console Plane must be evaluated as a product surface, not only as UI pages.

| Console Row | Required Result |
|---|---|
| Platform Admin onboarding | can create/link company, client, branch, channel, knowledge, booking settings |
| Go/No-Go | branch cannot go live with missing required capability fields |
| Knowledge Studio | validate, publish, history, rollback, invalid draft blocked |
| Integrations | provider identifiers/secrets/status are visible and scoped |
| Inbox | handoff queue, case detail, chat, context, diagnostics, actions |
| Calendar/team | specialists, services, working hours, bookings visible by role |
| Ops/status | health, outbox, provider, workers, release/build status visible enough for support |
| RBAC/tenant context | role navigation and API gates match company/client/branch context |
| Audit | important operator changes and destructive actions leave evidence |

This matrix should become the next dedicated block if Console readiness is selected as the next product blocker.

## 8. Go-Live Readiness Levels

Use these levels to avoid false closure.

| Level | Meaning | Allowed Claim |
|---|---|---|
| L0 — Defined | capability is documented | scope exists |
| L1 — Configured | data/config exists | internally configured, not proven |
| L2 — Internal Proof | local/runtime proofs pass | internal readiness for that row |
| L3 — External Canary | real provider/channel/customer-like path is proven | canary green for that row |
| L4 — Go-Live Ready | all required rows across planes are green | Beauty Salon v1 target ready |

A row cannot jump from L1 to L4. Provider, runtime, Console, data, observability, and release proofs are separate gates.

## 9. Explicit Non-Goals For Beauty Salon v1

Do not include in Beauty Salon v1 unless a later canon change says otherwise:

- generic assistant for all topics;
- payments, refunds, bank operations;
- medical/legal advice;
- exact free slot promises without internal Console Calendar or configured calendar/CRM provider;
- treating WhatsApp/Chatflow provider repair as an application-code closure path while the provider is commercially unavailable;
- treating Google Calendar as required for internal Console Calendar booking;
- auto-learning without approval workflow;
- multi-vertical rollout beyond salon/barbershop-like service businesses;
- custom core logic per salon;
- hidden support workflows outside Console/Ops;
- claiming production readiness from a single runtime proof.

## 10. Current Blocker Surfaces

This document does not assert current pass/fail for every row. It defines the acceptance target.

Known blocker surfaces from the current canon/context:

| Surface | Why It Blocks Go-Live |
|---|---|
| Provider canary | configuration/readiness is not the same as real external inbound/outbound proof |
| Shadow removal dependency proof | stopped shadow services are non-authoritative, but full removal still needs caller/dependency proof |
| Semantic ownership regression risk | downstream rescue/rewrite must stay forbidden; proven rows need guards when touched |
| Data/provider separation | target data readiness and internal booking proof do not imply external provider/channel go-live |

### 10.1 Reality Readiness Snapshot — 2026-05-01

This snapshot records verified facts from the active worktree/runtime and artifact bundles. It is not full go-live closure.

| Area | Current Fact | Product Meaning |
|---|---|---|
| Active runtime cohort | image drift was found and reconciled; final `release_topology_truth.valid=true` | live acceptance can use the current cohort after repeating fingerprint/topology checks |
| Runtime fingerprint | active worktree HEAD and `/admin/version.git_commit` both equal `9db031ee967999545f8a9673e7e57cf4d7202e73` | live probes can be trusted only after this check is repeated |
| Active operational DB | API `DATABASE_URL` points to `truffles_postgres_1` / `chatbot`; `appointments` exists and has live rows | internal Console Calendar proof must use this DB unless a migration decision changes ownership |
| Console DB | `truffles-console-postgres` exists separately and is not the current appointment source of truth | do not build booking acceptance around the separate Console DB by accident |
| Target data | final `go_live_data_truth.valid=true`; minimum pack contract and operational service integrity are ready for `demo_salon/main` | target data no longer blocks internal Console Calendar/booking acceptance; non-target fleet residuals remain report-only |
| Provider channel | `provider_integration_truth.valid=false`; Chatflow/WhatsApp is commercially unavailable | external WhatsApp go-live is blocked by provider/commercial access, not by an application-code fix |
| Internal booking | provider truth says `internal_booking_blocked_by_provider=false`; Console Calendar and Booking Matrix proofs use internal `appointments` | internal Console Calendar booking is proven independently of the external provider blocker |
| Observability | `observability_truth.valid=true` and correlated E2E turn proof exists | internal observability proof is closed; provider canary remains separate |
| Booking runtime | scripted D1 matrix remains `PARTIAL_MECHANISM_PROVEN`; the 2026-05-03 16-row matrix is `SCRIPTED_TECHNICAL_PROOF` with policy-core owner, final runtime green, no rescue flags, internal appointments, and Console Calendar visibility | `BSV1-04` has useful live technical evidence, but real-world product proof requires the Real-World Salon Acceptance Pack with owner-approved messy dialogs; external provider/channel go-live remains separate |
| Console lifecycle | role/tenant/state/audit/GUI lifecycle proof is `PROVEN` across Platform Admin, Owner, Admin, Manager, and Support | Console lifecycle is not the next product block unless fresh regression evidence appears |
| Calendar catalog data | repaired: target branch has 15 active `services`; 15 specialist-service links are target-branch scoped; cross-branch service links are 0 | `BSV1-09` data blocker is closed for `demo_salon/main`; guard must stay green |
| Data ownership path | `/tmp/truffles_data_ownership_snapshot_20260505.json` records Packs / Knowledge, Capabilities, Operational DB, RAG / Qdrant, and Policy-core context ownership for `demo_salon/main` | every accepted runtime row must prove both decision path and data ownership path; service catalog differences are a Customer Data Contract issue, not a hidden fallback path |

Internal Console Calendar kernel proof on 2026-04-26:

- artifact bundle: `/tmp/truffles_console_calendar_kernel_proof_20260426`;
- follow-up GUI/slots artifact bundle: `/tmp/truffles_reality_architecture_recovery_20260426/console_calendar_slots`;
- role lifecycle artifact bundle: `/tmp/truffles_console_role_lifecycle_proof_20260426`;
- role/context: `platform_admin` with explicit `demo_salon/main` tenant headers;
- API path proven: `GET /console/v1/me`, `GET /console/v1/calendar/specialists`, `POST /console/v1/calendar/bookings`, `GET /console/v1/calendar/bookings`, `POST /console/v1/calendar/bookings/{id}/cancel`;
- DB path proven: active `truffles_postgres_1/chatbot.appointments`;
- proof booking: `b92ca518-1cee-4a8c-b8a0-5ed47de21cd8`, created through Console Calendar API and then cancelled through Console Calendar API;
- slot-read runtime path: `/console/v1/calendar/slots` returns HTTP `200` for valid UUID specialist query after the 2026-04-26 runtime fix;
- browser GUI path: Console Web created and displayed appointment `79a9eca5-18ce-48ba-b925-1b32925f71b1`, then cleanup cancelled it through Console API;
- Manager role GUI path: Console Web created and displayed appointment `7bca5973-bf85-49ad-a951-a7ec3dbf6d3e`, then cleanup cancelled it through Console API;
- Support role denial path: Calendar API returns `403` and GUI shows Calendar access denied;
- active DB readback before cleanup: `status=CONFIRMED`, `source=console`, `confirmation_policy=client`, target branch `demo_salon/main`;
- DB audit after cleanup: `appointment_audit` row records `actor_type=agent`, `channel=console`, `action=cancel`, `CONFIRMED -> CANCELLED`;
- Console Go/No-Go readiness correctly separates `internal_console_calendar_booking.status=pass` from external provider/channel blockers.

This proves the internal Console Calendar / active DB kernel is usable. Later lifecycle and matrix artifacts extend this to real role lifecycle proof and scripted booking technical evidence; real-world product proof remains gated by section `10.3`.

### 10.2 Verified Readiness Snapshot — 2026-05-01

| Block | Status | Evidence |
|---|---|---|
| Console Lifecycle Acceptance Proof | `PROVEN` | `/tmp/truffles_delivery_track_20260428/console_lifecycle_acceptance_summary_20260429.json` |
| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` | `/tmp/truffles_delivery_track_20260428/booking_matrix_20260430_after_fix_i_full2/booking_matrix_semantic_audit_20260430i_full2.json`; reclassification RCA `/tmp/truffles_real_booking_matrix_20260502/booking_matrix_reclassification_rca_20260502.md` |
| Realistic Booking Matrix Closure | `SCRIPTED_TECHNICAL_PROOF` | `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/realistic_booking_matrix_product_summary_20260503g_fresh.json`; Console visibility `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/console_calendar_visibility_product_summary_20260503g_fresh.json`; decision ledger `DL-2026-05-03-001` |
| Observability End-To-End Turn Proof | `PROVEN` | `/tmp/truffles_delivery_track_20260428/observability_e2e_turn_summary_20260430.json` |
| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` | Chatflow/WhatsApp commercial access unavailable |

Current non-closed surfaces:

1. external provider/channel canary after commercial access is restored;
2. Real-World Salon Acceptance Pack for `BSV1-04/05/06` runtime proof on owner-approved messy dialogs;
3. final Beauty Salon v1 go-live review after fresh combined proof and provider status decision;
4. regression guards whenever proven Console/runtime/booking/observability surfaces are touched.

### 10.3 Real-World Salon Acceptance Pack — 2026-05-03

Status: `OWNER_REVIEWED_CORPUS_V0_AFTER_FAM_C0_DIAGNOSTIC_COMPLETE`.

This pack is the required next acceptance path for runtime product readiness. It must include owner-approved messy dialogs covering RU/KZ/mixed/translit, short fragmented messages, voice transcript style, cancellation/reschedule, complaint/medical/refund/payment confirmation handoff, price/duration interruptions, multiple services, vague time, missing contact/name, duplicate/retry, no-slot negotiation, unavailable service, and human request rows.

Each accepted row requires `raw owner = green`, `final runtime = green`, `rescue = no`, exact DB/Console/audit/trace proof, and capability/layer classification before any repair.

Each accepted row also requires data ownership evidence: active pack/version or fact ref for customer-facing facts, capability source/verdict for allowed actions, operational DB row or absence for executable actions, RAG / Qdrant projection status if used, and policy-core context card/ref that exposed the datum to the owner.

Execution model:

- Internal Pilot Proof is allowed because raw production salon transcripts do not exist yet.
- Existing registered tools generate candidate dialogs; the owner selects/edits/approves the sample.
- Approved rows become an owner-reviewed synthetic messy corpus: pilot proxy, not raw production transcripts.
- Exploration lane runs through behavioral failures to collect the complete failure-family map.
- Only invalid-run conditions stop Exploration: wrong runtime/tenant, broken scenario contract, missing trace/meta/owner output, or contaminated evidence.
- Repair starts only after failures are grouped by capability and architecture layer.
- Acceptance remains strict after repairs; Exploration diagnostics do not relax product go/no-go.
- Pack v0 is owner-reviewed and approved as an Internal Pilot Proof proxy only; it is not raw production transcript proof.
- Dev Exploration may use rendered assistant evidence to decouple semantic diagnosis from blocked provider delivery, but Acceptance must use delivery transport evidence.

Pack v0 evidence:

- `/tmp/truffles_real_world_salon_pack_20260503/owner_review_candidate_dialogs_20260503.md` contains the 112 review candidates used for selection.
- `/tmp/truffles_real_world_salon_pack_20260503/real_world_salon_acceptance_pack_v0_20260503.md` is the owner-reviewed Pack v0 selected from the candidate corpus.
- `/tmp/truffles_real_world_salon_pack_20260503/static_scenario_contract_pack_v0_20260503.json` is `valid=true` for static scenario contract only.
- `/tmp/truffles_real_world_salon_pack_20260503/llm_quality_gates_pack_v0_20260503.json` is `valid=true` for static gates with replay-baseline warning.
- `/tmp/truffles_real_world_salon_pack_20260503/surface_realism_audit_20260503.json` records the 2026-05-03 phone/time realism repair: compact/digit-spaced phone numbers and natural time expressions without colon/dot-heavy notation.
- `/tmp/truffles_real_world_salon_pack_20260503/exploration_smoke_rendered_v0_20260503/summary.json` is a 3-dialog diagnostic tranche only: `strict_pass_rate=0.6429`, `expected_reply_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`.
- `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_a_20260503.md` records the current failure-family map before repair.
- `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/summary.json` is a 10-dialog diagnostic tranche only: `strict_pass_rate=0.6136`, `hard_fail_rate=0.0682`, `expected_reply_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`.
- `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/manual_audit.json` is `status=done`, `human_semantic_valid=false`.
- `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_b_20260503.md` is the expanded pre-repair failure-family map.
- `/tmp/truffles_real_world_salon_pack_20260504/p0_handoff_repair_20260504a/p0_handoff_repair_summary_20260504a.json` is `valid=true` focused mechanism proof for `FAM-B1` and `FAM-B3` only; it is not Pack v0 Acceptance or Beauty Salon v1 product proof.
- `/tmp/truffles_real_world_salon_pack_20260504/fam_b2_lifecycle_repair_20260504a/fam_b2_lifecycle_repair_summary_20260504a.json` is `valid=true` focused lifecycle/oracle proof for `FAM-B2` only: strict pass/state transition pass are 1.0, manager actions are 4/4 OK, and expected-state mismatch count is 0.
- `/tmp/truffles_real_world_salon_pack_20260504/release_topology_truth_p0_handoff_20260504a.json` is `valid=true` for runtime image `truffles-local:real-world-p0-handoff-20260504a`.
- `/tmp/truffles_real_world_salon_pack_20260504/pack_v0_exploration_after_p0_20260504a/INVALID_RUN_DO_NOT_USE.md` marks the aborted 48-dialog / 511-turn full-pack attempt as invalid evidence.
- `/tmp/truffles_real_world_salon_pack_20260504/exploration_tranche_b_after_p0_20260504a/summary.json` is the after-P0 10-dialog diagnostic rerun: `strict_pass_rate=0.9091`, `hard_fail_rate=0.0`, `expected_reply_rate=0.9474`, `info_answer_rate=0.5`, `handoff_correct_rate=0.8889`, `decision_meta_coverage=1.0`, and `decision_trace_coverage=1.0`; it remains `semantic_valid=false` and `infra_valid=false`.
- `/tmp/truffles_real_world_salon_pack_20260504/failure_family_map_pack_v0_tranche_b_after_p0_20260504a.md` is the after-P0 failure-family map.
- `/tmp/truffles_real_world_salon_pack_20260504/fam_c_handoff_oracle_repair_20260504a/fam_c_handoff_oracle_repair_summary_20260504a.json` is `oracle_valid=true` focused proof for `FAM-C1` only: generic complaint/medical/human handoff follow-ups now remain pending handoff context; it is not Acceptance.
- `/tmp/truffles_real_world_salon_pack_20260505/fam_c0_evidence_reliability_20260505a/fam_c0_evidence_reliability_summary_20260505a.json` is `FOCUSED_EVIDENCE_RELIABILITY_PROOF_NOT_ACCEPTANCE` for `FAM-C0` only: 2 handoff dialogs / 6 turns, `infra_valid=true`, `strict_pass_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, zero webhook/infra/decision-meta/decision-trace errors, and manager actions 4/4 OK.
- `/tmp/truffles_real_world_salon_pack_20260505/pack_v0_tranche_b_after_fam_c0_diagnostic_summary_20260505b.json` is `DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE`: complete 10 dialogs / 44 turns, `infra_valid=true`, `run_integrity_valid=true`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0`, `expected_reply_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, zero webhook/infra/decision-meta/decision-trace errors, and manager actions 14/14 OK; it remains `semantic_valid=false`.
- `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/run/summary.json` is `FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE`: 2 dialogs / 10 turns, `semantic_valid=true`, `infra_valid=true`, `run_integrity_valid=true`, `strict_pass_rate=1.0`, `hard_fail_rate=0.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `semantic_override_rate=0.0`, and `stale_state_leak_rate=0.0`; manual audit is `status=done`, `human_semantic_valid=true`. Scope: unsupported-service availability, fact-interruption continuity, planner-boundary state containment, and range-time rendering only.
- `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/summary.json` is the first after-FAM-C2/FAM-C3 `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE` artifact: 10 dialogs / 44 turns reached `strict_pass_rate=1.0`, but manual audit remained `human_semantic_valid=false`; it is historical diagnostic evidence superseded for current acceptance-governance by `DL-2026-05-07-013`.
- `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507l/run/summary.json` is invalid diagnostic evidence and must not be reused because `--jid-mode unique` still reused allowlist JIDs before replay isolation was repaired.
- `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/summary.json` is the current Pack v0 quality-governance diagnostic: 10 dialogs / 44 turns, `infra_valid=true`, `run_integrity_valid=true`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `info_answer_rate=1.0`, `handoff_correct_rate=1.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `semantic_override_rate=0.0`, `stale_state_leak_rate=0.0`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0227`, and `failure_family_count=3`; manual audit is `status=done`, `human_semantic_valid=false`. Scope: diagnostic only; not Pack v0 Acceptance.

Current failure families:

- `FAM-A1` (`P0`, `REPAIR`): cancel/reschedule/admin-confirm requests are under-escalated by policy-core/planner into fact lookup instead of booking-manage handoff/admin confirmation.
- `FAM-A2` (`P0`, `REPAIR`): vague/daypart reschedule time can fail the policy schema and degrade, so raw owner is not green.
- `FAM-A3` (`P1`, `REPAIR`): calendar-tool contract/oracle needs review before runtime repair.
- `FAM-A4` (`P0`, `REPAIR`): quality-runner transport evidence separation was repaired for dev Exploration vs strict Acceptance.
- `FAM-B1` (`P0`, `FOCUSED_REPAIR_PROOF`): booking-manage cancel/reschedule/admin-confirm now routes to admin-confirmation `HANDOFF` in the 2026-05-04 focused proof; still requires Pack v0 rerun before Acceptance.
- `FAM-B2` (`P0`, `FOCUSED_REPAIR_PROOF`): handoff pending-state lifecycle, manager simulation, and scenario oracle are aligned in the 2026-05-04 focused proof; still requires Pack v0 rerun before Acceptance.
- `FAM-B3` (`P0`, `FOCUSED_REPAIR_PROOF`): complaint/medical/human handoff contact follow-up now stays `HANDOFF` / `handoff_context_update` in the 2026-05-04 focused proof; still requires Pack v0 rerun before Acceptance.
- `FAM-B4` (`P1`, `REPAIR`): calendar-tool contract miss on identity/context collection needs oracle-vs-executor classification.
- `FAM-B5` (`P1`, `REPAIR`): price/duration interruption response shape needs product copy decision.
- `FAM-B6` (`P1`, `REPAIR`): unsupported service clarification is weak and can enter booking collect loop without supported service selection.
- `FAM-C0` (`P0`, `BROAD_DIAGNOSTIC_STABLE_INFRA`): proof runtime reliability is repaired for current diagnostics; after-FAM-C0 Tranche B has `infra_valid=true`, but this is not Acceptance.
- `FAM-C1` (`P0`, `FOCUSED_ORACLE_PROOF`): generic complaint/medical/refund/payment/safety/human handoff follow-ups are sanitized as pending `HANDOFF`; still requires broader tranche after evidence reliability is stable.
- `FAM-C2` (`P1`, `FOCUSED_TECHNICAL_PROOF_NOT_ACCEPTANCE`): unsupported-service policy/oracle is repaired in the focused 2026-05-07 proof; unavailable service remains grounded `FACT` until a supported service is selected, not booking `COLLECT` or hidden `HANDOFF`.
- `FAM-C3` (`P1`, `FOCUSED_TECHNICAL_PROOF_NOT_ACCEPTANCE`): fact-interruption continuity is repaired in the focused 2026-05-07 proof; price/duration answers preserve booking continuity, range/daypart time asks for exact time, and inactive/degraded state does not leak as semantic booking memory.
- `FAM-C4` (`P1`, `DIAGNOSTIC_RUN_COMPLETED_NOT_ACCEPTANCE`): broader 10-dialog / 44-turn Pack v0 diagnostic completed after focused repairs, but the initial green-looking result was diagnostic only and later superseded by quality-governance repair evidence.
- `FAM-D0` (`P0`, `QUALITY_GOVERNANCE_REPAIR_PROOF_NOT_ACCEPTANCE`): quality runner replay isolation and false metric blockers are repaired for current diagnostics; `--jid-mode unique` now uses run-scoped JIDs, handoff/human wording no longer creates false info-answer obligations, and `info_answer_rate=1.0` in 20260507m.
- `FAM-D1` (`P1`, `ORACLE_REPAIR`): Pack v0 dialog `rwsp-v0-008` turn 1 expects time after a multi-service input, but correct Beauty Salon behavior is to collect service choice before time.
- `FAM-D2` (`P0`, `REPAIR`): Pack v0 dialog `rwsp-v0-008` turn 7 exposes policy-core owner/planner contract mismatch; booking commit confirmation emitted `action=fact` with `tool_action_hint=calendar.book_slot`, causing `policy_core_invalid_schema` and degraded runtime.

Next runtime acceptance work:

1. Repair the `FAM-D1` scenario/oracle expectation so multi-service customer input requires service-choice collection before time collection.
2. Repair `FAM-D2` at owner/planner contract level so booking commit confirmation cannot degrade through `policy_core_invalid_schema`.
3. Rerun focused proof for `FAM-D1/FAM-D2`, then broader Pack v0 diagnostic, before strict Acceptance.
4. Move to strict Acceptance only after diagnostic semantic validity is clean and provider/Console proof scope is selected.
5. Triage broad stale unit-test failures by capability/layer before any additional repair.

## 11. Source-Of-Truth Mapping

| Area | Source |
|---|---|
| Product/system front door | `docs/PRODUCT_SYSTEM_CANON.md` |
| Beauty Salon v1 capability map | `docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md` |
| Product promises and go-live rows | `STRATEGY/PRODUCT.md` |
| Owner requirements and no-go rules | `STRATEGY/REQUIREMENTS.md` |
| Runtime behavior | `SPECS/CONSULTANT.md`, `SPECS/ARCHITECTURE.md` |
| Console behavior | `docs/CONSOLE_PLANE_ACCEPTANCE_MAP.md`, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `docs/CONSOLE_AUDIT/*` |
| Infra/observability | `SPECS/INFRASTRUCTURE.md`, `docs/OBSERVABILITY_SURFACES.yaml`, `docs/RELEASE_TOPOLOGY_TRUTH.yaml` |
| Data readiness | `docs/GO_LIVE_DATA_READINESS.yaml` |
| Provider readiness | `docs/PROVIDER_INTEGRATION_READINESS.yaml` |
| Evidence/history | `STATE.md`, live probes, artifact bundles |

## 12. Next Valid Execution Blocks

After this map, valid next blocks are:

1. `No-Repeat / Process Governance Maintenance`
2. `External Provider Canary Proof` only after the provider is commercially available
3. `Final Beauty Salon v1 Go-Live Review` only after fresh combined proof and provider status are resolved

Selection rule:

- If booking proof is questioned, use section `9.21` of `docs/PRODUCT_SYSTEM_CANON.md` and rerun realistic booking only after fresh dated regression evidence.
- If docs/process would cause repeated proven work, choose no-repeat governance maintenance first.
- If the owner wants a third-party-reviewable structure, use the closed handoff map in `docs/PRODUCT_SYSTEM_CANON.md` section `9.16` and `TECH.md`.
- If the live customer channel is the immediate blocker and provider access is available, choose provider canary.
- If the live customer channel is commercially blocked, record visible provider readiness evidence and do not confuse it with internal booking readiness.
- If operational calendar/catalog data is branch-inconsistent, choose data ownership repair before booking/runtime acceptance.
- If a turn depends on customer data, require the Single-Turn Decision/Data Ownership Audit from `docs/PRODUCT_SYSTEM_CANON.md` section `9.24` before changing runtime behavior.
- If proven runtime/Console/observability behavior regresses, create a fresh dated regression artifact before reopening that block.

## 13. Lead-24/7 Acceptance Gate — 2026-05-12

This section defines the acceptance gate for the primary product pain locked in `docs/PRODUCT_SYSTEM_CANON.md` section 9.29 and in `docs/DECISION_LEDGER.yaml` entry `DL-2026-05-12-024`. It applies to `Beauty Salon v1` as the first vertical proving lead-24/7.

The platform passes the Lead-24/7 Acceptance Gate only when all five sub-gates pass simultaneously on the active vertical (Mira salon on `Beauty Salon v1` Pack):

1. **Latency.** p95 reply time on new incoming WhatsApp messages meets the threshold defined after the first realistic corpus batch. Defended publicly as "not worse than the live admin".
2. **Capture.** Percentage of incoming leads driven to a confirmed appointment OR an explicit qualified refusal / handoff meets the threshold defined after the first realistic corpus batch. Measured against the current manual owner workflow.
3. **Architecture.** Zero violations of `single_semantic_owner`, `tool_inventory`, `decision_ledger`, `pack_is_single_source_of_truth`, `layer_isolation` guards in main.
4. **Owner self-service.** Owner updates price, service, specialist, working-hours through the Pack. Mechanism (Console GUI vs YAML) pending audit of `truffles-api/app/pack_v1/*` and `console-web/*`.
5. **Corpus.** Every intent enabled in autonomous-mode for this vertical has a gold set of dialogs with `owner_approved=true` showing 100% match between production reactions and expected outcomes.

Until this gate passes, autonomous-mode is not allowed in production for any intent on this vertical. Assist-mode and shadow-mode are permitted as ramp-up stages.

Scope clarifications:

- The channel for this gate is WhatsApp. The commercial WhatsApp provider blocker does not block evaluation against this gate; a mock provider with identical contracts is used during development. Production cutover to the live WhatsApp provider is a separate readiness step (`docs/PROVIDER_INTEGRATION_READINESS.yaml`).
- Both new leads and repeat contacts from existing clients are in scope of this gate.
- Handoff to a human is a passing outcome of a dialog, not a failure mode. The capture gate counts "explicit qualified refusal or handoff" as success.
- Latency and capture thresholds are deliberately left as `TBD-after-first-batch`. They will be set in a follow-up ledger entry referencing the first realistic owner-approved corpus from `DL-2026-05-11-023`.

This gate supersedes any informal "good enough" definition used in prior phases of `Beauty Salon v1` for the lead-24/7 path. Other capability rows in this map (FACT, COLLECT, HANDOFF, Console acceptance matrix) remain valid; this gate adds the production-readiness condition layered on top of them.
