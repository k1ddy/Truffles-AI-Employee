# TECH — Технические данные

**Проверено: 2026-04-26**

---

## Сервер

| Параметр | Значение |
|----------|----------|
| IP | 5.188.241.234 |
| SSH порт | 222 |
| Пользователь | zhan |
| SSH команда | `ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234` |

---

## Перед SSH: проверка окружения

Если `pwd` = `/home/zhan/truffles-main` и public IP совпадает с IP выше — ты уже на проде, SSH не нужен.

Быстрая проверка:
```bash
hostname; whoami; pwd; curl -s https://ifconfig.me
```

---

## Docker контейнеры

| Имя | Образ | Назначение |
|-----|-------|------------|
| truffles-api | truffles-api_truffles-api | Python API (FastAPI) |
| truffles-outbox | truffles-api_truffles-api | Outbox worker (ACK-first delivery) |
| truffles-sentinel | truffles-api_truffles-api | Sentinel worker (health/self-heal) |
| truffles_postgres_1 | postgres:15-alpine | PostgreSQL |
| truffles_redis_1 | redis:7-alpine | Redis |
| truffles_qdrant_1 | qdrant/qdrant:latest | Vector DB |
| bge-m3 | text-embeddings-inference | Embeddings |
| truffles-traefik | traefik:v2.11 | Reverse proxy |

**Важно:** Инфраструктура разделена: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`). Прод релиз выполняется через `/home/zhan/truffles-main/scripts/restart_release.sh` (внутри вызывает `restart_api.sh` + `restart_workers.sh` + `restart_console_web.sh` и пишет artifact `release_topology_truth.json`). Канонический required cohort описан в `docs/RELEASE_TOPOLOGY_TRUTH.yaml`; shadow side services removed after dependency proof and must not be recreated without a fresh architecture decision. First go-live tenant data readiness is tracked separately in `docs/GO_LIVE_DATA_READINESS.yaml` and checked by `scripts/go_live_data_truth.py`; provider/webhook readiness is tracked in `docs/PROVIDER_INTEGRATION_READINESS.yaml` and checked by `scripts/provider_integration_truth.py`. Do not treat `/admin/health` fleet residuals or stale inbound traffic as hidden target readiness. В `/home/zhan/truffles-main/docker-compose.yml` — заглушка (не использовать). Ранее был кейс ошибки `KeyError: 'ContainerConfig'` на `up/build`.

### Active runtime snapshot — 2026-04-26

This snapshot records the current local/server reality used for architecture recovery. Re-run the commands before any live proof.

| Class | Containers / Surfaces | Meaning |
|---|---|---|
| `KEEP / REPAIR` | `truffles-api`, `truffles-console-web`, `truffles-outbox`, `truffles-sentinel`, `truffles-knowledge-activation`, `truffles_postgres_1`, `truffles_redis_1`, `truffles_qdrant_1`, `bge-m3`, `truffles-traefik`, `truffles-prometheus-1`, `truffles-grafana-1`, `truffles-tempo-1`, `truffles-alertmanager-1`, `truffles-console-keycloak` | Beauty Salon v1 kernel or required ops/auth infrastructure; release cohort drift was reconciled and must stay guarded |
| `REMOVED` | `truffles-provider-gateway`, `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, `truffles-outbox-service` | shadow side-service residue removed after dependency proof; reintroduction is guarded by `scripts/shadow_removal_dependency_truth.py` |
| `UNKNOWN` | `truffles-knowledge-activation-service`, `truffles-console-postgres`, `truffles-console-redis`, `truffles-local-postgres-a920` | needs dependency classification before removal or reliance |
| `LATER / UNRELATED` | `truffles_n8n_1`, `truffles_n8n-worker_1`, `truffles_pgadmin_1`, `truffles-website`, `gemini_autonomous_proxy` | not part of the first Beauty Salon v1 working kernel unless separately proven |

Current active build/runtime facts:

- active worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`;
- active HEAD: `9db031ee967999545f8a9673e7e57cf4d7202e73`;
- `/admin/version.git_commit`: `9db031ee967999545f8a9673e7e57cf4d7202e73`;
- `/admin/version.build_time`: `2026-04-26T15:56:37Z`;
- required release cohort truth: `python3 scripts/release_topology_truth.py --repo-root . --base-url http://localhost:8000 --expected-commit $(git rev-parse HEAD) --output <artifact>` returns `valid=true` after 2026-04-26 data-catalog repair restart on `truffles-local:data-catalog-repair-20260426a`;
- observability truth: `python3 scripts/observability_truth.py --repo-root . --output <artifact>` returns `valid=true`;
- target data truth: `python3 scripts/go_live_data_truth.py --repo-root . --env-file /home/zhan/truffles-main/truffles-api/.env --output <artifact>` now returns `valid=true` for `demo_salon/main` after operational service integrity repair;
- provider integration truth: `python3 scripts/provider_integration_truth.py --repo-root . --base-url http://localhost:8000 --env-file /home/zhan/truffles-main/truffles-api/.env --output <artifact>` returns `valid=false` because Chatflow/WhatsApp is commercially unavailable.

Active source-of-truth database:

- API `DATABASE_URL` points to `truffles_postgres_1` / database `chatbot`;
- key live tables include `clients`, `branches`, `conversations`, `messages`, `outbox_messages`, `appointments`, `appointment_services`, `appointment_audit`, and `knowledge_versions`;
- current live counts observed on 2026-04-26 recovery probes: `appointments=418`, `bookings=17`, `clients=7`, `branches=17`, `services=22`, `specialist_services=36`, `specialists=10`, `messages=152425`, `outbox_messages=22853`, `knowledge_versions=15`;

Active data integrity findings for `demo_salon/main` after 2026-04-26 repair:

- target branch `b7f75692-951e-421a-aae6-f5db97394799` has `15` active rows in `services`;
- `specialist_services` has `15` target-branch links for the 5 active target specialists;
- cross-client specialist-service links: `0`;
- cross-branch specialist-service links: `0`;
- service rows for `demo_salon` pointing to another client's branch: `0`;
- active knowledge pack still contains useful salon service catalog data with 14 service entries, plus prices/durations/promotions/policies;
- `go_live_data_truth.valid=true` now proves this catalog ownership seam for `demo_salon/main`.

- `truffles-console-postgres` is a separate Console/Auth-era database and is not the current appointment source of truth for Console API;
- internal Calendar acceptance must prove state in core `appointments`, not in Google Calendar and not in the separate Console DB.

Current Beauty Salon v1 target kernel path:

`Traefik -> Console Web -> FastAPI /console/v1 -> truffles_postgres_1/chatbot -> appointments/outbox/knowledge -> workers -> Prometheus/Grafana/Tempo/Alertmanager`

Current non-closed surfaces on that path:

1. external provider/channel proof is blocked commercially;
2. proven Console/runtime/observability rows need narrow regression checks when touched.

External WhatsApp/Chatflow channel is not part of the internal booking proof while access is commercially unavailable.

### Active architecture inventory baseline — 2026-05-01

This is a process/runtime inventory baseline. It does not claim product go-live closure.

Live facts remeasured on 2026-05-01:

- `/admin/version.git_commit`: `9db031ee967999545f8a9673e7e57cf4d7202e73`;
- `/admin/version.build_time`: `2026-04-30T17:23:07Z`;
- active runtime image: `truffles-local:booking-matrix-20260430i`;
- release topology truth: valid, artifact `/tmp/truffles_process_governance_20260501/release_topology_truth_inventory_20260501.json`;
- observability surface truth: valid, artifact `/tmp/truffles_process_governance_20260501/observability_truth_inventory_20260501.json`;
- active container inventory: `/tmp/truffles_process_governance_20260501/docker_ps_inventory_20260501.tsv`;
- system layer inventory: `/tmp/truffles_process_governance_20260501/system_layer_inventory_20260501.md`;
- classification plan: `/tmp/truffles_process_governance_20260501/keep_repair_strangle_plan_20260501.md`.

Layer-level classification:

| Layer | Classification | Direction |
|---|---|---|
| Ingress | `REPAIR / STRANGLE` | keep FastAPI boundary, drain legacy webhook mesh |
| Policy Core | `REPAIR` | keep only policy-core as semantic owner |
| Planner | `REPAIR` | project owner output only |
| Boundary | `REPAIR` | validate/reject/explicit degrade only |
| State | `REPAIR / STRANGLE` | canonical state plus derived compatibility projections |
| Executor/Tools | `KEEP / REPAIR` | execute accepted contracts |
| Booking/Calendar | `KEEP / REPAIR` | `appointments` is booking SoT |
| Handoff/Inbox | `KEEP / REPAIR` | visible human lifecycle |
| Console | `KEEP / REPAIR` | main GUI/control plane |
| Knowledge/Data | `KEEP / REPAIR / STRANGLE` | data/packs/capabilities, no domain branching in core |
| Observability/Ops | `KEEP / REPAIR` | required product surface; surface truth and e2e correlated proof are internally proven |
| Provider | `KEEP / LATER / BLOCKED` | delivery/status only; Chatflow access blocker is non-code |
| Shadow services | `REMOVED` | side-service residue removed after dependency proof; canonical API/workers remain |

### Architecture handoff closure — 2026-05-02

Status: `ARCHITECTURE_HANDOFF_CLOSED`.

Use this as the technical review starting point before reading historical inventories:

| Review question | Current answer |
|---|---|
| What is the product kernel? | Beauty Salon v1 managed consultant: facts, booking intake/commit, handoff, Console/Ops readiness |
| What is the active customer/runtime boundary? | `truffles-api` FastAPI routes and canonical workers; policy-core is the semantic owner |
| What is the management GUI? | `truffles-console-web` through `/console/v1`; Console is the main GUI for Platform Admin, Support, Owner, Admin, Manager |
| What is booking source of truth? | active API Postgres `truffles_postgres_1/chatbot.appointments`; not Google Calendar and not `bookings` |
| What owns facts/capabilities? | published knowledge/client pack, DB operational catalog, capabilities contracts; future niches extend through packs/capabilities/tools |
| What is blocked? | external Chatflow/WhatsApp provider canary, for commercial access reasons |
| What is shadow? | Side-service residue for Provider Gateway, Knowledge Gateway, Inbox Service, Decision Core, and Outbox Service was removed after dependency proof; canonical routes/workers remain |
| What is next technical cleanup? | provider/channel proof after Chatflow/WhatsApp commercial access is restored; otherwise final go-live review stays blocked by provider status |

Code ownership map for the active spine:

| Layer | Primary surfaces | Proof/guard |
|---|---|---|
| Ingress/provider adapters | `truffles-api/app/main.py`, `/webhook/*`, `/provider/*` | `scripts/provider_integration_truth.py`, provider blocker visibility |
| Policy owner/runtime | `truffles-api/app/core/consultant_runtime.py`, `turn_planner.py`, `turn_executor.py`, `dialog_state_service.py` | `scripts/single_semantic_owner_guard.py`, `scripts/semantic_preflight.py`, booking matrix artifacts |
| Booking/calendar | `truffles-api/app/services/appointment_service.py`, `truffles-api/app/routers/calendar.py`, `truffles-api/app/routers/console.py` | Console lifecycle proof, booking matrix, go-live data truth |
| Console/RBAC | `console-web/`, `truffles-api/app/services/console_auth.py`, `/console/v1/*` | Console lifecycle artifact, RBAC tests |
| Data readiness | `docs/GO_LIVE_DATA_READINESS.yaml`, `scripts/go_live_data_truth.py` | target `demo_salon/main` data truth |
| Release/observability | `docs/RELEASE_TOPOLOGY_TRUTH.yaml`, `docs/OBSERVABILITY_SURFACES.yaml`, truth scripts | release topology, observability truth, e2e turn truth |
| Removed shadow side-service residue | deleted side-app/restart surfaces; dependency/reintroduction guard remains | `scripts/shadow_removal_dependency_truth.py` |

