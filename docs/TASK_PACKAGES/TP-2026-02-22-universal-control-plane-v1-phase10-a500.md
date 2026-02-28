# TP-2026-02-22-universal-control-plane-v1-phase10-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE10
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE9
- `UNLOCKS`: UCPV1-PHASE11

## Название/цель
Universal Control Plane v1 / Phase 10: SLA/SLO Engine (Multi-level), чтобы SLA-профили были policy-driven, применялись по иерархии `global -> domain -> client -> branch`, и влияли на routing/escalation/alerts предсказуемо и аудируемо.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests (current state)`:
  - `truffles-api/app/routers/webhook/router_sla.py`
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `ops/console_owner_admin_kpi_snapshot.py`
  - `ops/owner_admin_control_loop.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_integrations_registry.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
- `Baseline commands`:
  - `rg -n "sla|slo|threshold|escalation_timeout|fallback_rate|provider_ops" truffles-api/app/routers truffles-api/app/services truffles-api/app/schemas`
  - `rg -n "sla|escalation_quality|provider_binding|readiness" truffles-api/tests ops`
  - `sed -n '1,260p' truffles-api/app/routers/webhook/router_sla.py`
  - `sed -n '420,640p' truffles-api/app/services/onboarding_state.py`
- `FACT findings`:
  - SLA-логика присутствует в нескольких независимых контурах:
    - in-memory router SLA (`fallback/timeout`) без scope layering и without persisted profile,
    - case list SLA status (`ok/warning/breached`) на fixed age thresholds (1h/2h),
    - onboarding SLA control loop (`reminder_1/reminder_2/escalation_timeout` + provider incidents),
    - provider ops lifecycle SLA (`p0/p1/p2 -> deadline -> due_soon/overdue`),
    - owner/admin KPI thresholds в ops snapshot tool.
  - Нет единого versioned SLA profile registry с effective merge `global/domain/client/branch`.
  - Нет единого runtime admission path, где SLA-profile deterministically управляет routing/escalation actions.
  - Нет audit trail для SLA profile publish/rollback/violation на platform-gov уровне.
- `Detected drift (target vs current)`:
  - Target B10 требует multi-level policy engine; current state покрывает только разрозненные SLA islands.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenSLO specification service level objectives alert policies`
- **Date/time (local):** `2026-02-28 08:19 (+05)`
- **Why this query is precise:** нужен vendor-neutral reference для структуры SLO/SLA objective и policy model перед проектированием contracts.
- **Sources opened (from this query):**
  - OpenSLO project: `https://github.com/OpenSLO/OpenSLO`
- **Existing solutions found:**
  - standard-like objective model (`service`, `indicator`, `objective`, `alert policy`) пригоден как reference schema для profile-driven SLA/SLO engine.
- **Decision:**
  - проектировать profile contracts в стиле objective/policy (threshold + window + action), но с Truffles-specific scopes `global/domain/client/branch`.
- **Rejected options:**
  - ad-hoc hardcoded thresholds в runtime-модулях без central profile registry.
- **Open questions:**
  - глубина windowing для v1: fixed windows vs rolling windows per metric class.

