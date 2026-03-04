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
- Quality-constant: бюджет/время не ослабляют acceptance и обязательные gate-проверки.

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
- LLM plan + deterministic safety boundaries.
- Tool-first execution.
- Decision meta/trace mandatory on inbound.
- No semantic hardcode in core routing.

## 5) Delivery protocol (mandatory for every block)

### 5.1 Analysis gate checklist

Каждый блок проходит analysis gate до кода:
1. FACT snapshot (current code/API/data/tests/evidence).
2. Contract delta (schema/API/RBAC/policy changes).
3. Dependency map (blast radius).
4. Risk matrix (P0/P1 + fallback behavior).
5. Migration path (flags, compatibility, cutover order).
6. Verification plan (unit/integration/e2e/negative/anti-drift).
7. Observability plan (decision_meta/trace/audit/outbox signals).
8. Rollback protocol.
9. Block DoD.
10. Explicit approval to implement.

### 5.2 Execution law for zero-context agents

- Один блок = одна worktree = одна ветка = один TP = один Report.
- Перед кодом обязателен FACT pre-check по коду и тестам, а не только по документам.
- Параллельные треки в репозитории не трогать.
- `main` не использовать как рабочую директорию изменений.
- Блок закрыт только при `Passed` + checks + evidence + doc sync.

## 6) Full atomic business-block plan (with expected outcomes)

| Business block | Implementation blocks | Current status | Expected business result | Expected implementation result (DoD) |
|---|---|---|---|---|
| B01 Tenant Core & Data Isolation | `UCPV1-PHASE2-SLICE1`, `UCPV1-PHASE2-SLICE2-*` | in_progress | Нет cross-tenant чтений/записей, tenant-context обязателен | Все критичные `/admin/*` write/read пути fail-closed без tenant-context; negative tests green |
| B02 RBAC & Governance Model | `UCPV1-PHASE1`, `UCPV1-PHASE2-SLICE2-*` | in_progress | Права ролей прозрачны и стабильны для Platform Admin first | Серверный RBAC source-of-truth; несанкционированные действия получают deterministic `403/400` |
| B03 Domain Catalog + Capabilities v2 | `UCPV1-PHASE3` | passed | Новая ниша подключается без core-кода | Domain registry CRUD + capability templates + effective merge по scope + schema validation |
| B04 Onboarding State Machine v2 | `UCPV1-PHASE4` | passed | Go-live воспроизводим и управляем в Console | Branch не уходит в live при незакрытых blockers; preflight/approve/reject/waive серверные |
| B05 Policy Governance Split | `UCPV1-PHASE5` | passed | Hard-law отделен от operational policy | Versioned policy registry lifecycle реализован (publish/history/rollback) + runtime effective merge с hard-law deny |
| B06 Tool Registry Certification | `UCPV1-PHASE6` | passed | Подключение инструментов безопасно и управляемо | Несертифицированный tool не попадает в effective capabilities; scope rules + health checks |
| B07 Provider/Channel Control (WA-first) | `UCPV1-PHASE7` | passed | Каналы управляются предсказуемо при деградации провайдера | Provider lifecycle registry + explicit branch channel status + safe degrade mode |
| B08 Knowledge Studio + Pack Compiler | `UCPV1-PHASE8` | passed | Контент управляется через Draft->Validate->Publish->Rollback | Publish блокируется при нарушении minimum data contract; rollback one-click |
| B09 Runtime Pack-Agnostic Decoupling | `UCPV1-PHASE9` | passed (owner-closed) | Runtime независим от demo-пака | Нет прямых demo imports в core runtime; adapter boundaries + neutral fallback |
| B10 SLA/SLO Engine (Multi-level) | `UCPV1-PHASE10` | passed | SLA/SLO профили реально влияют на runtime и escalation | Policy-driven thresholds + predictable actions + auditability on each violation |
| B11 Compliance KZ Retention/Lifecycle | `UCPV1-PHASE11` | passed | KZ boundary и lifecycle соблюдаются автоматически | Retention/delete/export jobs с owner+TTL+audit trail по каждому data class |
| B12 Control Tower for Platform Admin | `UCPV1-PHASE12` | passed | Fleet управляется через Console без CLI как основного пути | Risk queue + readiness board + drift board + action center с evidence links |
| B13 Migration Program (Current -> Target) | `UCPV1-PHASE13` | passed | Переход без stop-the-world | Waves (`canary -> cohort -> fleet`) с pass/fail gates и rollback triggers |

## 7) Execution status (FACT)

