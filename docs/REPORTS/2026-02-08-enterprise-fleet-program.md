# Enterprise Fleet Program (2026-02-08)

**Status:** PROPOSAL (execution-ready)  
**Owner:** Top Architect / Brain  
**Scope:** единая операционная модель управления 100000+ компаний (подключенные + новые), с поэтапной реализацией в 5 PR.

---

## 1) Цель программы

Сделать Console реальной единой управляющей поверхностью для всего жизненного цикла клиента:
- от подключения (prospect/onboarding),
- через ежедневные операции (интеграции, знания, команда, заявки),
- до масштабной эксплуатации (массовые операции, drift-control, audit, SLA),
- без split между `/console/v1/*`, legacy `/admin/*`, ручными скриптами и ad-hoc SQL.

Критерий успеха: Platform Admin может управлять большими портфелями компаний без ручных обходов и без риска tenant-утечек.

---

## 2) Факт-карта: что уже сделано и что нет

### 2.1 Уже сделано (подтверждено кодом)

1. Lifecycle read semantics для tenants уже реализованы:
- `GET /console/v1/admin/clients` с `lifecycle=active|archived|all` (`truffles-api/app/routers/console.py:5263`, фильтры `:5290-5292`).
- `GET /console/v1/admin/branches` с `lifecycle=active|archived|all` (`truffles-api/app/routers/console.py:5345`, фильтры `:5372-5374`).

2. Lifecycle write semantics для client уже реализованы:
- `POST /console/v1/admin/clients/{client_id}/archive` (`truffles-api/app/routers/console.py:5745`).
- `POST /console/v1/admin/clients/{client_id}/restore` (`truffles-api/app/routers/console.py:5833`).
- Prechecks на активные агенты/memberships/branches (`_collect_client_archive_blockers`, `truffles-api/app/routers/console.py:941`).
- Свободный `status` через `PATCH /admin/clients/{id}` запрещен (`truffles-api/app/routers/console.py:5685`).

3. Модель данных client уже содержит `deleted_at`:
- `truffles-api/app/models/client.py:17`.

4. Integrations registry + drift guard уже есть:
- `GET /console/v1/admin/integrations` (`truffles-api/app/routers/console.py:5417`).
- Drift signals/alerts (`_build_branch_integration_status`, `_emit_integration_drift_signals`, `truffles-api/app/routers/console.py:1055`, `:1125`).
- Тесты: `truffles-api/tests/test_console_integrations_registry.py`.

5. Legacy admin security hardening уже проведен:
- Token guard `_require_admin_token` (`truffles-api/app/routers/admin.py:120`).
- `prompt/settings/heal/outbox/metrics/...` требуют `X-Admin-Token`.
- `/admin/health` и `/admin/version` оставлены публичными как compatibility (`truffles-api/app/routers/admin.py:712`, `:728`).

### 2.2 Ключевые gaps, которые еще остались

1. Нет полноценного membership/RBAC admin surface:
- Есть только создание агента (`POST /console/v1/admin/agents`, `truffles-api/app/routers/console.py:6147`).
- Нет явных API на update membership scope, disable/enable membership, re-scope между company/client/branch.

2. Runbook lift в Console неполный:
- Console Ops Jobs сейчас только `outbox_process|heal|metrics_snapshot` (`truffles-api/app/routers/console.py:1293`).
- Ключевые операции все еще в скриптах (`ops/sync_client.py`, `ops/backfill_branch_rag.py`, `ops/diagnose.py`).

3. Legacy `/admin/*` все еще production-critical для consumers:
- CI/livecheck и runbooks завязаны на `/admin/health`, `/admin/version`, `/admin/outbox/process` (например `.github/workflows/ci.yml:1250`, `ops/diagnose.py:5602`, `:5760`).
- Значит одномоментное выключение legacy сломает контур эксплуатации.

4. Коммерческий lifecycle компании как enterprise-объекта не формализован до операционного состояния:
- В core есть только `company.billing_info` и onboarding `payment_status`; нет полноценной subscription/invoice модели (`docs/PROCESSES.md:434`).

5. Нет fleet-scale слоя массовых операций и SLA-приоритизации по портфелю:
- Нет batch операций (archive/restore/migrate/check) с dry-run, approval, artifact trail.
- Нет системной очереди remediate-задач по деградациям интеграций/данных.

---

## 3) Целевая Enterprise Operating Model

### 3.1 Объекты управления (must-have)

1. **Company**: коммерческий контракт, биллинг-контекст, owner-контакты, compliance flags.
2. **Client**: продуктовый tenant-контур (packs/capabilities/ops).
3. **Branch**: операционная единица канала (instance_id/phone/webhook_secret/timezone).
4. **Membership**: кто и в каком scope имеет доступ.
5. **Integration Binding**: факт связки branch с provider + drift-status.
6. **Ops Job**: управляемое действие с dry-run/execute/history/artifacts.

