# TP-2026-02-22-universal-control-plane-v1-phase5-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE5
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE4
- `UNLOCKS`: UCPV1-PHASE6

## Название/цель
Universal Control Plane v1 / Phase 5: закрыть Policy Governance split (hard-law vs operational policy) end-to-end через versioned policy registry в Console и runtime enforcement с fail-closed guardrails.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase4-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/schemas/capabilities.py`
  - `truffles-api/app/services/capabilities_service.py`
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/tests/test_capabilities_runtime.py`
  - `truffles-api/tests/test_policy_handler_runtime.py`
- `Baseline commands`:
  - `rg -n "@router\\.(get|post|patch|delete)\\(\"/admin/.+policy" truffles-api/app/routers/console.py`
  - `rg -n "policy_bundle|handoff_policy|allowed_fact_scopes" truffles-api/app/schemas truffles-api/app/services contracts`
  - `rg -n "policy_pack|_get_policy_pack|_resolve_hard_law_sections" truffles-api/app/routers/webhook/policy.py`
- `FACT findings`:
  - Отдельного policy-registry CRUD в `/admin/*` нет; policy приходит из knowledge pack (`contracts/policy/policy_bundle.v1.jsonschema`) и runtime handler (`truffles-api/app/routers/webhook/policy.py`).
  - В capabilities уже есть governance controls (`allowed_fact_scopes`, `handoff_policy`), но нет operational policy override contract.
  - Runtime hard-law gate уже определяет секции через `_resolve_hard_law_sections`, значит можно безопасно запретить runtime override для hard-law section на boundary-слое.
- `Detected drift (docs vs code)`: `partial` (B05 требует split-governance, в коде есть hard-law gate, но нет formalized operational override contract в capabilities).

## One web search (mandatory before implementation)
- **Query (exact):** `policy as code versioning rollback best practices open policy agent`
- **Date/time (local):** `2026-02-27 17:23, Asia/Almaty`
- **Why this query is precise:** таргетирует практики policy-as-code с упором на governance/versioning/rollback, чтобы выбрать безопасный путь без broad refactor.
- **Sources opened (from this query):**
  - Open Policy Agent docs, Policy Management: https://www.openpolicyagent.org/docs/management
  - Open Policy Agent docs, Deployment model: https://www.openpolicyagent.org/docs/deploy
- **Existing solutions found:** policy-as-data, signed/controlled distribution, explicit separation policy decision and enforcement boundary.
- **Decision:** `reuse + integrate` — расширяем существующий capabilities contract и runtime policy boundary вместо внедрения нового policy engine в этом блоке.
- **Rejected options:**
  - Вводить новый внешний policy orchestrator: отклонено как DEC-level архитектурный скачок вне scope.
  - Делать policy override через клиентские regex в core: отклонено (нарушает semantic-first charter и no-hardcode gate).
- **Open questions:** нет; решение по versioned policy registry принято в рамках wave2 текущего блока.

## Root cause (mandatory)
- **Symptom:** hard-law и operational policy смешаны на runtime data-path; tenant/branch-level customization operational policy не формализован в capabilities contract.
- **Minimal reproduction:**
  - Проверить `CapabilitiesPayload` и runtime policy load path (`_get_policy_pack`) на наличие operational override contract.
  - Проверить, можно ли безопасно переопределить policy response без риска hard-law override.
- **Evidence to capture:** schema diff, runtime merge behavior, tests для allowed override и hard-law deny.
- **Five Whys (or equivalent):**
  1. Why? B05 еще не закрыт после B04.
  2. Why? Нет explicit contract для operational policy overrides в capabilities.
  3. Why? Runtime policy load берет pack/config напрямую без capability-level policy patch layer.
  4. Why? Не реализован boundary-guard, который разрешает только operational sections и блокирует hard-law sections.
  5. Why? Без boundary-guard невозможно безопасно выполнить governance split в production path.
- **Root cause statement:** отсутствует явный operational-policy override boundary между capabilities и runtime policy-pack с fail-closed защитой hard-law sections.
- **Fix mechanism:** двухволновая реализация: (1) capability-level boundary contract (`policy_overrides`) для operational sections; (2) versioned `client_policy_versions` registry + Console publish/rollback API + runtime merge from registry с hard-law deny.

## Reuse-first plan (mandatory)
- **Internal reuse:** `CapabilitiesPayload`, `merge_capabilities`, runtime context (`get_runtime_capabilities`), existing hard-law resolver `_resolve_hard_law_sections`.
- **External reuse:** OPA policy-as-code principles использованы как design reference (без runtime dependency).
- **Why not reinvent the wheel:** механизм capability merge и hard-law gate уже есть; нужен минимальный contract extension + boundary enforcement, а не новая policy subsystem.