Completed in this program chain:
- `UCPV1-PHASE1` passed.
- `UCPV1-PHASE2-SLICE1` passed.
- `UCPV1-PHASE2-SLICE2-ANALYSIS` passed.
- `UCPV1-PHASE2-SLICE2-IMPL1` passed.
- `UCPV1-GATES-SANITARY` passed.
- `UCPV1-PHASE2-SLICE2-IMPL2` passed.
- `UCPV1-PHASE3` passed.
- `UCPV1-PHASE4` passed.
- `UCPV1-PHASE5` passed.
- `UCPV1-PHASE6` passed.
- `UCPV1-PHASE7` passed.
- `UCPV1-PHASE8` passed.
- `UCPV1-PHASE10` passed.
- `UCPV1-PHASE11` passed.
- `UCPV1-PHASE12` passed.
- `UCPV1-PHASE13` passed.

Current active block:
- `none` (UCP v1 phase chain closure complete).

Current queue head:
- `none` (awaiting next program block definition).
- Latest completed block (2026-03-02): `UCPV1-PHASE13` closure pass-gate on fresh `origin/main` with deterministic checks (`108 passed`), governance checks (`SESSION_AGENT=a704 scripts/session_check.sh`, `scripts/zero_context_gate.sh`), and contract check (`python3 scripts/generate_openapi.py --check`).
- Latest closed slice update (2026-03-02): `UCPV1-PHASE13` slice3 added `GET /console/v1/admin/control-tower/migration-program/{wave}` with per-wave deterministic decision (`promote|hold`) and wave-filtered promotion action queue.

Post-UCP UX convergence chain (A705):
- `UVC-UX-STAGE1-A705`: done (IA ownership matrix in existing tabs, no new top-level tab introduced).
- `UVC-UX-STAGE2-A705`: done (plain-language contract hardening across Tenants/Settings/Knowledge/Ops/Marketing).
- `UVC-UX-STAGE3-A705`: done (cross-tab loop continuity Integrations -> Workspace -> Ops -> Tenants).
- `UVC-UX-STAGE4-A705`: done (fail-closed anti-drift contract gate merged and green in CI).
- `UVC-UX-STAGE5-A705`: done (rollout go/no-go matrix + KPI baseline/post + merged-main monitoring evidence delivered; fleet decision `GO`, legacy cleanup checklist completed).
- `UVC-UX-PROGRAM-CLOSEOUT-A705`: done (steady-state control-loop automation handoff completed: wrapper-script + scheduled/dispatch workflow + runbook/canon sync + local evidence artifact).
- `UVC-UX-STEADY-STATE-OPERATIONS-A705`: done (operator-assist remediation automation added to control-loop with deterministic plan/brief/commands artifacts, strict decision gate option, and contract tests).
- `UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705`: done (deterministic audit governance gate added to control-loop + CI, canonical audit/backlog duplicates cleaned, and fail-closed governance artifact evidence delivered).
- `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`: in_progress (wave1 merged via PR `#885`; wave2 merged via PR `#888`; wave3 merged via PR `#889`; closeout merged via PR `#890`; wave4 merged via PR `#891`; final-close merged via PR `#892`; wave5 delivered on branch with deterministic checks (`py_compile`, `pytest 16 passed`, frontend lint/build, `session_check`) and further bounded extraction (`console_router_utils` param-validation helpers + `provisioning-wizard-shell-panels`), pending merge and closure review).

## 8) Program-level DoD

- Каждый бизнес-блок проходит analysis gate до начала реализации.
- Каждый бизнес-блок имеет отдельные TP/Report с фиксированным BLOCK_ID и зависимостями.
- Контракты (API/schema/roles/policy/capabilities) задокументированы и покрыты тестами.
- Нет hardcode под конкретного клиента/нишу в core runtime.
- Все production-critical изменения подтверждены evidence (`tests + traces + audit + SQL/API snapshots`).

## 9) No-go constraints

- Нельзя ослаблять hard-law/safety/tenant guards ради скорости.
- Нельзя обходить обязательные gates и выдавать "упрощенный pass".
- Нельзя смешивать текущий блок с параллельными задачами других треков.
- Нельзя закрывать блок без проверки фактической реализации и doc sync.

## 10) Risks and blockers to monitor

- Legacy demo-coupling в runtime fallback paths.
- Остаточные смешанные role assumptions в части `/admin/*`.
- Большой blast radius console-router изменений без блоковой декомпозиции.
- Drift между кодом и документами при пропуске FACT pre-check и post-sync.

## 11) Deliverables and canonical links

- Master program TP: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`
- Master report (this doc): `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- Dependency graph: `docs/BLOCK_GRAPH.yaml`
- Zero-context templates: `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`, `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
- Program entrypoint evidence: `STATE.md` NOW block for UCPV1 chain