## Root cause (mandatory)
- **Symptom:** B10 не закрыт: SLA/SLO сигналы есть, но единый multi-level engine отсутствует.
- **Minimal reproduction:**
  - `rg -n "_calculate_sla_status|_resolve_provider_ops_sla|_build_sla_control_loop|_update_router_sla" truffles-api/app`
  - `rg -n "escalation_timeout_minutes|escalation_quality_rate" truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- **Evidence to capture:**
  - кодовые места SLA islands,
  - отсутствие profile registry migration/model/API,
  - текущие deterministic tests around isolated contours.
- **Five Whys (or equivalent):**
  1. Почему B10 не закрыт: SLA-решения распределены по разным слоям без общего источника истины.
  2. Почему распределены: исторически добавлялись локальные контуры под конкретные pain-points (onboarding/inbox/provider).
  3. Почему этого недостаточно: нельзя централизованно управлять порогами и действиями по tenant hierarchy.
  4. Почему это риск: drift между контурами и непредсказуемые violation actions при масштабировании ниш/клиентов.
  5. Почему нужен отдельный блок: требуются contract/data/runtime changes с governance и rollback.
- **Root cause statement:**
  - отсутствие единой data-driven SLA/SLO policy-модели и enforcement pipeline по всем scope-уровням.
- **Fix mechanism:**
  - внедрить SLA profile registry + effective merge + runtime violation actions + auditable lifecycle.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse `onboarding_state` SLA loop как один из signal producers,
  - reuse provider lifecycle queue decision model (`priority -> deadline/state`),
  - reuse existing console policy governance patterns (`publish/history/rollback` from phase5).
- **External reuse:**
  - OpenSLO objective/policy vocabulary как reference model для профилей.
- **Why not reinvent the wheel:**
  - ядро v1 строится поверх существующих SLA telemetry points, добавляя единый contract и governance, а не переписывая все метрики с нуля.

## Invariant
- Любой inbound заканчивается только `FACT/COLLECT/HANDOFF`.
- Hard-law остается выше SLA policy (SLA не может ослабить hard-law).
- Tenant isolation + audit обязательны для любой SLA profile write/change.
- No semantic hardcode in core runtime.
- Quality-constant gate: отсутствие полного required контура = `BLOCKED`, не упрощенный pass.

## Scope
- Создать единый SLA/SLO profile contract и storage lifecycle.
- Реализовать effective merge `global -> domain -> client -> branch`.
- Подключить profile-driven thresholds/actions в runtime governance boundaries.
- Добавить observability + audit для violations и profile changes.
- Обновить Console API/UI для управления профилями.

## Out of scope
- Полный redesign LLM policy-core.
- Переписывание всей исторической аналитики/метрик.
- Full production migration wave (это `UCPV1-PHASE13`).

## Touch-list (planned)
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `truffles-api/migrations/*` (new SLA profile tables)
- `truffles-api/app/models/*` (SLA profile models/snapshots)
- `truffles-api/app/services/*` (SLA profile/effective/violation service)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/*` (runtime adapters where violation action applies)
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/*` (unit/integration for profile merge + violation actions)
- `contracts/console_api/openapi.v1.yaml`

## Plan (1..N)
1. Закрыть Analysis Gate и согласовать contract delta (schema/API/RBAC).
2. Ввести SLA profile registry (`draft/published/rollback`) с audit trail.
3. Реализовать effective profile merge по hierarchy scopes.
4. Подключить runtime violation action resolver (routing/escalation/alerts).
5. Добавить deterministic tests (positive/negative/anti-drift).
6. Обновить console contracts/UI и evidence docs.
7. Провести bounded acceptance checks без long llm-quality lane.

## Analysis Gate (required for code start)
1. FACT Snapshot: текущие SLA islands и существующие API/DB/test coverage.
2. Contract Delta: новые profile schemas + endpoints + role rules.
3. Dependency Map: `console`, `webhook`, `onboarding_state`, `owner_admin`, analytics tables.
4. Risk Matrix: violation over-trigger, stale profile cache, cross-scope merge drift.
5. Migration Plan: backward-compatible defaults + profile fallback + rollout flags.
6. Test Plan: unit/integration/negative + anti-drift snapshots.
7. Observability Plan: profile id/version in decision_meta + trace stage for SLA action.
8. Rollback Plan: revert profile snapshot and disable action mapping by flag.
9. DoD: deterministic profile effect on routing/escalation/alerts with audit evidence.
10. Approval: implementation starts only after analysis package approval.

## DoD
- SLA profile lifecycle available in Console (`draft/publish/history/rollback`) with RBAC/audit.
- Effective profile merge deterministic across `global/domain/client/branch`.
- Runtime emits `decision_trace`/`decision_meta` with profile/version and violation action.
- Violation actions are predictable and covered by deterministic tests.
- `docs/BLOCK_GRAPH.yaml` updates `UCPV1-PHASE10 -> passed` only after evidence-backed checks.

## Checks
- Analysis stage (current block state):
  - `rg -n "sla|slo|escalation_timeout|fallback_rate|provider_ops" truffles-api/app truffles-api/tests ops`
  - `python3 -m py_compile truffles-api/app/routers/webhook/router_sla.py truffles-api/app/services/onboarding_state.py truffles-api/app/services/console_owner_admin.py`
- Implementation stage (future, mandatory):
  - `cd truffles-api && ruff check app tests`
  - `cd truffles-api && pytest -q tests/test_console_onboarding_state.py tests/test_console_integrations_registry.py tests/test_console_cases_helpers.py`
  - `cd truffles-api && pytest -q tests/test_message_endpoint.py -k "sla or escalation"`
  - `cd truffles-api && python3 scripts/generate_openapi.py --check`
  - bounded `ops/diagnose.py` verification (без long lane для этого slice).

## Evidence
- Analysis evidence:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
  - fact references in:
    - `truffles-api/app/routers/webhook/router_sla.py`
    - `truffles-api/app/services/onboarding_state.py`
    - `truffles-api/app/routers/console.py`
    - `truffles-api/app/schemas/console.py`
    - `ops/console_owner_admin_kpi_snapshot.py`
- Implementation evidence (future):
  - tests + trace/meta + SQL/API snapshots + rollback proof.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` for this analysis-only step.
- **Fail-fast / scope lock:** only deterministic/read-only checks in this block stage.
- **Stop condition:** if deterministic gates show regression/no new evidence in 2 итерациях, stop-the-line and RCA.
- **Escalation path:** Brain/Top Architect for scope or contract delta decisions.

## Release safety (mandatory for non-doc changes)
- **Strategy:** staged rollout by scope (`global -> pilot domain -> selected client -> branch`).
- **Go/no-go signals:** violation false-positive rate, escalation surge, fallback-rate drift, outbox pressure.
- **Rollback:** profile snapshot rollback + action mapping flag off.
- **Post-release monitoring window:** at least `24h` with ops guard snapshots.

## Doc sync plan (after implementation)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`

## Rollback
- rollback profile to previous published snapshot,
- disable profile-driven violation actions by feature flag,
- revert phase10 commits if deterministic gates fail.

## No-go
- Нельзя вводить hardcoded thresholds в runtime вместо profile contracts.
- Нельзя ослаблять hard-law/policy gates ради SLA tuning.
- Нельзя закрывать блок без evidence trace/meta/audit.

## Risks/Blockers
- Fragmented SLA logic can cause contract drift if migrated partially.
- Violation-action misconfiguration can over-escalate and inflate outbox/manager load.
- Program-level dependency note: `UCPV1-PHASE9` remains blocked in graph, but owner override allows continuing `phase10` implementation slices with bounded checks and without long-lane acceptance claims.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes (analysis package ready; implementation slices allowed by owner override).
- `Start from`: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `Do not touch`: unrelated parallel tracks.
- `Open risks`: merge drift between SLA islands.
- `First command to verify`: `rg -n "sla|slo|policy" truffles-api/app/routers/console.py truffles-api/app/services`