### Shadow removal dependency proof — 2026-05-02

Status: `SHADOW_REMOVAL_DEPENDENCY_PROVEN`.

Repeatable command:

`python3 scripts/shadow_removal_dependency_truth.py --repo-root . --include-runtime --extra-file /home/zhan/infrastructure/docker-compose.truffles.yml --output /tmp/truffles_process_governance_20260502/shadow_removal_dependency_truth_live_20260502.json`

Live result:

- `valid=true`;
- decision `removal_ready_for_later_block`;
- blocking static production references: `0`;
- live dependency hits from running containers: `0`;
- proof-time runtime state showed `truffles-provider-gateway`, `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, and `truffles-outbox-service` all existed but were stopped with Docker status `exited`; the subsequent removal block is closed below.

Next safe technical action:

- the separate `Shadow side-service removal block` is closed below;
- preserve canonical `truffles-api`, `truffles-outbox`, Console, provider blocker visibility, and internal booking/calendar paths.

### Shadow side-service removal — 2026-05-02

Status: `SHADOW_SIDE_SERVICES_REMOVED`.

Removed side-service residue:

- side app entrypoints for Provider Gateway, Knowledge Gateway, Inbox Service, Decision Core, and Outbox Service;
- side-service restart scripts for the five removed side services;
- side-service-only routers for Inbox Service, Decision Core, and Outbox Service;
- shadow authority guard and tests that only existed to keep removed side services non-authoritative;
- release topology and observability shadow side-service entries.

Preserved canonical surfaces:

- `truffles-api` remains the runtime API;
- `truffles-outbox`, `truffles-knowledge-activation`, and `truffles-sentinel` remain canonical workers;
- Console remains the management GUI;
- canonical `/provider/*` and `/knowledge/snapshot` routes on `truffles-api` remain available according to their existing enable/config contracts;
- Chatflow/WhatsApp remains `BLOCKED_NON_CODE` and still does not block internal Console Calendar booking.

Closure evidence:

- `/tmp/truffles_process_governance_20260502/shadow_removal_dependency_truth_after_removal_20260502.json` reports `valid=true`, `blocking_references=0`, and all five removed containers `exists=false`;
- `/tmp/truffles_process_governance_20260502/release_topology_truth_after_shadow_removal_20260502.json` reports `valid=true` and `shadow_services={}`;
- `/tmp/truffles_process_governance_20260502/observability_truth_after_shadow_removal_20260502.json` reports `valid=true` with no shadow observability dependency;
- `/tmp/truffles_process_governance_20260502/shadow_side_service_removal_closure_20260502.md` is the dated closure record.

### Observability e2e turn proof — 2026-05-01

Repeatable command:

`python3 scripts/observability_e2e_turn_truth.py --repo-root . --base-url http://localhost:8000 --env-file /home/zhan/truffles-main/truffles-api/.env --output /tmp/truffles_process_governance_20260501/observability_e2e_turn_truth_20260501_final.json`

Live result:

- `valid=true`;
- `message_id=obs-e2e-20260501T041742Z-1af921aa37`;
- `conversation_id=6b860169-d180-4651-9367-9fb4d63ffb64`;
- `outbox_id=e59b7e68-ea4e-4421-8798-d071f922e299`;
- `trace_id=19f1071d0ecb737890671329bec504dd`;
- `outcome=FACT`, `action=fact`, `source=llm_policy_core`;
- correlated DB state: `messages.metadata.decision_meta`, `runtime_trace_contract`, and `outbox_messages.meta.timing/correlation`;
- correlated telemetry: `truffles-outbox` logs, Tempo `outbox.process` span, `/metrics` webhook counter, and `worker_heartbeat_status{worker="truffles-outbox"} 1.0`;
- Console/Ops: `/console/v1/health` returned `ok`;
- Provider: `provider_integration_truth.valid=false` only for `CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE`; internal booking/turn proof remains not blocked.

### Verified product work map — 2026-05-01

This is the durable no-repeat map for product-block selection.

Registered guard:

`python3 scripts/product_work_map_guard.py --repo-root .`

Purpose:

- verifies `docs/PRODUCT_SYSTEM_CANON.md` contains the 2026-05-01 verified work map;
- prevents stale docs from reopening Console Lifecycle or Observability E2E as next product blocks after their dated proofs;
- requires the 2026-05-03 16-row booking result to remain classified as `SCRIPTED_TECHNICAL_PROOF`, not `REAL_WORLD_PRODUCT_PROOF`, after `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/realistic_booking_matrix_product_summary_20260503g_fresh.json` and Console visibility proof;
- prevents stale architecture docs from reverting handoff closure back to in-progress;
- requires Provider/Channel Readiness to remain `BLOCKED_NON_CODE` until commercial access is restored.

### Decision & Action Ledger — 2026-05-03

Registered guard:

`python3 scripts/decision_ledger_guard.py --repo-root .`

Purpose:

- keeps a concise decision/action history in `docs/DECISION_LEDGER.yaml`;
- requires ledger entries for mechanism changes, architecture decisions, blocker reclassification, tool/script creation or change, product status changes, and proof downgrade/invalidation;
- blocks the 2026-05-03 booking matrix from being re-promoted from `SCRIPTED_TECHNICAL_PROOF` to `REAL_WORLD_PRODUCT_PROOF` without a Real-World Salon Acceptance Pack;
- verifies the ledger file, schema fields, current binding entries through `DL-2026-05-07-011`, and impacted durable docs;
- preserves the Internal Pilot Proof process: owner-reviewed synthetic messy corpus, Exploration lane, invalid-run stop conditions, behavioral failures do not stop run execution, failure-family map before repair.
- preserves the Single-Turn Decision/Data Ownership Audit: every meaningful turn must show `decision path + data ownership path`, and runtime repairs depending on customer data must define the Customer Data Contract across Packs / Knowledge, Capabilities, Operational DB, RAG / Qdrant, and Policy-core context.

Owner: Architect/Brain.
Inputs: `docs/DECISION_LEDGER.yaml`, product canon, Beauty Salon capability map, session prompt, `TECH.md`, `STRUCTURE.md`.
Outputs: pass/fail with missing ledger/schema/status terms.
Run when: changing product status, proof status, architecture decisions, blocker status, scripts/tools/guards, or decision-process docs.
Proof value: prevents silent proof inflation and makes zero-memory agent handoff auditable.
Limit: does not prove runtime behavior; it only guards the decision/proof classification record.

### Real-World Salon Acceptance Pack tooling — 2026-05-03

Use existing registered quality tools before creating any new runner.

- Generate owner-review candidates with `scripts/booking_dialog_scenarios.py`.
- Run non-blocking Exploration with `ops/diagnose.py llm-quality` or `ops/diagnose.py llm-quality-matrix` without fail-on-threshold behavior; behavioral failures do not stop run execution.
- Stop Exploration only on invalid-run evidence problems: wrong runtime/tenant, broken scenario contract, missing owner output, missing trace/meta, or harness contamination.
- Aggregate families with `ops/diagnose.py llm-quality-trends` and static/product gates with `ops/diagnose.py llm-quality-gates`.
- Use `scripts/focused_family_proof.py` only after a capability/layer-classified mechanism repair.
- Summarize artifacts with `scripts/quality_artifact_report.py`.

Owner-reviewed synthetic messy corpus is an Internal Pilot Proof proxy, not raw production transcript proof. Strict Acceptance must still require `raw owner = green`, `final runtime = green`, `rescue = no`, and exact DB/Console/audit/trace proof.

Pack v0 owner-reviewed internal pilot artifacts:

- `/tmp/truffles_real_world_salon_pack_20260503/static_scenario_contract_20260503.json`
- `/tmp/truffles_real_world_salon_pack_20260503/llm_quality_gates_exploration_candidates_20260503.json`
- `/tmp/truffles_real_world_salon_pack_20260503/surface_realism_audit_20260503.json`
- `/tmp/truffles_real_world_salon_pack_20260503/real_world_salon_acceptance_pack_v0_20260503.json`
- `/tmp/truffles_real_world_salon_pack_20260503/real_world_salon_acceptance_pack_v0_20260503.md`
- `/tmp/truffles_real_world_salon_pack_20260503/static_scenario_contract_pack_v0_20260503.json`
- `/tmp/truffles_real_world_salon_pack_20260503/llm_quality_gates_pack_v0_20260503.json`

Runtime `llm-quality` Exploration starts only after owner approval of the sample. Do not use interrupted or invalid `llm-quality` attempts as evidence.

### Customer data ownership / single-turn audit — 2026-05-05

Decision source: `docs/DECISION_LEDGER.yaml` entry `DL-2026-05-05-010` and `docs/PRODUCT_SYSTEM_CANON.md` section `9.24`.

Operating rule: business behavior cannot be judged from the control-flow path alone. For meaningful LLM/runtime diagnostics, capture both:

- decision path: input, policy-core owner output, planner/binding, boundary verdict, state write/load, executor/tool action, final response, trace/meta, rescue/degrade flag;
- data ownership path: Packs / Knowledge active version/refs, Capabilities source/verdict, Operational DB rows or absence, RAG / Qdrant projection status if used, and Policy-core context cards/allowed payload.

Customer Data Contract ownership:

- Packs / Knowledge own customer-facing facts and salon rules.
- Capabilities own allowed channels/providers/features/tools/fact scopes/handoff policy.
- Operational DB owns executable services, specialists, specialist-service links, and `appointments`.
- RAG / Qdrant is retrieval projection only, not semantic owner and not core booking truth.
- Policy-core context is a governed projection into the LLM owner, not a new truth source.

Current target snapshot: `/tmp/truffles_data_ownership_snapshot_20260505.json` (`FACTUAL_SNAPSHOT_NOT_PRODUCT_PROOF`) shows `demo_salon/main` active pack version `033ba3b8-a19a-4887-8587-aa761243f29c`, `client_capabilities` source, 14 pack service catalog rows, 15 active DB services, 5 active specialists, and 15 active specialist-service links.

Transport evidence policy for `ops/diagnose.py llm-quality`:

- `--transport-evidence-policy rendered` is allowed only for `--quality-lane dev` Exploration when the goal is semantic diagnosis against the internal rendered assistant response while provider delivery is commercially blocked.
- `--transport-evidence-policy delivery` is mandatory for Acceptance and product proof; `llm-quality-gates` rejects acceptance-lane artifacts that use rendered evidence.
- Rendered evidence may come from inline response or the canonical assistant row in `messages`; inbound `outbox_messages.payload_json` text must not count as assistant response proof.

Current corrected diagnostic tranche:

- invalid/do-not-use attempts: `/tmp/truffles_real_world_salon_pack_20260503/exploration_run_v0_20260503/INVALID_RUN_DO_NOT_USE.md` and `/tmp/truffles_real_world_salon_pack_20260503/exploration_smoke_outbox_v0_20260503/INVALID_RUN_DO_NOT_USE.md`;
- corrected dev Exploration: `/tmp/truffles_real_world_salon_pack_20260503/exploration_smoke_rendered_v0_20260503/summary.json`;
- failure-family map: `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_a_20260503.md`;
- status: `DIAGNOSTIC_TRANCHE_NOT_PRODUCT_PROOF` with 3 dialogs / 14 turns; manual audit and full Pack v0 acceptance are still pending.

Current expanded diagnostic tranche:

- run: `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g`;
- summary: `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/summary.json`;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260503/exploration_tranche_b_rendered_v0_20260503g/manual_audit.json` (`status=done`, `human_semantic_valid=false`);
- failure map: `/tmp/truffles_real_world_salon_pack_20260503/failure_family_map_pack_v0_tranche_b_20260503.md`;
- metrics: 10 dialogs / 44 turns, `strict_pass_rate=0.6136`, `hard_fail_rate=0.0682`, `expected_reply_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`;
- status: `DIAGNOSTIC_TRANCHE_NOT_PRODUCT_PROOF`; dev lane, rendered evidence, `--allow-judge-off`, run-economy `warn`, not baseline/Acceptance.

Tranche B repair order:

1. `FAM-B1`: booking-manage cancel/reschedule/admin-confirm ownership must not collapse to `FACT/calendar.get_booking`.
2. `FAM-B3`: handoff contact/context follow-up must update handoff, not start booking collect.
3. `FAM-B2`: handoff lifecycle state, manager simulation, and scenario oracle must be aligned before interpreting pending-state rows.
4. `FAM-B4/B5/B6`: calendar-tool oracle ambiguity, fact-interruption copy contract, and unsupported-service policy are P1 follow-ups after P0s.

Focused P0 repair runtime proof — 2026-05-04:

- runtime image: `truffles-local:real-world-p0-handoff-20260504a`;
- `/admin/version.build_time`: `2026-05-04T15:49:56Z`;
- release topology truth: `/tmp/truffles_real_world_salon_pack_20260504/release_topology_truth_p0_handoff_20260504a.json` is `valid=true`;
- focused family summary: `/tmp/truffles_real_world_salon_pack_20260504/p0_handoff_repair_20260504a/p0_handoff_repair_summary_20260504a.json` is `valid=true` for 5 exact-family dialogs;
- proof scope: `FAM-B1` customer cancel/reschedule/admin-confirmation routes to admin-confirmation `HANDOFF`; `FAM-B3` name/phone after complaint/medical/human handoff stays `HANDOFF` / `handoff_context_update`;
- proof limit: focused mechanism proof only; not Pack v0 Acceptance, provider delivery proof, or Beauty Salon v1 go-live readiness.

Focused FAM-B2 lifecycle/oracle proof — 2026-05-04:

- focused summary: `/tmp/truffles_real_world_salon_pack_20260504/fam_b2_lifecycle_repair_20260504a/fam_b2_lifecycle_repair_summary_20260504a.json` is `valid=true`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260504/fam_b2_lifecycle_repair_20260504a/run/summary.json` has turn-level `strict_pass_rate=1.0`, `state_transition_pass_rate=1.0`, manager actions `4/4` OK, and `expected_state_mismatch_count=0`;
- runtime sanity: `/tmp/truffles_real_world_salon_pack_20260504/release_topology_truth_fam_b2_20260504a.json`, `/tmp/truffles_real_world_salon_pack_20260504/go_live_data_truth_fam_b2_20260504a.json`, and `/tmp/truffles_real_world_salon_pack_20260504/observability_truth_fam_b2_20260504a.json` are `valid=true`; provider truth remains `valid=false` only for commercial Chatflow/WhatsApp blocker;
- code scope: `ops/diagnose.py` quality oracle/manager simulation and `truffles-api/app/services/llm_quality_contracts.py` scenario sanitation; no runtime semantic-owner move;
- proof limit: dev rendered evidence with `--skip-outbox`; not provider delivery, not strict Acceptance, not go-live.

Pack v0 after-P0 diagnostic rerun — 2026-05-04:

- invalid full-pack attempt: `/tmp/truffles_real_world_salon_pack_20260504/pack_v0_exploration_after_p0_20260504a/INVALID_RUN_DO_NOT_USE.md`; 48 dialogs / 511 turns was too slow as one blocking pass and must not be reused as evidence;
- rerun summary: `/tmp/truffles_real_world_salon_pack_20260504/exploration_tranche_b_after_p0_20260504a/summary.json`;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260504/exploration_tranche_b_after_p0_20260504a/manual_audit.json` (`status=done`, `human_semantic_valid=false`);
- failure map: `/tmp/truffles_real_world_salon_pack_20260504/failure_family_map_pack_v0_tranche_b_after_p0_20260504a.md`;
- metrics: 10 dialogs / 44 turns, `strict_pass_rate=0.9091`, `hard_fail_rate=0.0`, `expected_reply_rate=0.9474`, `info_answer_rate=0.5`, `handoff_correct_rate=0.8889`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`;
- status: `DIAGNOSTIC_AFTER_P0_NOT_ACCEPTANCE`; `semantic_valid=false`, `infra_valid=false`, dev lane rendered evidence, not baseline/Acceptance.

Focused FAM-C1 generic handoff oracle proof — 2026-05-04:

- focused summary: `/tmp/truffles_real_world_salon_pack_20260504/fam_c_handoff_oracle_repair_20260504a/fam_c_handoff_oracle_repair_summary_20260504a.json` is `oracle_valid=true`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260504/fam_c_handoff_oracle_repair_20260504a/run_handoff/summary.json` has 2 dialogs / 6 turns, `strict_pass_rate=1.0`, `state_transition_pass_rate=1.0`, failure-family count `0`, and manager actions `4/4` OK;
- code scope: `truffles-api/app/services/llm_quality_contracts.py` scenario sanitizer keeps complaint/medical/refund/payment/safety/human follow-ups in pending handoff context; this is proof tooling only, not runtime semantic ownership;
- proof limit: dev rendered/skip-outbox focused run; `infra_valid=false` remains because decision-meta timeouts persist on expected no-response pending turns.

Focused FAM-C0 evidence reliability proof — 2026-05-05:

- focused summary: `/tmp/truffles_real_world_salon_pack_20260505/fam_c0_evidence_reliability_20260505a/fam_c0_evidence_reliability_summary_20260505a.json` is `FOCUSED_EVIDENCE_RELIABILITY_PROOF_NOT_ACCEPTANCE`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260505/fam_c0_evidence_reliability_20260505a/run_handoff/summary.json` has 2 handoff dialogs / 6 turns, `infra_valid=true`, `strict_pass_rate=1.0`, `pass_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, and zero webhook/infra/decision-meta/decision-trace errors;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260505/fam_c0_evidence_reliability_20260505a/run_handoff/manual_audit.json` is `status=done`; product/oracle/evaluator/infra backlog families are zero, with only run-level `semantic_invalid` because the focused handoff-only dev run is not Acceptance;
- code scope: `ops/diagnose.py` proof-runtime classification, pending ACK scheduling, manager simulation advisory handling, and manual-audit backlog filtering; no runtime semantic-owner change;
- proof limit: dev rendered transport evidence with simulated manager and skipped provider delivery; not provider proof, not Pack v0 Acceptance, not go-live.

Pack v0 after-FAM-C0 diagnostic rerun — 2026-05-05:

- invalid partial run: `/tmp/truffles_real_world_salon_pack_20260505/exploration_tranche_b_after_fam_c0_20260505a/INVALID_RUN_DO_NOT_USE.md`; stopped after 4/44 turns and must not be reused as evidence;
- diagnostic summary: `/tmp/truffles_real_world_salon_pack_20260505/pack_v0_tranche_b_after_fam_c0_diagnostic_summary_20260505b.json` is `DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260505/exploration_tranche_b_after_fam_c0_fast_20260505b/summary.json` completed 10 dialogs / 44 turns with `run_integrity_valid=true`, `infra_valid=true`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0`, `expected_reply_rate=1.0`, `handoff_correct_rate=1.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, zero webhook/infra/decision-meta/decision-trace errors, and manager actions `14/14` OK;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260505/exploration_tranche_b_after_fam_c0_fast_20260505b/manual_audit.json` is `status=done`, `human_semantic_valid=false`; remaining root causes are `fam_c2_unsupported_service_contract_unresolved` and `fam_c3_fact_interruption_copy_contract_unresolved`;
- trends: `/tmp/truffles_real_world_salon_pack_20260505/pack_v0_after_fam_c0_trends_20260505b.json` compares after-P0 and after-FAM-C0 diagnostics and shows current infra families cleared;
- proof limit: dev rendered transport evidence with simulated manager; not provider delivery proof, not strict Acceptance, not go-live.

Focused FAM-C2/FAM-C3 repair proof — 2026-05-07:

- runtime image: `truffles-local:fam-c2-c3-unsupported-focus-20260507h`;
- `/admin/version.build_time`: `2026-05-07T00:25:00Z`;
- release topology truth: `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/release_topology_truth_20260507h.json` is `valid=true`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/run/summary.json` completed 2 dialogs / 10 turns with `semantic_valid=true`, `infra_valid=true`, `run_integrity_valid=true`, `strict_pass_rate=1.0`, `hard_fail_rate=0.0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `semantic_override_rate=0.0`, and `stale_state_leak_rate=0.0`;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/run/manual_audit.json` is `status=done`, `human_semantic_valid=true`;
- runtime sanity after canonical runtime-profile restart: `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/release_topology_truth_after_runtime_profile_20260507h.json`, `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/go_live_data_truth_after_runtime_profile_20260507h.json`, and `/tmp/truffles_real_world_salon_pack_20260507/fam_c2_c3_unsupported_focus_20260507h/observability_truth_after_runtime_profile_20260507h.json` are `valid=true`; provider truth remains `valid=false` only for commercial Chatflow/WhatsApp unavailability;
- code scope: policy-core owner contract checks for unsupported-service availability/continuation, planner-boundary state containment, inactive legacy booking load filtering, and executor range-time rendering;
- proof limit: `FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE`; dev rendered evidence, no provider delivery, no appointment creation, no Console Calendar visibility, not Pack v0 Acceptance.

Pack v0 after-FAM-C2/FAM-C3 broader diagnostic — 2026-05-07:

- runtime image: `truffles-local:booking-manage-continuity-20260507k`;
- `/admin/version.build_time`: `2026-05-07T14:10:31Z`;
- release topology truth: `/tmp/truffles_real_world_salon_pack_20260507/booking_manage_continuity_20260507k/release_topology_truth_20260507k.json` is `valid=true`;
- llm-quality run: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/summary.json` completed 10 dialogs / 44 turns with `run_integrity_valid=true`, `strict_pass_rate=1.0`, `pass_rate=1.0`, `hard_fail_rate=0.0`, `failure_family_count=0`, `blocking_reason_count=0`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `handoff_correct_rate=1.0`, `post_llm_semantic_rewrite_rate=0.0`, `keyword_override_rate=0.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `booking_commit_without_required_contact=0.0`, `semantic_override_rate=0.0`, and `stale_state_leak_rate=0.0`;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_booking_manage_continuity_20260507k/run/manual_audit.json` is `status=done`, `evidence_handoff_valid=true`, `human_semantic_valid=false`;
- code scope: handoff semantic axes preserved through owner/planner/runtime/dialog-state contracts, booking-manage handoff context update limited to existing handoff memory, unsupported-service booking continuation routed to governed FACT;
- proof limit: `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE`; `infra_valid=false` from one unclassified expected no-response payment/media handoff decision-meta timeout, `semantic_valid=false` from `info_answer_rate=0.5`, synthetic owner-proxy corpus, rendered transport, simulated manager, no provider delivery, no fresh appointment/Console Calendar proof.

Pack v0 quality-governance/replay-isolation repair — 2026-05-07:

- `ops/diagnose.py` quality-governance repair: handoff/human/complaint/refund/payment/safety/medical contexts do not infer false info-answer obligations, pending payment/media handoff no-response evidence is soft only with handoff context, and `--jid-mode unique` creates run-scoped unique JIDs even when allowlists exist;
- invalid diagnostic evidence: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507l/run/summary.json` must not be reused because it was produced before unique-JID replay isolation was repaired;
- current diagnostic evidence: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/summary.json` completed 10 dialogs / 44 turns with `infra_valid=true`, `run_integrity_valid=true`, `decision_meta_coverage=1.0`, `decision_trace_coverage=1.0`, `info_answer_rate=1.0`, `handoff_correct_rate=1.0`, `fact_without_evidence_rate=0.0`, `irrelevant_fact_rate=0.0`, `semantic_override_rate=0.0`, `stale_state_leak_rate=0.0`, `strict_pass_rate=0.9545`, `hard_fail_rate=0.0227`, and `failure_family_count=3`;
- manual audit: `/tmp/truffles_real_world_salon_pack_20260507/pack_v0_after_quality_governance_20260507m/run/manual_audit.json` is `status=done`, `human_semantic_valid=false`, with one product runtime family (`policy_core_invalid_schema`) and one scenario/oracle family (`multi-service service-choice`);
- proof limit: still `PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE`; no provider delivery, no fresh appointment/Console Calendar proof, no product-readiness claim.

Runtime restart note: direct API/worker restarts can inherit `.env` `OUTBOX_WORKER_MODE=off` and break the outbox worker heartbeat. Use `scripts/restart_release.sh` or pass the `release_runtime_profile.py` override (`OUTBOX_WORKER_MODE=local_debug`) before making observability claims.

Next repair order after 2026-05-07 Pack v0 diagnostic:

1. Do not claim product proof from any Pack v0 diagnostic run.
2. Repair the Pack v0 multi-service scenario/oracle expectation so service-choice collection precedes time collection.
3. Repair the policy-core booking commit action/tool schema mismatch that produced `policy_core_invalid_schema`.
4. Rerun focused proof for the remaining family, then broader Pack v0 diagnostic before strict Acceptance.
5. Broad stale unit-test failures classified by capability/layer before repair.

Post-ledger runtime sanity artifacts:

- `/tmp/truffles_real_world_salon_pack_20260503/release_topology_truth_post_ledger_20260503.json` is `valid=true` for active HEAD/runtime commit `9db031ee967999545f8a9673e7e57cf4d7202e73`.
- `/tmp/truffles_real_world_salon_pack_20260503/observability_truth_post_ledger_20260503.json` is `valid=true` after canonical runtime-profile restart; outbox heartbeat is healthy with `OUTBOX_WORKER_MODE=local_debug`.
- `/tmp/truffles_real_world_salon_pack_20260503/go_live_data_truth_post_ledger_20260503.json` is `valid=true` for `demo_salon/main` target data readiness.
- `/tmp/truffles_real_world_salon_pack_20260503/provider_integration_truth_post_ledger_20260503.json` is `valid=false` only for `CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE`; internal booking proof remains separate.

Scenario-surface realism rules for `scripts/booking_dialog_scenarios.py`:

- phone slots in `variant` mode should include compact/digit-spaced forms such as `87015705555`, `7015705555`, `8701 570 55 55`, not only `+7 (...)` formatting;
- time slots in `variant` mode should include customer-like forms such as `17 30`, `5 30 вечера`, `вечером в пять`, `после шести`, not colon/dot-heavy `17:45` / `17.45` notation;
- surface realism is still a corpus-quality aid, not semantic ownership; policy-core remains the only semantic owner.

Evidence bundle:

- `/tmp/truffles_process_governance_20260501/tp_verified_product_work_map_20260501.md`
- `/tmp/truffles_process_governance_20260501/verified_product_work_map_rca_20260501.md`
- `/tmp/truffles_process_governance_20260501/verified_product_work_map_20260501.md`
- `/tmp/truffles_process_governance_20260501/focused_web_search_work_map_governance_20260501.md`
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/realistic_booking_matrix_product_summary_20260503g_fresh.json`
- `/tmp/truffles_real_booking_matrix_20260503/live_full_after_g_fresh/console_calendar_visibility_product_summary_20260503g_fresh.json`

### Architecture handoff baseline — 2026-05-01

This is the original third-party-reviewable baseline for the proven Beauty Salon v1 spine. It is superseded by `Architecture handoff closure — 2026-05-02` after shadow authority drain and stopped-or-disabled observability proof.

Artifact:

- `/tmp/truffles_process_governance_20260501/architecture_consolidation_handoff_20260501.md`
- `/tmp/truffles_process_governance_20260501/architecture_authority_surface_audit_20260501.md`

Supporting artifacts:

- `/tmp/truffles_process_governance_20260501/tp_architecture_consolidation_handoff_20260501.md`
- `/tmp/truffles_process_governance_20260501/architecture_consolidation_handoff_rca_20260501.md`
- `/tmp/truffles_process_governance_20260501/focused_web_search_architecture_handoff_20260501.md`

Use it before discussing rewrites, module splits, OSS/tool choices, or cross-vertical expansion.

Completed consolidation target:

- `Shadow/Authority Drain Closure`: shadow side services are guarded against authority-active runtime and can be stopped without false observability failure.
- `Shadow Side-Service Removal`: stopped side-service residue is removed after dependency proof; canonical runtime/API/worker surfaces remain.

### Console Calendar kernel proof — 2026-04-26

Artifact bundle:

- `/tmp/truffles_console_calendar_kernel_proof_20260426`

Proven through live API and active DB:

- Keycloak token auth works for Console API proof.
- Explicit headers select target tenant: `X-Company-Id`, `X-Client-Id`, `X-Branch-Id`.
- `GET /console/v1/me` resolves `platform_admin` for `demo_salon/main`.
- `GET /console/v1/calendar/specialists` returns target branch specialists.
- `POST /console/v1/calendar/bookings` creates an appointment in active `truffles_postgres_1/chatbot.appointments`.
- `GET /console/v1/calendar/bookings` reads the created appointment back through Console API.
- `POST /console/v1/calendar/bookings/{id}/cancel` cancels the proof appointment.
- `appointment_audit` records the console cancellation.
- `GET /console/v1/business/go-no-go-readiness` separates `internal_booking_ready=true` from `external_channel_ready=false` / provider blockage.

Proof appointment:

- `b92ca518-1cee-4a8c-b8a0-5ed47de21cd8`
- created by Console API with `source=console`
- cancelled by Console API after readback to avoid leaving an active proof booking

Current blocker truth:

- internal Console Calendar / active DB kernel is API-proven for Platform Admin;
- browser GUI proof is available for Platform Admin internal Calendar create/read/cleanup after the `/calendar/slots` runtime fix;
- full Console Plane readiness is not closed until Owner/Admin role proof, handoff/inbox lifecycle proof, broader audit coverage, and readiness UI proof are complete;
- external WhatsApp channel remains blocked by commercial provider access, not by internal calendar implementation.

### Console Calendar slots and GUI proof — 2026-04-26

Artifact bundle:

- `/tmp/truffles_reality_architecture_recovery_20260426/console_calendar_slots`

What changed:

- fixed `/console/v1/calendar/slots` runtime crash for valid `specialist_id` UUID query parameters;
- FastAPI already converts `specialist_id: UUID`, so the endpoint must pass that UUID to `SchedulingService` directly and serialize it as `str(...)` in the response;
- added a deterministic router test for the UUID conversion contract.

Live proof after deploy:

- runtime fingerprint: `/admin/version.git_commit=9db031ee967999545f8a9673e7e57cf4d7202e73`, `/admin/version.build_time=2026-04-26T13:14:04Z`;
- `semantic_preflight.valid=true`;
- `GET /console/v1/calendar/slots?specialist_id=2bf786b5-5384-451b-9dee-b33eeb025241&date=2026-05-01&duration=60` returns HTTP `200` and `9` available slots;
- Console Web browser proof created appointment `79a9eca5-18ce-48ba-b925-1b32925f71b1` through the GUI, showed it in Calendar, then cleaned it up through Console API;
- DB readback after cleanup: appointment is `CANCELLED`, `source=console`, with proof marker `gui_kernel_proof_20260426_5202ca6e`;
- `appointment_audit` records `agent / console / cancel / CONFIRMED -> CANCELLED`.

Residual note:

- browser proof recorded one transient NextAuth `CLIENT_FETCH_ERROR` during auth navigation, but the final authenticated Calendar flow had no failed `/api/proxy/calendar` or `/api/proxy/me` responses.

### Console Calendar role lifecycle proof — 2026-04-26

Artifact bundle:

- `/tmp/truffles_console_role_lifecycle_proof_20260426`

Proven roles with available credentials:

| Role | Calendar API | Browser GUI | Result |
|---|---:|---:|---|
| `platform_admin` | pass | pass | baseline internal Calendar proof exists |
| `manager` | pass | pass | created, displayed, and cleaned up appointment `7bca5973-bf85-49ad-a951-a7ec3dbf6d3e` |
| `support` | denied | denied | expected least-privilege result: API returns `403`, GUI shows Calendar access denied |

Manager proof details:

- role: `manager`;
- target: `demo_salon/main`;
- GUI path: Calendar page -> booking composer -> service/specialist/date/slot/customer -> create -> visible in list;
- DB readback after cleanup: appointment `CANCELLED`, `source=console`, marker `role_lifecycle_proof_20260426_ad7e5be1`;
- audit readback: `agent / console / cancel / CONFIRMED -> CANCELLED`.

Credential blocker:

- no reusable Owner/Admin role credentials were available in `/home/zhan/secrets/console-rbac-accounts-2026-01-26.json`;
- do not manufacture hidden role success by reusing Platform Admin as Owner/Admin;
- Owner/Admin lifecycle proof remains open until real credentials or an explicit provisioning task creates controlled test accounts.

---

## База данных

| Параметр | Значение |
|----------|----------|
| Контейнер | truffles_postgres_1 |
| База | chatbot |
| Пользователь | ${DB_USER} |
| Пароль | ${DB_POSTGRESDB_PASSWORD} |

**Где брать креды:** на проде источник истины — `/home/zhan/infrastructure/.env` (переменные `DB_POSTGRESDB_USER`, `DB_POSTGRESDB_PASSWORD`).
В `truffles-api/.env` `DB_USER` может отсутствовать — используйте значения из infra env.

### Подключение
```bash
# Из SSH
docker exec -it truffles_postgres_1 psql -U "$DB_USER" -d chatbot

# Запрос
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c 'SELECT ...'
```

### Таблицы (ключевые)
- clients, companies, branches — орг‑структура/тенант
- agents, agent_memberships — роли доступа в консоли
- client_settings — настройки клиента
- users, conversations, messages — ядро диалогов
- handovers — заявки на менеджера
- outbox_messages — ACK‑first доставка
- audit_events — аудит действий консоли
- console_idempotency_keys — идемпотентность console API
- metrics_daily — агрегированные метрики

Полный список таблиц и дата актуализации — `docs/IMPERIUM_CONTEXT.yaml`.

---

## Клиенты

| name | client_id | telegram_chat_id |
|------|-----------|------------------|
| truffles | 499e4744-5e7f-4a97-8466-56ff2cdcf587 | -1003362579990 |
| demo_salon | <CLIENT_ID> | -1003412216010 |

---

## API

| URL | Назначение |
|-----|------------|
| https://api.truffles.kz | Python API |

### Endpoints
- `POST /webhook/{client_slug}` — входящие сообщения от ChatFlow (прямой путь, preferred)
- `POST /webhook` — входящие сообщения (legacy wrapper)
- `POST /telegram-webhook` — callbacks от Telegram
- `GET /media/{path}` — выдача локально сохранённого медиа по подписи
- `GET /health` — проверка здоровья
- `GET /admin/health` — health/self-heal метрики
- `POST /admin/outbox/process` — обработка ACK-first очереди (admin token)
- `GET /admin/metrics` — чтение дневных метрик (admin token)
- `POST /admin/metrics/snapshot` — запуск snapshot метрик (admin token)
- `POST /admin/media/cleanup` — TTL‑очистка `/home/zhan/truffles-media` (admin token)
- `POST /reminders/process` — обработка напоминаний

### Removed shadow side services

Provider Gateway side app, Knowledge Gateway side app, Inbox Service, Decision Core, and Outbox Service side app were removed on 2026-05-02 after dependency proof. Use canonical `truffles-api` routes and canonical workers.

**WhatsApp Webhook URL (ChatFlow):**
`https://api.truffles.kz/webhook/{client_slug}?webhook_secret=<SECRET>`

**Inbound verification (ChatFlow):**
- Реальный inbound = WA‑сообщение клиента → ChatFlow → `/webhook/{client_slug}`; `send-text` — outbound и не создаёт inbound.
- POST на `/webhook` без WA‑клиента = симуляция (использовать только если DoD это допускает).
- В БД поле называется `messages.metadata` (JSONB), не `message_metadata`.
- `instanceId` в webhook — это routing‑token, который мы задаём в URL/metadata; provider‑ID ChatFlow не используем.

### Переменные окружения (API)
- `NO_RESPONSE_ALERT_MINUTES` — порог минут для алерта “вход есть — ответа нет” (default: 3).
- `OUTBOX_COALESCE_SECONDS` — тишина перед склейкой сообщений в outbox (default: 8).
- `OUTBOX_MAX_WAIT_SECONDS` — максимум ожидания до принудительной обработки outbox (default: 10).
- `OUTBOX_PROCESS_LIMIT` — лимит сообщений на один запуск `/admin/outbox/process` (default: 10).
- `OUTBOX_MAX_ATTEMPTS` — максимум попыток outbox перед статусом FAILED (default: 5).
- `OUTBOX_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для повторов outbox (default: 2).
- `OUTBOX_STALE_PROCESSING_SECONDS` — через сколько секунд PROCESSING считается зависшим и переходит обратно в очередь (default: 120).
- `WEBHOOK_PIPELINE_BUDGET_MS` — бюджет (мс) для /webhook пайплайна (LLM/RAG gating) (default: 7000).
- `CONSOLE_IDEMPOTENCY_TTL_SECONDS` — TTL незавершённых console idempotency ключей (default: 600).
- `ALERTS_ADMIN_TOKEN` — токен для admin/outbox эндпойнтов.
- `CHATFLOW_RETRY_ATTEMPTS` — количество попыток отправки в ChatFlow (default: 3).
- `CHATFLOW_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для ChatFlow (default: 0.5).
- `CHATFLOW_MEDIA_BASE_URL` — базовый URL ChatFlow media API (default: https://app.chatflow.kz/api/v1).
- `PUBLIC_BASE_URL` — публичный base URL API для signed media (default: http://localhost:8000).
- `MEDIA_SIGNING_SECRET` — секрет подписи для `/media/*` (обязателен в проде).
- `MEDIA_URL_TTL_SECONDS` — TTL подписи для `/media/*` (default: 3600).
- `MEDIA_STORAGE_DIR` — базовый каталог медиа (default: /home/zhan/truffles-media).
- `MEDIA_CLEANUP_TTL_DAYS` — TTL очистки локальных медиа (default: 7).
- `MEDIA_STORAGE_WARN_BYTES` — порог алерта по объёму (default: 5GB).
- `PROVIDER_GATEWAY_INBOUND_ENABLED` — включает `POST /provider/inbound` (global).
- `PROVIDER_GATEWAY_INBOX_ENABLED` — пишет `inbox_events` для provider inbound.
- `PROVIDER_GATEWAY_INBOX_REQUIRED` — если `1`, inbound отвечает ошибкой при сбое записи `inbox_events`.
- `PROVIDER_GATEWAY_STATUS_ENABLED` — включает `POST /provider/status`.
- `PROVIDER_GATEWAY_OUTBOUND_ENABLED` — отправка outbox через Provider Gateway (global; требует `PROVIDER_GATEWAY_OUTBOUND_URL`).
- `PROVIDER_GATEWAY_OUTBOUND_URL` — URL provider gateway outbound endpoint.
- `PROVIDER_GATEWAY_STATUS_CALLBACK_URL` — callback URL для статусов отправки.
- `PROVIDER_GATEWAY_TOKEN` — токен для inbound/outbound/status.
- `QDRANT_COLLECTION` — коллекция Qdrant (default: truffles_knowledge; при `TEST_MODE=1` и пустом env → truffles_knowledge_ci).
- `KNOWLEDGE_SNAPSHOT_ENABLED` — включает canonical `/knowledge/snapshot` on `truffles-api`.
- `KNOWLEDGE_SNAPSHOT_TOKEN` — токен для canonical snapshot route (header `X-Knowledge-Snapshot-Token`).
- `KNOWLEDGE_SNAPSHOT_TTL_SECONDS` — TTL snapshot (сек).
- `KNOWLEDGE_SNAPSHOT_HMAC_KEY` — HMAC‑секрет подписи snapshot.
- `KNOWLEDGE_SNAPSHOT_KEY_ID` — key id для подписи snapshot (optional).
- `KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED` — включает shadow-consumer для consult snapshot (default: false).
- `KNOWLEDGE_SNAPSHOT_CONSULT_MODE` — режим consult snapshot: `shadow|fallback|strict` (default: shadow).
- `KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST` — список `client_slug` для canary/cutover (через запятую).
- `BOOKING_CONFIRM_ENABLED` — включить LLM-first slot_extract + booking_confirm (default: false).
- `BOOKING_CONFIRM_CONFIDENCE_THRESHOLD` — порог уверенности для подтверждения слота (default: 0.9).
- `CALENDAR_TOKEN_ENC_KEY` — ключ pgcrypto для шифрования OAuth токенов календаря (обязателен после включения sync).
- `CALENDAR_SYNC_INBOUND_ENABLED` — включает расписание inbound sync через outbox (default: true).
- `CALENDAR_SYNC_INBOUND_INTERVAL_SECONDS` — минимальный интервал inbound sync на branch (default: max(60, `CALENDAR_SYNC_STALE_SECONDS`/2), либо 300 при `CALENDAR_SYNC_STALE_SECONDS=0`).
- `CALENDAR_SYNC_STALE_SECONDS` — порог staleness для health gate (default: 900).
- `CALENDAR_SYNC_LOOKBACK_DAYS` — глубина lookback для inbound sync (default: 14).
- `CALENDAR_SYNC_LOOKAHEAD_DAYS` — глубина lookahead для inbound sync (default: 60).
- `METRICS_DAILY_AUTO_ENABLED` — включает ежедневный snapshot metrics_daily (default: false).
- `METRICS_DAILY_RUN_HOUR_UTC` — час запуска (UTC) для snapshot (default: 1).
- `METRICS_DAILY_RUN_MINUTE_UTC` — минута запуска (UTC) для snapshot (default: 5).
- `METRICS_DAILY_TARGET_OFFSET_DAYS` — на сколько дней назад считать (default: 1).
- `METRICS_DAILY_STATUS_ALLOWLIST` — allowlist `client.status` (default: active, `all` = без фильтра).
- `METRICS_DAILY_RETRY_SECONDS` — backoff при ошибке snapshot (сек, default: 600).
- `METRICS_DAILY_RETRY_MAX` — максимум повторов snapshot за день (default: 3).
- `METRICS_DAILY_BACKFILL_MAX_DAYS` — лимит backfill дней для `/admin/metrics/snapshot` (default: 31).
- `AUDIO_TRANSCRIPTION_ENABLED` — включить транскрибацию коротких голосовых (default: false).
- `AUDIO_TRANSCRIPTION_MAX_MB` — максимум размера голосового для транскрипции (default: 2).
- `AUDIO_TRANSCRIPTION_MODEL` — модель транскрипции (default: whisper-1).
- `AUDIO_TRANSCRIPTION_LANGUAGE` — язык транскрипции (например: ru).

---

## Console Web + Keycloak (Control Plane)

**Домены:**
- `https://console.truffles.kz` — Console UI
- `https://auth.truffles.kz` — Keycloak (OIDC)

**Где живёт конфигурация:**
- `docker-compose.console.yml` — Keycloak + console‑postgres + console‑redis (Traefik routing).
- `truffles-api/docker-compose.yml` — сервис `console-web` (Traefik routing).
- `console-web/.env.local` — `NEXTAUTH_URL`, `KEYCLOAK_ISSUER`, `NEXT_PUBLIC_API_URL`.
- `truffles-api/docker-compose.yml` — `CONSOLE_OIDC_JWKS_URL`, `CONSOLE_OIDC_ISSUER`, `CONSOLE_OIDC_AUDIENCE`.

**Данные и источники:**
- Console API читает/пишет **core DB** (`DATABASE_URL` в `truffles-api`, контейнер `truffles_postgres_1`, БД `chatbot`).
- `console-postgres` в `docker-compose.console.yml` сейчас не используется Console API (резерв под будущие нужды).

**Secrets (локально, не в git):**
- `/home/zhan/secrets/console-contract.env` → `CONSOLE_API_TOKEN` для Schemathesis/k6.
- `/home/zhan/secrets/console-e2e.env` → креды Playwright.

**Console tenancy (interim):**
- `/console/v1/me` возвращает список `clients` и `selection_required`.
- При нескольких клиентах обязателен `X-Client-Id`.
- UI хранит выбор в `localStorage` (`console:client_id`) и очищает на logout.
- Полный орг‑уровень (Company/Client/Branch) — DEC‑011, в разработке.

**Запуск (docker‑вариант, preferred):**
```bash
docker compose -f /home/zhan/truffles-main/docker-compose.console.yml up -d console-postgres console-redis console-keycloak
GIT_COMMIT=$(git -C /home/zhan/truffles-main rev-parse HEAD) \
BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web
```

**Console Web restart (build info wired):**
```bash
/home/zhan/truffles-main/scripts/restart_console_web.sh
```

**Legacy (если console‑web ещё на PM2):**
- см. `docs/DEPLOYMENT_RUNBOOK.md` (раздел PM2).

---

## Calendar Scheduling (SoT) — доступы и шаги

**Env (API):**
- Файл: `/home/zhan/truffles-main/truffles-api/.env`
- Обязательно: `CALENDAR_TOKEN_ENC_KEY` (32+ bytes random, хранить как секрет).
- OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

**Миграция схемы (Phase 1):**
```bash
set -a
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot < /home/zhan/truffles-main/truffles-api/migrations/009_add_calendar_scheduling.sql
```

**Проверка:**
```bash
docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c \"\\dt appointments\"
docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c \"\\dt calendar_blocks\"
```

**Backfill legacy bookings → appointments (Phase 3):**
```bash
set -a
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot < /home/zhan/truffles-main/truffles-api/migrations/010_backfill_appointments_from_bookings.sql
```

**Backfill tokens (pgcrypto):**
```bash
set -a
source /home/zhan/truffles-main/truffles-api/.env
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot -v key="$CALENDAR_TOKEN_ENC_KEY" \\
  -c \"UPDATE google_calendar_tokens SET \\
      access_token_enc = pgp_sym_encrypt(access_token, :'key'), \\
      refresh_token_enc = pgp_sym_encrypt(refresh_token, :'key'), \\
      encryption_version = 1, encrypted_at = now() \\
    WHERE access_token_enc IS NULL AND access_token IS NOT NULL;\"
```

**Fail-closed поведение:**
- Если `CALENDAR_TOKEN_ENC_KEY` не задан, а токены уже зашифрованы — доступ к календарю отключён.

---

## Console API Idempotency (мутации)

- Все мутации `/console/v1/*` должны идти с idempotency‑key в заголовке.
- Ответ сохраняется в `console_idempotency_keys` по ключу `(client_id, idempotency_key, scope)` и переиспользуется.
- Для диагностики: `console_idempotency_keys` + `audit_events` (дубликаты не должны появляться).

---

## Console API Contracts

- Источник истины: `contracts/console_api/openapi.v1.yaml` + `contracts/console_api/errors.v1.json`.
- Генерация: `truffles-api/scripts/generate_openapi.py` (обновлять после изменений в `console` роутерах).
- Любые breaking изменения — через новую версию контракта.

---

## Observability (OTel/Tempo)

**Включение:**
- `OTEL_ENABLED=1`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318/v1/traces`
- `OTEL_SERVICE_NAME` — для API (`truffles-api`).
- `OTEL_SERVICE_NAME_OUTBOX` — для outbox worker (`truffles-outbox`).
- `OTEL_SERVICE_NAME_SENTINEL` — для sentinel (`truffles-sentinel`).
- Span attrs: `message_id`/`outbox_id`/`trace_id`/`client_slug`/`conversation_id`/`branch_id`.

**Проверки:**
```bash
curl -fsS http://localhost:3200/ready
curl -fsS http://localhost:3200/metrics | rg -m 1 tempo_distributor_spans_received_total

docker logs truffles-api --tail 5 | rg -i 'otel enabled'
docker logs truffles-outbox --tail 5 | rg -i 'otel enabled'
docker logs truffles-sentinel --tail 5 | rg -i 'otel enabled'
```

---

## Quality toolchain (OSS стандарт)

**Цель:** повторяемые проверки без “самописных” велосипедов.

**Инструменты (принятый стандарт):**
- **Schemathesis** — contract/fuzz по OpenAPI.
- **Hypothesis** — property‑based инварианты логики.
- **k6** — load/soak (контейнер).
- **OpenTelemetry + Prometheus + Grafana + Loki/Tempo** — наблюдаемость.
- Канонический coverage contract теперь лежит в `docs/OBSERVABILITY_SURFACES.yaml`.
- Каноническая live-check команда теперь `python3 scripts/observability_truth.py --repo-root . --output /tmp/observability_truth.json`.
- Removed shadow side services are guarded against reintroduction by `scripts/shadow_removal_dependency_truth.py`.
- Runtime now exports worker heartbeat metrics for `truffles-outbox` / `truffles-sentinel` via `worker_heartbeat_status` and `worker_heartbeat_age_seconds`; `/admin/health/check` mirrors them under `checks.workers`.

**Примечание:** интеграция инструментов делается через Task Package и фиксируется evidence в `STATE.md`.

---

## Development Tool/Test Inventory Governance

Purpose: keep development work controlled, discoverable, and transferable to zero-memory agents.

Mandatory work chain:

`Business capability -> architecture layer -> inventory lookup -> decision record -> implementation -> proof -> impacted docs/inventory update`

### Business Capability Platform Technology Policy — 2026-05-09

Truffles is a business capability platform, not a framework demo and not a vertical-specific chatbot.

External orchestration frameworks such as LangChain or LangGraph are allowed only after a bounded adoption gate:

- define the business capability and architecture layer the framework serves;
- prove the existing registered toolchain cannot cover the need cleanly;
- create/update a Decision Ledger entry;
- register owner, inputs, outputs, run conditions, proof value, limitations, rollback path, and acceptance criteria in `TECH.md` / `STRUCTURE.md`;
- prove a bounded spike without weakening the canonical hot path, boundary validation, state ownership, traceability, or go/no-go evidence.

Frameworks must not own semantic meaning, business truth, tenant authority, booking calendar truth, or product-readiness claims.

Signal and knowledge policy:

- lexicons, regex, aliases, normalizers, and RAG retrieval may provide evidence or candidate facts;
- policy-core remains the semantic owner;
- packs/capabilities/operational DB/tool contracts own business data and allowed actions;
- inline core phrase/domain hardcode must be classified as normalization-only debt or moved to manifest/pack/capability ownership.

Current inventory note: as of the 2026-05-09 documentation repair, no active LangChain/LangGraph runtime dependency is registered as part of the canonical hot path.

### Process optimization closure — 2026-05-02

Status: `PROCESS_OPTIMIZED_AND_GUARDED`.

This is the technical execution contract for future agents and humans:

- One active product block at a time.
- Docs update is an output of proof, not a substitute for proof.
- Do not create or rely on a new tool, script, architecture test, runtime worker, router, provider adapter, OSS dependency, or external integration until the function is registered below or in `STRUCTURE.md`.
- If inventory and runtime reality disagree, repair the inventory and prove the selected product path before adding more implementation.
- Keep documentation proportional: update impacted durable docs after proof; do not create duplicate docs for reporting.

Validation tiers:

| Tier | When | Checks |
|---|---|---|
| `T0 Reality` | Before runtime/product claims. | `git status --short --branch`, `git rev-parse HEAD`, `/admin/version`, `/health`, selected live probes. |
| `T1 Touched Slice` | After code/script/test/doc edits. | `python3 -m py_compile` for touched Python, targeted pytest, `git diff --check`, `git diff --cached --check`. |
| `T2 Governance` | After process, architecture, scripts, or docs status changes. | `python3 scripts/decision_ledger_guard.py --repo-root .`, `python3 scripts/product_work_map_guard.py --repo-root .`, `python3 scripts/tool_inventory_guard.py --repo-root .`, relevant semantic/shadow guards. |
| `T3 Live Truth` | Before claiming product/runtime state. | `semantic_preflight`, `release_topology_truth`, `go_live_data_truth`, `observability_truth`, `provider_integration_truth || true`. |
| `T4 Architecture Gate` | Before broad closure claims. | `python3 scripts/arch_guard.py --repo-root .`; current accepted independent blocker is only stale `docs/_generated/AGENT_PACKET.json`. |

Process artifacts:

- `/tmp/truffles_process_governance_20260502/tp_process_optimization_closure_20260502.md`
- `/tmp/truffles_process_governance_20260502/focused_web_search_process_optimization_20260502.md`
- `/tmp/truffles_process_governance_20260502/process_optimization_closure_rca_20260502.md`
- `/tmp/truffles_process_governance_20260502/process_optimization_closure_20260502.md`

Creation law:

- No new development tool, script, architecture test, runtime worker, router, provider adapter, or external dependency may be created or used as a new standard until its owner, inputs, outputs, run conditions, proof value, and limits are registered here or in `STRUCTURE.md`.
- If a task needs a new tool but the function overlaps an existing registered tool, repair/extend the existing tool first.
- Run `python3 scripts/tool_inventory_guard.py --repo-root .` after changing `scripts/` or `truffles-api/tests/architecture/`.
- Run `python3 scripts/shadow_removal_dependency_truth.py --repo-root .` after changing removed side-service inventory, topology, or references.
- `scripts/arch_guard.py` runs the shadow removal dependency truth, inventory guard, decision ledger guard, and product work-map guard as part of the architecture gate; current known independent blocker can still be stale generated `docs/_generated/AGENT_PACKET.json`.

Inventory categories:

| Category | Registered tools/tests | Function |
|---|---|---|
| Architecture/governance guards | `scripts/arch_guard.py`, `scripts/recovery_execution_guard.py`, `scripts/whole_system_program_guard.py`, `scripts/authority_freeze_guard.py`, `scripts/authority_registry_block_guard.py`, `scripts/legacy_freeze_guard.py`, `scripts/legacy_mesh_caller_guard.py`, `scripts/legacy_mesh_drain_guard.py`, `scripts/legacy_drain_closure_guard.py`, `scripts/shadow_lane_elimination_guard.py`, `scripts/shadow_removal_dependency_truth.py`, `scripts/operational_entrypoint_dedupe_guard.py`, `scripts/whole_system_governance_closure_guard.py`, `scripts/closure_claim_truth_guard.py`, `scripts/closure_rescue_claim_guard.py`, `scripts/boundary_degrade_guard.py`, `scripts/boundary_rewrite_guard.py`, `scripts/semantic_bridge_growth_guard.py`, `scripts/semantic_contract_sync_guard.py`, `scripts/semantic_owner_reopen_guard.py`, `scripts/single_semantic_owner_guard.py`, `scripts/system_reproof_guard.py`, `scripts/touched_slice_continuity_guard.py`, `scripts/continuity_writer_guard.py`, `scripts/continuity_state_normalization_guard.py`, `scripts/fact_contract_schema_guard.py`, `scripts/fact_family_cutover_guard.py`, `scripts/fact_plane_guard.py`, `scripts/pack_runtime_separation_guard.py`, `scripts/proof_path_guard.py`, `scripts/semantic_preflight.py`, `scripts/tool_inventory_guard.py`, `scripts/decision_ledger_guard.py` | Freeze architecture laws, source-of-truth consistency, semantic ownership, removed shadow side-service dependency/reintroduction checks, boundary behavior, continuity ownership, pack/runtime separation, closure claims, decision/proof classification ledger, and registered tool/test inventory. |
| Runtime/live truth probes | `scripts/release_topology_truth.py`, `scripts/release_runtime_profile.py`, `scripts/go_live_data_truth.py`, `scripts/observability_truth.py`, `scripts/observability_e2e_turn_truth.py`, `scripts/provider_integration_truth.py`, `scripts/shadow_removal_dependency_truth.py`, `scripts/semantic_surface_inventory.py`, `scripts/check_migration_governance.py`, `scripts/check_console_audit_governance.py` | Prove active release cohort, runtime profile, tenant data readiness, observability surfaces, correlated e2e turn observability, provider readiness, removed-shadow dependency/reintroduction state, semantic surface inventory, migration governance, and Console audit governance. |
| Release/restart operations | `scripts/restart_release.sh`, `scripts/restart_api.sh`, `scripts/restart_workers.sh`, `scripts/restart_console_web.sh`, `scripts/restart_knowledge_activation_service.sh`, `scripts/knowledge_activation_postdeploy.sh`, `scripts/platform_admin_control_loop.sh`, `scripts/install_hooks.sh`, `scripts/test_api_container.sh` | Build, deploy, restart, postdeploy, install hooks, and container-test operational surfaces. |
| Session/process tools | `scripts/session_start.sh`, `scripts/session_check.sh`, `scripts/session_gate.sh`, `scripts/session_end.sh`, `scripts/session_resume.sh`, `scripts/session_index_rebuild.sh`, `scripts/session_audit.sh`, `scripts/zero_context_gate.sh`, `scripts/doc_truth_gate.sh`, `scripts/build_agent_packet.py` | Maintain session discipline, zero-context handoff, doc truth checks, and generated agent packet consistency. |
| Quality/booking proof tools | `scripts/booking_confirm_verify.sh`, `scripts/booking_dialog_scenarios.py`, `scripts/booking_quality_matrix_resumable.sh`, `scripts/focused_family_proof.py`, `scripts/quality_artifact_report.py`, `scripts/quality_chain_controller.sh`, `scripts/llm_quality_digest.py`, `scripts/llm_quality_guarded.sh`, `scripts/load_intents.py`, `scripts/intents.json` | Generate/execute booking and LLM-quality scenarios, resumable matrices, focused family proof, quality summaries, and intent fixture loading. |
| Architecture tests | `truffles-api/tests/architecture/test_arch_guard_packet.py`, `truffles-api/tests/architecture/test_authority_freeze_guard.py`, `truffles-api/tests/architecture/test_authority_registry.py`, `truffles-api/tests/architecture/test_authority_registry_block_guard.py`, `truffles-api/tests/architecture/test_boundary_degrade_guard.py`, `truffles-api/tests/architecture/test_boundary_rewrite_guard.py`, `truffles-api/tests/architecture/test_closure_claim_truth_guard.py`, `truffles-api/tests/architecture/test_closure_rescue_claim_guard.py`, `truffles-api/tests/architecture/test_continuity_state_normalization_guard.py`, `truffles-api/tests/architecture/test_decision_ledger_guard.py`, `truffles-api/tests/architecture/test_fact_contract_schema_guard.py`, `truffles-api/tests/architecture/test_fact_family_cutover_guard.py`, `truffles-api/tests/architecture/test_fact_plane_guard.py`, `truffles-api/tests/architecture/test_go_live_data_truth.py`, `truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`, `truffles-api/tests/architecture/test_legacy_freeze_guard.py`, `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`, `truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py`, `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`, `truffles-api/tests/architecture/test_observability_e2e_turn_truth.py`, `truffles-api/tests/architecture/test_observability_truth.py`, `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`, `truffles-api/tests/architecture/test_outbox_runtime_model_registry.py`, `truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`, `truffles-api/tests/architecture/test_proof_blackbox_guards.py`, `truffles-api/tests/architecture/test_provider_integration_truth.py`, `truffles-api/tests/architecture/test_recovery_execution_guard.py`, `truffles-api/tests/architecture/test_release_runtime_profile.py`, `truffles-api/tests/architecture/test_release_topology_truth.py`, `truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`, `truffles-api/tests/architecture/test_semantic_contract_sync_guard.py`, `truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`, `truffles-api/tests/architecture/test_semantic_preflight.py`, `truffles-api/tests/architecture/test_shadow_lane_elimination_guard.py`, `truffles-api/tests/architecture/test_shadow_removal_dependency_truth.py`, `truffles-api/tests/architecture/test_single_continuity_writer.py`, `truffles-api/tests/architecture/test_single_semantic_owner_guard.py`, `truffles-api/tests/architecture/test_system_reproof_guard.py`, `truffles-api/tests/architecture/test_tool_inventory_guard.py`, `truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`, `truffles-api/tests/architecture/test_truth_carrier_freeze.py`, `truffles-api/tests/architecture/test_whole_system_governance_closure_guard.py`, `truffles-api/tests/architecture/test_whole_system_program_guard.py` | Pytest coverage for architecture guards and live-truth contract scripts. |

---

## Console quality gates (Playwright / Schemathesis / k6)
CI uses GitHub secrets for auth and skips jobs if they are missing:
- `CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`
- `CONSOLE_KEYCLOAK_TOKEN_URL`, `CONSOLE_KEYCLOAK_CLIENT_ID`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`,
  `CONSOLE_KEYCLOAK_USERNAME`, `CONSOLE_KEYCLOAK_PASSWORD`
- optional: `CONSOLE_API_TOKEN` (bypass Keycloak for contract/k6)

**Playwright (smoke, read-only):**
```bash
cd console-web
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1 \
KEYCLOAK_ISSUER=https://auth.truffles.kz/realms/truffles \
KEYCLOAK_CLIENT_ID=console-web \
KEYCLOAK_CLIENT_SECRET=console-client-secret \
NEXTAUTH_URL=http://localhost:3000 \
E2E_USERNAME=admin \
E2E_PASSWORD=admin \
npm run test:e2e:smoke
```

**Playwright (mutating, only staging):**
```bash
cd console-web
E2E_ALLOW_MUTATIONS=1 npm run test:e2e:mutating
```

**Schemathesis (GET-only contract smoke):**
```bash
SCHEMATHESIS_TOKEN="<bearer token>" \
schemathesis --config-file contracts/console_api/schemathesis.toml run contracts/console_api/openapi.v1.yaml \
  --url https://api.truffles.kz/console/v1 \
  --include-method=GET \
  --checks all \
  --request-timeout 10 \
  --hypothesis-max-examples=3 \
  --header "Authorization: Bearer ${SCHEMATHESIS_TOKEN}"
```
**Seed IDs:** `contracts/console_api/schemathesis.toml` contains stable `case_id`/`conversation_id` used in contract
checks. If the IDs go stale, update them with a real handover + conversation from the same client as the
console token.

**k6 (smoke modes):**
```bash
CONSOLE_API_URL=https://api.truffles.kz/console/v1 \
CONSOLE_API_TOKEN="<bearer token>" \
k6 run ops/k6/console_smoke.js
```
- **PR non-prod smoke:** `console-k6-pr` в `.github/workflows/ci.yml`; запускается на PR при console-related diff и использует только явный non-prod target через `CONSOLE_K6_PR_*` secrets. Если target/secrets не настроены, job честно skip'ается с причиной.
- **Live manual smoke:** workflow `Console k6` через `workflow_dispatch`; использовать перед релизом после изменений в Console API/фильтрах/пагинации/индексах, перед подключением крупного клиента, при подозрении на деградацию.
- **Nightly live smoke:** workflow `Console k6` по `schedule`; нужен для drift/latency observability вне PR CI.
- **Когда обновлять сценарий:** появился новый “горячий” эндпоинт или изменились параметры фильтров; изменились SLO/пороговые значения.
- **Режим:** только read‑only; low VU/iterations. PR lane не должен указывать на prod; live/manual и nightly используют live API.
- **Selection headers:** при multi-tenant selection можно передать `CONSOLE_API_COMPANY_ID`, `CONSOLE_API_CLIENT_ID`, `CONSOLE_API_BRANCH_ID`.

---

## CI / GitHub Actions (как запускать, зачем и когда)

**Источник правды:** `.github/workflows/ci.yml`.

### Когда CI запускается
- **Pull Request → main:** lint + unit + core‑eval (если затронуты L1‑пути). long/asr только при L2‑изменениях или label `run-long`. build/push/deploy/livecheck не выполняются.
- **Push → main:** полный пайплайн (lint/unit/core/long/asr → build-push → deploy → ci-livecheck), если гейты позволяют.
- **workflow_dispatch:** ручной запуск с опциями `run_long` и `run_livecheck`.

### Console gates
- `console-e2e` (Playwright smoke) — запускается при изменениях в `console-web/**` или CI.
- `console-contract` (Schemathesis GET-only) — запускается при изменениях в `contracts/console_api/**` или console API.
- `console-k6-pr` — автоматический read-only smoke для console-related PR diff; использует только `CONSOLE_K6_PR_*` secrets и non-prod target.
- `Console k6 / console-k6-live` — ручной live smoke через отдельный workflow `.github/workflows/console-k6.yml`.
- `Console k6 / console-k6-nightly` — scheduled live drift check через `.github/workflows/console-k6.yml`.

### Console E2E (локально, чтобы воспроизвести CI)
- Креды: `/home/zhan/secrets/console-e2e.env` (не коммитить).
- Важно: `NEXTAUTH_URL` должен совпадать с `PLAYWRIGHT_BASE_URL` (иначе CSRF).
- Команда и контекст запуска — в `docs/DEV_SETUP.md` (раздел 6).
- Seed данных (идемпотентный) — `truffles-api/scripts/console_e2e_seed.py`.

### Console secrets (источник истины)
- CI secrets: GitHub Actions (`CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`, `CONSOLE_API_TOKEN`).
- Prod host: `/home/zhan/secrets/console-e2e.env` (E2E login + Keycloak client secret).
- Contract/k6 live: `/home/zhan/secrets/console-contract.env` (token or Keycloak user creds).
- PR non-prod k6: GitHub Secrets `CONSOLE_K6_PR_API_URL`, `CONSOLE_K6_PR_API_TOKEN` or preview Keycloak creds `CONSOLE_K6_PR_KEYCLOAK_*`.
- `CONSOLE_API_TOKEN` не хранится в репозитории: получать через Keycloak token endpoint и использовать локально.
- Шаблон переменных: `console-web/.env.e2e.example`.

### Почему этапы пропускаются (skipped)
**Path filters (changes):**
- L1 включает: `truffles-api/app/**`, `truffles-api/tests/**`, `knowledge/**`, `ops/**`, `.github/workflows/**`.
  - Нет L1‑изменений → `core-eval` skip.
- L2 включает: `truffles-api/app/knowledge/**/EVAL.yaml`, `truffles-api/app/knowledge/**/SALON_TRUTH.yaml`, `truffles-api/tests/test_demo_salon_eval.py`.
  - Нет L2‑изменений → `long-eval` и `asr-eval` skip.
**Doc‑only fast lane:**
- Изменения в `SPECS/**`, `STRATEGY/**`, `docs/**`, `AGENTS.md`, `STRUCTURE.md`, `TECH.md`, `STATE.md` не считаются L1 → `core-eval` skip.
- На main build/deploy/livecheck запускаются только если `deploy_required=true` (код/рантайм), иначе пропускаются.
- Отдельно: правки `STATE.md` не запускают deploy/livecheck и не требуют `core-eval` (если нет других L1 изменений).
 - При doc‑only deploy/ci-livecheck job полностью пропускаются (не просто “skipped” шаги).

**deploy_required (точный список путей):**
- `truffles-api/app/**`
- `truffles-api/migrations/**`
- `truffles-api/scripts/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `scripts/restart_api.sh`
- `scripts/restart_workers.sh`
- `scripts/restart_release.sh`
- `scripts/check_migration_governance.py`
- `knowledge/**`

**livecheck_required (точный список путей):**
- `truffles-api/app/**`
- `truffles-api/migrations/**`
- `truffles-api/scripts/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `scripts/restart_api.sh`
- `scripts/restart_workers.sh`
- `scripts/restart_release.sh`
- `scripts/check_migration_governance.py`
- `knowledge/**`
- `ops/**`
- `.github/workflows/**`

**Event gate (PR vs main):**
- На PR `build-push`, `deploy`, `ci-livecheck` всегда skip.
- На main эти шаги выполняются только при успешных обязательных джобах (lint/unit/secret-scan + long/asr, если они не skipped).
- `core-eval` остаётся обязательным quality-signal, но не блокирует deploy.

### Как форсировать проверки
- **long/asr:** label `run-long` на PR или `workflow_dispatch` с `run_long=true`.
- **ci-livecheck:** только на `main` и только если `deploy` сработал; на `workflow_dispatch` нужно `run_livecheck=true`.

### Quality validity gates (`ops/diagnose.py llm-quality`)
- **infra_valid** = пройден preflight/infra-контур (включая webhook_secret/branch/env/judge prerequisites).
- **semantic_valid** = нет threshold/regression breach при валидном сравнении; это contract-level signal, а не полный human-semantic quality verdict.
- Product-quality `green` допустим только после отдельного turn-by-turn human semantic audit (или будущего machine-readable `human_semantic_valid=true`).
- Любой run с `infra_valid=false` считается `INVALID`: его нельзя использовать для сравнения качества и для обновления baseline.
- Обновление canonical baseline (`ops/results/booking_quality.json`) допускается только при `infra_valid=true`, `semantic_valid=true`, `judge.enabled=true` (`judge_mode=sample|all`).
- Strict replay (`--scenarios-file`) без judge допускается только как debug (`--allow-judge-off`) и не считается каноническим quality-evidence.
- Dev Exploration may use `--transport-evidence-policy rendered` to classify semantic failure families without depending on blocked provider delivery.
- Product/Acceptance runs must use `--transport-evidence-policy delivery`; rendered-evidence runs cannot update the canonical baseline or prove go-live readiness.

### Closure layers (mandatory interpretation)
- `structural_complete` = ownership seams, contracts, guards, and code boundaries exist and are enforced.
- `contract_complete` = deterministic/runtime contract proof is green.
- `practical_behavior_complete` = fresh current-head replay is valid and blocker failure families are closed on the live path.
- `human_semantic_complete` = full turn-by-turn human audit is green.
- Product-quality or general `green` is allowed only when all four layers are satisfied; earlier layers never imply the later ones automatically.

### Validation order (local-first)
- Для core/поведенческих правок порядок проверки фиксированный: `local realism` -> `local deterministic` -> `CI deterministic`.
- `local realism` = реальные LLM‑диалоги (10–15 ходов) + chaos перебивки + tool hooks + booking confirm path.
- Если нет `OPENAI_API_KEY`/judge key для required local realism run, статус задачи = `BLOCKED`.
- CI не является источником финальной поведенческой валидации; CI подтверждает воспроизводимость и ловит базовый drift.

### Behavioral RCA / debug order (mandatory)
- Step 1: identify the dominant failure family from `summary.json` and `manual_audit.md/json`.
- Step 2: translate that family into one broken invariant and one shared mechanism. Family labels are evidence surfaces, not final implementation units.
- Step 3: reconstruct the exact path using `responses.jsonl` and `trace_bundle.jsonl`; for live incidents use `python3 ops/diagnose.py dialog-report ...`.
- Step 4: classify the layer before any code change:
  - `owner_error`
  - `boundary_fallback_error`
  - `fact_composition_error`
  - `oracle_or_evaluator_error`
  - `infra_or_runtime_failure`
- Step 5: write one root-cause statement for the shared mechanism, not for a single dialog/turn.
- Step 6: only then add deterministic checks and implement the bounded fix; the checks must prove the mechanism, not only the surfaced wording.
- Step 7: rerun replay + full human semantic audit and state explicitly which shared mechanism is now closed and which residual mechanisms remain open.
- Mandatory debug bundle for behavioral handoff: `summary.json`, `responses.jsonl`, `trace_bundle.jsonl`, `manual_audit.md`, `manual_audit.json`, `manual_audit_workspace.md`, `manual_audit_workspace.json`, `family_registry.json`, `judge_conflicts.jsonl`, exact run command, failing family name, broken invariant, shared mechanism, and layer classification.
- Cross-run comparison before the next RCA block is now explicit: `python3 ops/diagnose.py llm-quality-trends --run-dir <prev> --run-dir <current> ...`.

### CI scope (what belongs in CI)
- В CI держим только простые, быстрые и детерминированные проверки, не требующие внешнего LLM.
- Примеры CI-набора: lint, unit, schema/contracts, deterministic replay, smoke на trace/meta contract.
- Сложные LLM+tools+chaos прогоны выполняются локально перед PR и прикладываются как evidence.

### CI livecheck параллелизм
- **Матрица групп:** `ci-livecheck` запускается в 4 параллельных группах (`pool-a/b/c/d`), каждая гоняет свой набор suite‑ов.
- **Требование к allowlist:** желательно минимум 4 JID в `OUTBOUND_ALLOWLIST_JIDS`; если меньше — фиксируется `ALLOWLIST_TOO_SHORT` и включается fallback.
- **Артефакты:** на группу отдельные `livecheck-artifacts-<group>` и `livecheck-evidence-<group>.md`.
- **Fallback:** если allowlist < 4, `pool-a` запускает все suite последовательно, `pool-b/c/d` пропускаются.

### Livecheck-only (быстрый rerun без полного CI)
- **Когда:** если `ci-livecheck` красный и нужно проверить фикс без повторного lint/unit/build/deploy.
- **Как запустить:** GitHub → Actions → `Livecheck Only` → Run workflow.
  - `expected_commit` = SHA, который уже задеплоен (если пусто — проверяется только `/admin/version`).
  - `expected_version` = `main` (по умолчанию).
  - `min_allowlist_jids` = 4 (должны быть 4 JID в allowlist для параллели).
- **Что делает:** проверяет `/admin/version`, затем гоняет только livecheck suites (4 параллельных пула).
- **Что НЕ делает:** не запускает lint/unit/core/long/asr и не деплоит.
- **Fallback:** если allowlist меньше `min_allowlist_jids`, запускается один пул (`pool-a`) с полным набором suites.

### Гейты build/deploy/livecheck (важно понимать)
- `build-push` запускается только на `main` или `workflow_dispatch`, и только если lint/unit/secret-scan ok.
- `deploy` внутри себя решает `deployed=true/false`; на `main` при `deploy_required=true` silent skip запрещён (job падает).
- `ci-livecheck` job всегда виден, но шаги выполняются только если `deploy.outputs.deployed=true`.

### Concurrency (почему бывают cancelled)
- Для не‑main включён `cancel-in-progress`, поэтому новый PR‑пуш отменяет предыдущие run’ы. Это нормально.

### Быстрый рецепт
- **Док‑изменения без поведения:** PR → проверяем lint/unit; остальные этапы будут skipped — это ожидаемо.
- **Изменение поведения:** merge в main → полный CI + deploy + livecheck.
- **Нужен полный прогон без мержа:** `workflow_dispatch` на `main` с `run_long`/`run_livecheck` (если есть доступ и гейты позволяют).
- **Live‑check sender‑only:** используйте `clean_auto` как отправителя (ChatFlow send‑text) → receiver‑номер салона; если написать на `clean_auto`, ответа не будет. Подробности — `SPECS/SYSTEM_REFERENCE.md` §4.3.

---

## Telegram

| Клиент | Bot username | Bot token |
|--------|--------------|-----------|
| truffles | @truffles_kz_bot | 8045341599:AAGY... |
| demo_salon | @salon_mira_bot | 8249719610:AAGd... |

Webhook URL: `https://api.truffles.kz/telegram-webhook`

---

## Полезные команды

### Логи API
```bash
ssh -p 222 zhan@5.188.241.234 "docker logs truffles-api --tail 100"
```

### Observability Truth
```bash
ssh -p 222 zhan@5.188.241.234 "cd /home/zhan/truffles-main && python3 scripts/observability_truth.py --repo-root . --output /tmp/observability_truth.json"
```
Канон required surfaces и известных gaps — `docs/OBSERVABILITY_SURFACES.yaml`.
Worker liveness is now surfaced through `/metrics` (`worker_heartbeat_*`) and `/admin/health/check` (`checks.workers`).

### Деплой API (prod)
```bash
# Обновить APP_VERSION (используется в /admin/version и livecheck deploy-verify)
ssh -p 222 zhan@5.188.241.234 "sed -i 's/^APP_VERSION=.*/APP_VERSION=main/' /home/zhan/truffles-main/truffles-api/.env"