## Invariant
- Hard-law override недопустим в branch/client runtime path.
- Policy governance остается fail-closed: если override невалиден, runtime использует базовый policy pack.
- Semantic ownership в LLM core не заменяется regex/hardcode логикой.
- RBAC ownership сохраняется: capabilities patch доступен только platform admin.

## Scope
- Добавить `policy_overrides` в capabilities schema (операционные секции только).
- Применить operational policy overrides в runtime `_get_policy_pack`.
- Ввести versioned policy registry (`client_policy_versions`) с publish/history/rollback semantics.
- Добавить Console API `/admin/policy-registry`, `/admin/policy-registry/publish`, `/admin/policy-registry/rollback` (platform-admin only).
- Подключить runtime policy merge к effective policy registry версии (branch -> client fallback) c hard-law deny.
- Добавить/обновить deterministic tests для schema/runtime/console/service слоев.

## Out of scope
- Изменение policy bundle schema `policy_bundle.v1`.
- Перестройка onboarding/knowledge pipelines.
- CI workflow redesign.

## Touch-list
- `truffles-api/app/schemas/capabilities.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/capabilities_service.py`
- `truffles-api/app/services/policy_registry_service.py`
- `truffles-api/app/models/client_policy_version.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/migrations/044_add_client_policy_versions.sql`
- `truffles-api/tests/test_capabilities_runtime.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `truffles-api/tests/test_console_policy_registry.py`
- `truffles-api/tests/test_policy_registry_service.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase5-a500.md`
- `docs/SESSION_INDEX.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`

## Plan (1..N)
1. Зафиксировать B05 analysis gate и создать phase5 TP/Report.
2. Реализовать wave1 boundary: `policy_overrides` + runtime hard-law deny.
3. Реализовать wave2 registry: новая таблица/модель/сервис versioning+rollback.
4. Добавить Console policy registry API и platform-admin audit trail.
5. Подключить runtime merge к effective registry version с branch->client fallback.
6. Прогнать deterministic checks + openapi drift gate + doc sync.

## DoD
- `CapabilitiesPayload` принимает только operational policy overrides (`payment_info`, `discounts`) и отвергает hard-law section keys.
- Runtime `_get_policy_pack` применяет operational override только если section не входит в hard-law set.
- Versioned registry `client_policy_versions` поддерживает publish/history/rollback без hard-law override surface.
- Console policy registry API работает только для platform admin и оставляет audit trail.
- Runtime использует effective registry version (branch first, client fallback) и fail-closed при невалидном payload.
- Deterministic tests зелёные для schema/runtime/console/service слоев.
- Block docs/session sync выполнен без дрейфа и блок переводится в `passed`.

## Checks
- `python3 -m py_compile truffles-api/app/models/client_policy_version.py truffles-api/app/services/policy_registry_service.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `pytest -q truffles-api/tests/test_policy_registry_service.py truffles-api/tests/test_console_policy_registry.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_console_onboarding_contract_api.py truffles-api/tests/test_console_domain_catalog.py`
- `pytest -q truffles-api/tests/test_apply_sql_migrations.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`

## Evidence
- test logs from policy registry + runtime + console suites in Checks
- migration + model + router/service diffs in touch-list
- phase5 report with final verdict and no residual B05 registry gap

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** локальные targeted tests только по touched modules.
- **Stop condition:** 2 итерации без новых signals -> вернуть RCA и не расширять scope.
- **Escalation path:** Brain/Top Architect approval для расширения до full booking-quality contour.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased enablement через tenant-scoped publish in policy registry (client/branch scopes).
- **Go/no-go signals:** tests pass + openapi check pass + отсутствие hard-law override в runtime path.
- **Rollback:** `POST /admin/policy-registry/rollback` на стабильную версию или revert commit.
- **Post-release monitoring window:** 24h on policy-gate traces (`policy_gate`, `source`, runtime errors).

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase5-a500.md`
  - `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase5-a500.md`
  - `docs/SESSION_INDEX.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - phase5 переводится в `passed` только после green checks + block graph/state sync.

## Rollback
- Revert текущий commit(s) блока.
- Проверить policy registry через `POST /admin/policy-registry/rollback`.
- Перезапустить deterministic suite из секции Checks.

## No-go
- Не добавлять hard-law override через capabilities.
- Не внедрять новый policy engine без DEC.
- Не расширять scope на unrelated runtime tracks.
- Не ослаблять safety gates ради “быстрого pass”.

## Risks/Blockers
- Возможна необходимость расширить operational sections beyond `payment_info/discounts` после product review.
- Высокая связность `webhook/policy.py` повышает риск regressions при дальнейшем расширении B05.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (next planned block `UCPV1-PHASE6`)
- `Do not touch`: unrelated booking quality tracks and onboarding state machine code
- `Open risks`: возможное расширение operational sections beyond текущего allow-list
- `First command to verify`: `pytest -q truffles-api/tests/test_policy_registry_service.py truffles-api/tests/test_console_policy_registry.py`