### 3.2 State machines

1. **Company lifecycle**:
- `prospect -> contracting -> onboarding -> active -> at_risk -> suspended -> archived`.

2. **Client lifecycle**:
- `active <-> archived` (уже реализовано), плюс причины и блокеры.

3. **Branch lifecycle**:
- `draft -> active -> degraded -> inactive`.

4. **Membership lifecycle**:
- `invited -> active -> disabled -> revoked`.

5. **Integration lifecycle**:
- `healthy -> warning -> degraded -> disconnected` (в Console уже частично есть).

### 3.3 Управленческие инварианты

1. Никаких mutating действий без audit reason и actor attribution.
2. Никаких кросс-tenant операций без явного scope и dry-run preview.
3. Любой bulk execute должен иметь dry-run output + confirmation_id.
4. Любая деградация интеграции должна иметь route-to-action (job/runbook), не только индикатор.

---

## 4) План реализации в 5 PR

## PR-1 Fleet Registry Read + Context Semantics

**Scope**
- Единый read-реестр по Company/Client/Branch/Integration с консистентными lifecycle фильтрами.
- Unified list/search/sort/pagination для портфельного режима Platform Admin.
- `Console /me` и selectors синхронизированы с lifecycle режимами для platform-admin.

**DoD**
- Platform Admin получает корректные Active/Archived/All views по всем уровням.
- Context bar/selection не подмешивает архив в active-режим.
- OpenAPI и frontend types синхронизированы.

**Ручная проверка Owner**
1. Открыть Tenants и переключить `Active / Archived / All`.
2. Проверить, что archived не появляется в Active списках.
3. Поиск по company/client/branch находит и активные, и архивные в `All`.
4. Переключение компании не ломает client/branch selector.

**Ценность**
- Мгновенная операционная видимость портфеля.
- Убирается текущая путаница при сопровождении подключенных клиентов.

**Риски и митигации**
- Риск: поломка context selection.
- Митигация: contract tests `/me` + e2e for selectors + fail-closed asserts.

---

## PR-2 Lifecycle Actions + Side Effects

**Scope**
- Закрыть lifecycle действия для company/client/branch в едином action-style API.
- Ввести обязательные prechecks/blockers и side-effects policy.
- Добавить bulk lifecycle actions с dry-run + execute + audit.

**DoD**
- Archive/restore невозможен при нарушении prechecks.
- Есть понятный blocker report (agents/memberships/branches/integrations).
- Для bulk есть idempotency и rollback playbook.

**Ручная проверка Owner**
1. Попробовать архивировать активного клиента с активными агентами -> получить блокер.
2. Отключить блокеры и повторить -> archive успешен.
3. Restore возвращает клиента в active.
4. Bulk dry-run показывает список затронутых сущностей до execute.

**Ценность**
- Контролируемые изменения без случайного отключения рабочих клиентов.
- Подготовка к массовым операциям на большом портфеле.

**Риски и митигации**
- Риск: случайный массовый outage.
- Митигация: двухшаговый execute (dry-run + confirmation_id), ограничение batch size, audit trail.

---

## PR-3 Membership/RBAC Admin Completeness

**Scope**
- CRUD memberships (company/client/branch scope).
- Disable/enable/re-scope для агентов.
- Rebind OIDC/Telegram identity с guard against duplicates.

**DoD**
- Platform Admin может менять доступы без SQL.
- Любой change виден в audit.
- Негативные tests на duplicate identity/role escalation.

**Ручная проверка Owner**
1. Создать branch-scoped manager.
2. Переместить его в другой филиал (re-scope).
3. Отключить и убедиться, что вход/доступ пропал.
4. Включить обратно и проверить восстановление доступа.

**Ценность**
- Безопасное управление большим штатом и филиальными аккаунтами.
- Снижение операционных инцидентов доступа.

**Риски и митигации**
- Риск: lockout админов.
- Митигация: protected-admin policy (нельзя отключить последний active owner/platform_admin).

---

## PR-4 Runbook-to-Console Jobs

**Scope**
- Поднять в Console Jobs ключевые операции:
- `sync_client`, `backfill_branch_rag`, расширенный `outbox process`, heal, metrics snapshot.
- Job templates + dry-run + execute + history + artifacts.

**DoD**
- Регулярные ops-действия делаются из Console без ручного запуска скриптов.
- Каждое выполнение оставляет reproducible artifact.
- Ошибки jobs имеют actionable diagnostics.