# CI build/push → pull image (prod standard)
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 RUN_MIGRATIONS=1 MIGRATION_BOOTSTRAP_MODE=auto REQUIRE_GHCR=1 VERIFY_VERSION=1 EXPECTED_GIT_COMMIT=<sha> EXPECTED_VERSION=main bash /home/zhan/truffles-main/scripts/restart_release.sh"

# ❌ Запрещено на проде: локальная docker-compose build/run для API
# restart_release.sh по умолчанию использует GHCR и требует GHCR-образ (REQUIRE_GHCR=1).
# По умолчанию RUN_MIGRATIONS=1: SQL миграции применяются до переключения контейнера.
```
`restart_release.sh` поддерживает `IMAGE_NAME`, `PULL_IMAGE=1`, `RUN_MIGRATIONS=1`, `MIGRATION_BOOTSTRAP_MODE=auto|legacy|off`, `REQUIRE_GHCR=1`, `VERIFY_VERSION=1`, `EXPECTED_GIT_COMMIT`, `EXPECTED_VERSION`, `RESTART_CONSOLE_WEB=1`, `RUN_RELEASE_TOPOLOGY_TRUTH=1`, `RELEASE_TOPOLOGY_TRUTH_OUTPUT`, `RELEASE_ENV_FILE`, `RELEASE_RUNTIME_NETWORK`, `RUNTIME_PROFILE_OUTPUT`.
Он резолвит immutable digest, затем через `scripts/release_runtime_profile.py` выводит derived runtime profile (`OUTBOX_WORKER_MODE`, `DATABASE_LOCAL_CIDRS`) и уже потом применяет один image reference к `truffles-api`, `truffles-outbox`, `truffles-knowledge-activation`, `truffles-sentinel`; затем проверяет console build SHA и пишет topology truth artifact.
`restart_api.sh` используется внутри release flow и поддерживает `EXPECTED_IMAGE`, `MIGRATION_BOOTSTRAP_MODE`.
`scripts/release_topology_truth.py` читает `docs/RELEASE_TOPOLOGY_TRUTH.yaml`, поэтому изменение required cohort делается через явный repo contract. Shadow side-service residue was removed after dependency proof; reintroduction requires a fresh architecture decision and `scripts/shadow_removal_dependency_truth.py`.
`scripts/release_runtime_profile.py` устраняет env/runtime drift для outbox worker mode и передаёт local Docker-network CIDRs в runtime safety, чтобы release behaviour не зависел от session-only override.

Проверка topology truth без релиза:
```bash
ssh -p 222 zhan@5.188.241.234 "cd /home/zhan/truffles-main && python3 scripts/release_topology_truth.py --repo-root . --base-url http://localhost:8000 --output /tmp/release_topology_truth.json"
```

Точечный перезапуск только воркеров (если нужно отдельно):
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env bash /home/zhan/truffles-main/scripts/restart_workers.sh"
```

