# Universal Control Plane v1 Master Program (A500)

## 1) Program intent

Построить platform-agnostic Control Plane, где Platform Admin управляет компаниями, клиентами, филиалами, поведением консультанта и данными через Console (кроме архитектурных изменений ядра), а новые ниши подключаются через packs/config/contracts без клиентского hardcode.

## 2) Approved decisions (owner-confirmed)

1. Hierarchy: `company -> client -> branch` (override сверху вниз).
2. Isolation: shared infra + strict tenant guards + tenant-scoped audit.
3. Compliance: raw/PII/backups только в KZ.
4. Hard policy ownership: только Platform Admin.
5. Tools/integrations onboarding: только через сертифицированный registry.
6. Capabilities publish в prod: только Platform Admin.
7. Branch override разрешен для `channels/providers/booking_mode/timezone` и `SLA/operational policy`; hard-law override запрещен.
8. SLA/SLO layering: `global -> domain -> client -> branch`.
9. Handoff truth: Console queue = source of truth; Telegram = paging fallback.
10. Retention profile: baseline `10.A` (messages/media/trace/audit lifecycle).
11. Cross-tenant learning: только opt-in и только обезличенные агрегаты.
12. Client deletion: soft-delete -> grace -> hard purge + audit trail.

## 3) Non-negotiable invariants

- Любой inbound завершает ровно один outcome: `FACT` или `COLLECT` или `HANDOFF`.
- Hard-law выше всех локальных правил и не меняется branch-слоем.
- Без валидного tenant context действия в runtime/console не выполняются.
- Любая write/change операция остается auditable.
- Подключение новых ниш без изменения decision core.

## 4) Architecture target (control-plane view)

### 4.1 Data and tenancy
- Canonical context в каждом API/event: `company_id/client_id/branch_id/client_slug`.
- Fail-closed selection + cross-tenant denial.
- Tenant-scoped storage keys и audit payloads.

### 4.2 Governance planes
- `Policy plane`: hard-law (platform-controlled) + operational policies (scope-limited overrides).
- `Capabilities plane`: channels/providers/features/tools, effective merge by scope.
- `Knowledge plane`: Draft -> Validate -> Publish -> Rollback, published artifacts only.
- `Ops plane`: SLA/SLO, drift alerts, remediation actions, evidence links.

### 4.3 Runtime contract
- LLM plan + deterministic safety.
- Tool-first execution.
- Decision meta/trace mandatory on inbound.

## 5) Program phases and mandatory analysis gate

Каждый phase выполняется только через analysis gate.

### Analysis gate checklist (for every major block)
1. FACT snapshot (current code/API/data/tests/evidence).
2. Contract delta (schema/API/RBAC/policy changes).
3. Dependency map (blast radius).
4. Risk matrix (P0/P1 + fallback behavior).
5. Migration path (flags, compatibility, cutover order).
6. Verification plan (unit/integration/e2e/negative/anti-drift).
7. Observability plan (decision_meta/trace/audit/outbox signals).
8. Rollback protocol.
9. Phase DoD.
10. Explicit approval to implement.

### Phase map

- `Phase 1`: Governance bootstrap and contract hardening.
- `Phase 2`: Tenant/RBAC hardening and canonical context consistency.
- `Phase 3`: Domain catalog + capabilities/domain profiles for any niche.
- `Phase 4`: Onboarding state machine + go-live gates + reference integrity.
- `Phase 5`: Policy governance split (hard-law vs operational) + override enforcement.
- `Phase 6`: Tool/provider certification lifecycle and drift controls.
- `Phase 7`: Knowledge studio maturity + pack-agnostic runtime boundary hardening.
- `Phase 8`: SLA/SLO multi-level engine + control-tower operations.
- `Phase 9`: KZ retention, deletion lifecycle, compliance automation.
- `Phase 10`: Fleet migration waves (canary -> cohort -> full fleet) with rollback gates.

## 6) Execution status

- `Phase 1` completed: capabilities write governance locked to `platform_admin` with tests and canon sync.
- `Phase 2` slice 1 completed: tenant hierarchy write (`companies/clients/lifecycle`) locked to `platform_admin` with tests and canon sync.
- `Phase 2` slice 2 analysis completed: remaining `/admin/*` role-boundary map and priority queue fixed for implementation wave.
- `Phase 2` slice 2 implementation wave 1 completed: governance catalog reads (`onboarding-blueprints`, `reference-packs`) locked to `platform_admin`.
- Next in queue: `Phase 2` slice 2 implementation wave 2 (remaining provisioning/admin role-boundary normalization).

## 7) Program-level DoD

- Каждый phase имеет evidence-backed close report.
- Нет client-specific hardcode в core behavior.
- All critical gates are enforceable in API (not UI-only).
- Control Plane supports onboarding новых ниш через config/pack contracts.

## 8) No-go constraints

- No bypass for hard-law/safety gates.
- No cross-tenant implicit access.
- No branch override of hard-law policy blocks.
- No acceptance without deterministic checks + evidence.

## 9) Risks to manage

- Legacy demo-coupling in runtime fallback paths.
- Existing mixed role assumptions (owner/admin write scopes).
- Large blast radius of console router changes.
- Operational drift if migration waves skip gating.

## 10) Deliverables

- Master program TP: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`
- Master report (this doc): `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- Phase-1 TP: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase1-a500.md`
- Phase-1 report: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase1-a500.md`
- Phase-2 TP (slice 1): `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-a500.md`
- Phase-2 report (slice 1): `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-a500.md`
- Phase-2 TP (slice 2 analysis): `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-a500.md`
- Phase-2 report (slice 2 analysis): `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-analysis-a500.md`
- Phase-2 TP (slice 2 implementation wave 1): `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-impl1-a500.md`
- Phase-2 report (slice 2 implementation wave 1): `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl1-a500.md`