**Ручная проверка Owner**
1. Запустить dry-run `sync_client` из UI.
2. Выполнить execute и открыть artifacts.
3. Запустить `backfill_branch_rag` dry-run/execute на тестовом филиале.
4. Проверить history и replayability результата.

**Ценность**
- Ускорение и стандартизация операций.
- Снижение bus-factor по OPS-скриптам.

**Риски и митигации**
- Риск: UI-обертка поверх нестабильных скриптов.
- Митигация: строго типизированные job contracts + timeout/retry/cancel + immutable artifacts.

---

## PR-5 Unified Admin Surface + Legacy Consumer Migration

**Scope**
- Миграция consumers с legacy `/admin/*` на `/console/v1/ops/*` и `/console/v1/admin/*`.
- Compatibility matrix для CI/runbooks.
- Legacy endpoints переводятся в explicit compatibility mode/deprecation.

**DoD**
- Все регулярные admin действия Platform выполняются через Console API.
- CI/runbooks используют новый контур или documented compatibility wrappers.
- Legacy surface не содержит уникальной бизнес-критичной write-логики.

**Ручная проверка Owner**
1. Прогнать ключевые runbooks без legacy-specific ручных шагов.
2. Проверить CI health/livecheck после migration.
3. Убедиться, что `/admin/*` не нужен для ежедневных операций.

**Ценность**
- Единая точка управления, ниже риск расхождений и скрытых bypass.
- Готовность к enterprise-аудиту и росту команды.

**Риски и митигации**
- Риск: поломка существующих automation consumers.
- Митигация: phased migration matrix, dual-run период, deprecation window с telemetry.

---

## 5) Program-level риски и митигации

| Риск | Impact | Митигация | Доказательство |
|------|--------|-----------|----------------|
| Split admin surfaces дают разное поведение | Высокий | PR-5 migration matrix + dual-run | parity tests + CI livecheck |
| Массовые операции ломают активных клиентов | Высокий | dry-run + prechecks + confirmation + batch limits | blocker reports + audit events |
| Ошибки RBAC дают лишний доступ | Критичный | membership contract tests + negative auth tests | cross-tenant test matrix |
| Drift сигнал есть, но remediation нет | Средний | PR-4 jobs связаны с drift causes | job artifacts + integration status recovery |
| Коммерческий статус не связан с операциями | Средний | explicit company lifecycle + gates | onboarding/contract status in Console |
| Невозможно доказать стабильность | Высокий | SLO/SLI и evidence pipeline | metrics_daily + livecheck artifacts |

---

## 6) SLO и реалистичная гарантия

Абсолютной гарантии "без багов" нет. Реалистичная гарантия для enterprise-операций:
- `Availability SLO` Console Admin API: >= 99.5%.
- `Correctness SLO` lifecycle/membership actions: >= 99.9% success без rollback.
- `Detection SLO` для integration drift: <= 15 минут до detection.
- `Recovery SLO` для типовых ops jobs: <= 30 минут до recover/rollback.

Это и есть практический ответ на "90% времени стабильной правильной работы":
- цель ставим существенно выше 90% (99.5/99.9),
- и привязываем к измеримым SLI + CI/livecheck + audit evidence.

---

## 7) Ценность по ролям

| Роль | Что получает | Как измеряем |
|------|--------------|--------------|
| Owner (Truffles) | Контроль портфеля, предсказуемые риски, прозрачные операции | incidents/month, time-to-root-cause, migration coverage |
| Platform Admin | Полный operational cockpit без SQL/скриптов | mean time to complete admin task, % tasks from Console |
| Support | Быстрый triage и единый статус клиента/интеграций | time-to-first-diagnosis, reopen rate |
| Client Owner/Admin | Прозрачный lifecycle филиалов и доступов | onboarding lead time, misconfiguration rate |
| Branch Manager | Стабильные каналы и меньше инцидентов из-за настроек | delivery failure rate, handover response SLA |

---

## 8) Evidence-модель для каждого PR

Обязательный пакет evidence:
1. CI run URL + pass/fail matrix.
2. `git diff --stat` + список измененных контрактов/API.
3. OpenAPI diff (если есть API changes).
4. Manual owner check transcript (скрин/шаги/результат).
5. SQL/trace snippets для lifecycle/integration/job side-effects.

Без этого PR не считается завершенным в каноне.

---

## 9) Итог

Архитектурно enterprise-платформа уже возможна: базовые сущности, lifecycle ядро, integrations drift и onboarding-контур есть. Главный разрыв не в "можно/нельзя", а в незавершенном управленческом слое: membership admin completeness, job-операции и migration off legacy.

Программа из 5 PR закрывает этот разрыв без большой перестройки модели данных и без нарушения текущих инвариантов.