### Removed shadow side-service lifecycle

Current lifecycle decision: `REMOVED / DEPENDENCY_PROVEN / REINTRODUCTION_GUARDED`. `truffles-provider-gateway`, `truffles-knowledge-gateway`, `truffles-inbox-service`, `truffles-decision-core`, and `truffles-outbox-service` were removed after `scripts/shadow_removal_dependency_truth.py --include-runtime` proved no blocking production callers or live container dependencies. Do not recreate their side-app entrypoints, restart scripts, routers, or containers without a fresh architecture decision. Product traffic must stay on canonical `truffles-api` and canonical workers.

### Перезапуск API (без обновления кода)
```bash
ssh -p 222 zhan@5.188.241.234 "RUN_MIGRATIONS=1 MIGRATION_BOOTSTRAP_MODE=auto bash /home/zhan/truffles-main/scripts/restart_release.sh"
```
По умолчанию перезапуск идёт с GHCR `:main` (REQUIRE_GHCR=1); локальные образы на проде запрещены.
`restart_release.sh` перезапускает API+workers+console в одном шаге и пишет `release_topology_truth.json` для required cohort.

### Go-live data readiness truth
```bash
cd /home/zhan/truffles-main
python3 scripts/go_live_data_truth.py --repo-root . --env-file /home/zhan/truffles-main/truffles-api/.env --output /tmp/go_live_data_truth.json
```
Канон first Beauty v1 target data readiness — `docs/GO_LIVE_DATA_READINESS.yaml`. Этот check доказывает target data readiness отдельно от runtime health, provider integration recovery, booking semantic closure и fleet-wide residual branches.

