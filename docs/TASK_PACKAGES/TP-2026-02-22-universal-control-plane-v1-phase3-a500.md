# TP-2026-02-22-universal-control-plane-v1-phase3-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE3
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE2-SLICE2-IMPL2
- `UNLOCKS`: UCPV1-PHASE4

## Название/цель
Universal Control Plane v1 / Phase 3: реализовать Domain Catalog + Capabilities v2 для platform-admin управления нишами через Console, включая domain registry CRUD, domain capability templates и effective merge `global -> domain -> client -> branch` без core hardcode.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/models/*`
  - `truffles-api/app/services/capabilities_service.py`
  - `truffles-api/tests/test_console_*`
- `Baseline commands`:
  - `rg -n 'onboarding-blueprints|reference-packs|/admin/capabilities|domain_slug' truffles-api/app/routers/console.py`
  - `rg -n 'CapabilitiesPayload|merge_capabilities|domain_slug' truffles-api/app/services/capabilities_service.py truffles-api/app/schemas/capabilities.py`
- `FACT findings`:
  - В runtime есть `client_capabilities` (scope `client|branch`), но нет DB-managed domain catalog registry.
  - `onboarding-blueprints` каталог сейчас статический (service-level list), без CRUD через Console.
  - `reference_packs` управляется через upsert/list, но это не покрывает полноценный domain registry с capability templates.
  - `get_capabilities` в `/admin/capabilities` сейчас мерджит только `client -> branch`; layer `domain` отсутствует.
- `Detected drift (docs vs code)`: target B03 в master report требует Domain registry CRUD + capability templates + merge `global/domain/client/branch`, что частично отсутствует в коде.

## One web search (mandatory before implementation)
- **Query (exact):** `schema-driven feature flags configuration hierarchy override precedence`
- **Date/time (local):** `2026-02-27 15:09 (+05), Asia/Almaty`
- **Why this query is precise:** фиксирует best-practice для управляемых capability-профилей: schema validation, deterministic override precedence, fail-closed config application.
- **Sources opened (from this query):**
  - Martin Fowler, Feature Toggles: https://martinfowler.com/articles/feature-toggles.html
  - Twelve-Factor App (Config): https://12factor.net/config
  - OWASP ASVS Access Control Design: https://owasp-aasvs4.readthedocs.io/en/latest/V4.1.html
- **Existing solutions found:** hierarchical config merge with explicit precedence, schema-first payload validation, server-side centralized authorization.
- **Decision:** `reuse + integrate` existing `CapabilitiesPayload` + `merge_capabilities` + console platform-admin guards; добавить недостающий domain layer и registry как data-model extension.
- **Rejected options:**
  - Новый отдельный capability engine/service: отклонено как лишняя архитектурная развилка в этом блоке.
  - Domain templates в кодовых константах: отклонено (нарушение pack/config-only управления).
- **Open questions:** `none` (scope блока зафиксирован, migration deterministic).

## Root cause (mandatory)
- **Symptom:** новая ниша не может быть полностью заведена через Console как управляемая сущность с capability template и predictable effective merge.
- **Minimal reproduction:**
  - Проверить `/admin/capabilities` effective payload при наличии `domain_slug` в client/branch payload.
  - Убедиться, что отдельного domain registry CRUD endpoint отсутствует.
- **Evidence to capture:** router diff, migration, deterministic tests для merge precedence и domain registry CRUD.
- **Five Whys (or equivalent):**
  1. Почему onboarding новых ниш неполный? Нет DB-managed domain registry.
  2. Почему это критично? Platform Admin не может управлять доменами через Console end-to-end.
  3. Почему текущего reference pack недостаточно? Он хранит контентный пакет, но не capability template и lifecycle домена.
  4. Почему effective merge неполный? В коде реализован только `client -> branch` слой.
  5. Почему нужен fix в этом блоке? Это прямой DoD для B03 перед Phase4 onboarding-state-machine.
- **Root cause statement:** в текущей реализации отсутствует управляемый domain layer как источник capability templates и отсутствует его включение в runtime-effective merge.
- **Fix mechanism:** добавить domain catalog table/model/API + включить domain template layer в deterministic merge pipeline `global -> domain -> client -> branch`.

## Reuse-first plan (mandatory)
- **Internal reuse:** `CapabilitiesPayload`, `merge_capabilities`, `_require_platform_admin`, existing console audit/permission patterns.
- **External reuse:** не требуется; задача решается внутри текущих контрактов платформы.
- **Why not reinvent the wheel:** ключевые примитивы уже есть; расширяем их domain-layer и registry вместо новой подсистемы.

## Invariant
- Tenant isolation fail-closed сохраняется.
- Platform-admin remains source of truth for governance writes.
- Existing client/branch capabilities API contract не ломается.
- Никакого semantic hardcode в core runtime.

## Scope
- Добавить DB-managed domain registry with capability template payload.
- Добавить Console API для domain registry CRUD (platform-admin only).
- Добавить domain-layer в effective capabilities merge (`global -> domain -> client -> branch`).
- Добавить deterministic tests для:
  - access contract (platform-admin only),
  - schema validation для template payload,
  - merge precedence correctness.
- Canon sync (`SPECS/CONTROL_PLANE.md`) + report/state evidence.

## Out of scope
- Phase4 onboarding-state-machine implementation.
- Branch change/go-live workflow redesign.
- Runtime LLM policy-core behavior changes.
- CI pipeline changes.

## Touch-list
- `truffles-api/migrations/043_add_domain_capability_templates.sql`
- `truffles-api/app/models/domain_capability_template.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/capabilities_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_domain_catalog.py`
- `truffles-api/tests/test_console_admin_provisioning.py` (if merge assertions need extension)
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase3-a500.md`

## Plan (1..N)
1. Ввести DB/model для domain catalog capability templates (migration + ORM).
2. Добавить console schema + endpoints list/upsert/disable для domain registry.
3. Реализовать helper effective merge с domain layer и подключить в `/admin/capabilities` (+ onboarding contract capability mismatch path).
4. Добавить deterministic tests по access/schema/merge precedence.
5. Синхронизировать canon docs + report/state + block status.

## DoD
- Domain registry CRUD доступен через Console API и ограничен `platform_admin`.
- Capability template payload валидируется schema-first (`CapabilitiesPayload`).
- Effective capabilities учитывает domain template layer перед client/branch overrides.
- Targeted tests green и подтверждают precedence `global -> domain -> client -> branch`.
- `docs/BLOCK_GRAPH.yaml` для `UCPV1-PHASE3` переведен в `passed` только после evidence.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/capabilities_service.py truffles-api/app/schemas/console.py truffles-api/app/models/domain_capability_template.py truffles-api/tests/test_console_domain_catalog.py`
- `pytest -q truffles-api/tests/test_console_domain_catalog.py`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "capabilities or platform_admin"`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py -k "capability or onboarding"`

## Evidence
- migration + ORM + API diff
- test outputs
- phase3 report
- state entry + block graph update

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** сначала новые targeted tests, затем ограниченный regression subset по onboarding/provisioning.
- **Stop condition:** 2 итерации без нового сигнала -> обновление RCA перед продолжением.
- **Escalation path:** Brain/Top Architect approval for runs >3.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout (platform-admin canary tenant first).
- **Go/no-go signals:** endpoints access contract (403/200), merge precedence tests, absence of provisioning regressions.
- **Rollback:** revert block commit + migration-compatible disable (table remains, endpoints hidden by revert).
- **Post-release monitoring window:** 24h audit monitoring for domain-catalog events.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `SPECS/CONTROL_PLANE.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase3-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - code/doc drift по domain capabilities не переносится в следующий блок; текущий блок закрывается только при синхронизации.

## Rollback
- Revert block commit.
- Повторно прогнать targeted tests для подтверждения возврата контракта.

## No-go
- Не добавлять domain semantics в core-runtime hardcode.
- Не менять unrelated `/admin/branch-changes*` и marketing endpoints.
- Не ослаблять platform-admin governance gates.
- Не выполнять работу в `truffles-main/main`.

## Risks/Blockers
- Возможен конфликт с существующими client payload без `domain_slug`; fallback должен оставаться deterministic.
- Нужна аккуратная совместимость: domain layer должен быть optional и не ломать current tenants.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `truffles-api/app/routers/console.py` around `/admin/capabilities` and onboarding/reference pack endpoints
- `Do not touch`: runtime webhook decision core and unrelated tenancy waves
- `Open risks`: backward compatibility for tenants with empty `domain_slug`
- `First command to verify`: `pytest -q truffles-api/tests/test_console_domain_catalog.py`

## Branch / Worktree / Base
- Branch: `feat/2026-02-27-ucpv1-phase3-a500`
- Worktree: `/home/zhan/worktrees/2026-02-27-ucpv1-phase3-a500`
- Base: `origin/main`