### Provider integration readiness truth
```bash
cd /home/zhan/truffles-main
python3 scripts/provider_integration_truth.py --repo-root . --base-url http://localhost:8000 --env-file /home/zhan/truffles-main/truffles-api/.env --output /tmp/provider_integration_truth.json
```
Канон first Beauty v1 provider/webhook readiness — `docs/PROVIDER_INTEGRATION_READINESS.yaml`. `no_recent_inbound` is a stale-traffic/canary warning by default, not a hard provider failure; strict degradation is available only through explicit `INTEGRATION_WATCHDOG_NO_RECENT_INBOUND_DEGRADES=1`.

### Запрос к БД
```bash
ssh -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U \"$DB_USER\" -d chatbot -c 'SELECT * FROM clients'"
```

### Qdrant
```bash
ssh -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: ${QDRANT_API_KEY}' 'http://localhost:6333/collections'"
```

### Knowledge update (packs)
- SOP и шаги: `SPECS/SYSTEM_REFERENCE.md` → раздел **4.1 Knowledge update SOP**.
- Важно: использовать `python3`, затем build+restart (без `docker cp`).

---

## Outbox (ACK-first)

- Входящие сообщения только кладутся в outbox (`/webhook*`), обработка идёт отдельным воркером.
- Основной путь: контейнер `truffles-outbox` (loop + backoff).
- Fallback: `/etc/cron.d/truffles-outbox` может вызывать `POST /admin/outbox/process`.
- При ошибке отправки outbox планирует повтор с backoff (next_attempt_at) до `OUTBOX_MAX_ATTEMPTS`.
- Зависшие `PROCESSING` (старше `OUTBOX_STALE_PROCESSING_SECONDS`) переводятся обратно в `PENDING` или в `FAILED` при исчерпании попыток.
- Ручной запуск (на сервере):
```bash
TOKEN=$(/usr/bin/docker exec truffles-api /bin/sh -lc 'echo "$ALERTS_ADMIN_TOKEN"')
curl -fsS -X POST http://localhost:8000/admin/outbox/process -H "X-Admin-Token: $TOKEN"
```

---

## Миграции (ожидают выполнения)

### add_reminder_settings.sql
```sql
ALTER TABLE client_settings
ADD COLUMN IF NOT EXISTS enable_reminders BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS enable_owner_escalation BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS mute_duration_first_minutes INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS mute_duration_second_hours INTEGER DEFAULT 24;
```

После выполнения — обновить owner_telegram_id:
```sql
UPDATE client_settings SET owner_telegram_id = '@ent3rprise' WHERE client_id = '<CLIENT_ID>';
```
