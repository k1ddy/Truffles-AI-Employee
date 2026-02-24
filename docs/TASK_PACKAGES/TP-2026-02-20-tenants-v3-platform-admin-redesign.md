# TP-2026-02-20-tenants-v3-platform-admin-redesign

## Название/цель
Довести `/tenants` до реального `platform_admin control tower` для полного цикла управления компаниями:
онбординг -> эксплуатация -> изменения -> вывод/восстановление, без скрытых состояний и с предсказуемым поведением на большом масштабе.

## Revision
- `2026-02-22`: глубокая перепроверка на `main@9b804d69` и фиксация остаточных системных проблем.
- `2026-02-22`: Wave 5/6 hardening — deterministic e2e/a11y lane без skip, auth-setup decoupling, KPI contrast fix.
- `2026-02-23`: recovery update — критерий `tenants/page.tsx <= 1200 LOC` переведен в рекомендательный, обязательный фокус приемки: рабочая ценность `/tenants` (deterministic scope + actionable flow + полная видимость company scope).
- `2026-02-23`: execution update — выполнены Wave 0 + ключевые пункты Wave 1/2: атомарный scope sync (`company/client/branch`), backend/frontend `branch_id` contract для `/admin/branches`, Scenario B3 (e2e), business-copy cleanup в верхних операционных блоках.
- `2026-02-23`: post-merge verification update — PR `#802` merged (`30f30eb6`), CI green; F3 закрыт (cockpit branch slice больше не привязан к первому клиенту), F2 закрыт на UX уровне (single editable context source на `/tenants`), Wave 4 продолжен выносом `fleet attention` и `portfolio companies` в отдельные компоненты.
- `2026-02-23`: execution continuation — Wave 4 decomposition extended (`clients/change-management/decommission/lifecycle-modal` moved to dedicated components), page-filter URL race fixed for Scenario C (`clear filters` deterministic), and Wave 4 perf track started with dedicated tenants latency histogram for `/admin/tenants/portfolio` + `/admin/tenants/company-cockpit` (`console_tenants_endpoint_latency`, label `endpoint`).
- `2026-02-23`: Wave 4 continuation — добавлен read-model cache для fleet-агрегаций (`tenants_fleet_cache` + migration `038`), cache-hit/miss tests, и perf snapshot tool `ops/console_tenants_perf_snapshot.py` с p95 SLO-оценкой по `console_tenants_endpoint_latency`.
- `2026-02-23`: Wave 5/6 continuation — cleaned deep lifecycle/editor copy (`TenantsClientLifecycleModal`, `TenantsClientsPanel`, `tenants/page.tsx`) и формализован rollout policy для `NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER` (shadow -> canary -> full + rollback guardrails).
- `2026-02-23`: post-merge canary evidence — deployed build rechecked (`Build: 93824a4 | 2026-02-23T07:17:01Z`), live `tenants-a11y` fail-closed lane green (`3 passed`), and authenticated perf + runtime metrics snapshots satisfy SLO.
- `2026-02-23`: Wave 4 async refresh continuation — cache-hit near-expiry now triggers background refresh for tenants summary/attention with inflight dedupe guard; attention cache scope includes `limit` to avoid cross-limit cache collisions.
- `2026-02-23`: Wave 4 event-driven continuation — tenant write-path mutations now invalidate `tenants_fleet_cache` (`fleet_summary`/`fleet_attention`) via best-effort nested transaction guard, reducing stale cache windows after provisioning/go-live/integration operations.
- `2026-02-23`: Wave 4 scope-aware invalidation continuation — `tenants_fleet_cache` schema extended with `scope_company_id/scope_client_id` (`migration 039`), summary cache upserts persist scope metadata, and write-path invalidation now targets `scope_company_id IS NULL OR scope_company_id IN (affected company_ids)` instead of full-table cache wipe.
- `2026-02-23`: Wave 4 targeted prewarm continuation — invalidation now queues affected `company_id` scopes for post-commit async summary rebuild (`after_commit` queue + prewarm worker), reducing cold-start for mutated company scopes while preserving fail-open mutation path.
- `2026-02-23`: Wave 4 + CI hardening continuation — post-commit prewarm расширен до `global portfolio` (summary + attention default scope, rate-limited) для снижения cold-start после мутаций, `console-contract-live` исправлен на корректный schemathesis base URL, `console-e2e-live` auth setup защищён от `AggregateError` в login transition.
- `2026-02-24`: Wave 1 contract debt continuation — `company-cockpit` получил `include_branches` (`true` by default), `/tenants` запрашивает cockpit с `include_branches=false` (branches остаются из `/admin/branches`), что убирает дублирующий branch payload/compute в company scope without breaking API compatibility.
- `2026-02-24`: Wave 1/4 continuation — added large-scope `company-cockpit` perf-contract tests (limit/cursor/query propagation + fail-fast on oversized limits), extracted operational KPI compute/rules from `tenants/page.tsx` into `console-web/src/app/tenants/operational-kpi.ts` (`2969 -> 2789` LOC), and refreshed runtime p95/p99 snapshot artifact (`tenants-perf-snapshot-after-merge-20260224.json`) with explicit branch SLO miss evidence.
- `2026-02-24`: Wave 4 branch-path continuation — optimized `/admin/branches` query contract for platform scale (removed large `client_id IN (...)` filter in favor of `Client` join filters by `status/company`, added branch-list indexes in migration `040_add_branches_listing_perf_indexes.sql`, expanded branch contract tests), and rechecked runtime SLO after authenticated load (`branches p95=100ms`, snapshot `status=pass`).
- `2026-02-24`: Clarified decomposition contract semantics — `page.tsx -> orchestration-only` means architectural isolation of data/actions from view composition; it does **not** mean reducing operator control. Functional controls (`create/edit/archive/restore/publish/rollback/context`) remain mandatory and already available.
- `2026-02-24`: Wave 3 decomposition continuation — extracted `useTenantsDataQueries` (React Query orchestration) and `useTenantsActions` (context chain actions) from `tenants/page.tsx`; page size reduced `2789 -> 2487` LOC while preserving current operator workflows.
- `2026-02-24`: Wave 3 decomposition continuation (part 2) — moved intent/KPI navigation handlers (`runActionQueueIntent`, `runKpiAction`, client target navigation) from `tenants/page.tsx` into `useTenantsActions`; page size reduced `2487 -> 2422` LOC.
- `2026-02-24`: Wave 3 decomposition continuation (part 3) — moved quick-create handlers (`handleQuickCreateCompany`, `handleQuickCreateClient`, `handleQuickCreateBranch`) from `tenants/page.tsx` into `useTenantsActions`; page size reduced `2422 -> 2301` LOC.
- `2026-02-24`: Wave 3 decomposition continuation (part 4) — moved company/client save handlers (`handleSaveCompany`, `handleSaveClient`) from `tenants/page.tsx` into `useTenantsActions`; page size reduced `2301 -> 2214` LOC.
- `2026-02-24`: Wave 3 decomposition continuation (part 5) — moved editor bootstrap + lifecycle + branch-change pipelines (`startCompanyEdit/startClientEdit/startBranchEdit`, `open/close/submit lifecycle`, `preview/publish/rollback branch change`) from `tenants/page.tsx` into `useTenantsActions`; page size reduced `2214 -> 1883` LOC.
- `2026-02-24`: Wave 3/4 continuation — extracted scope-derived state into `useTenantsScopeDerivedState` (`context names/maps/filter options`, `tenants/page.tsx: 1883 -> 1723` LOC) and extended post-commit targeted prewarm to include affected-company `fleet_attention` (not only summary) via `_schedule_fleet_attention_prewarm_for_company_ids` with contract tests; runtime perf snapshot refreshed (`tenants-perf-snapshot-after-company-attention-prewarm-20260224.json`, `status=pass`).
- `2026-02-24`: Wave 3/4 continuation (part 2) — extracted remaining lifecycle/branch patch/format helpers from `tenants/page.tsx` into `tenants-page-helpers.ts` (`1723 -> 1376` LOC), and extended incremental prewarm to event metadata queue (`_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY`) consumed in `after_commit` (summary+attention+global schedule) with rollback cleanup + contract tests; post-merge verification confirms PR `#810` merged with green CI run `22335329574`.
- `2026-02-24`: Wave 3/4 continuation (part 3) — extracted action-queue orchestration from `tenants/page.tsx` into `use-tenants-action-queue.ts` (`1376 -> 1268` LOC), introduced coalesced post-commit prewarm dispatch queue (`_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX`, `_TENANTS_FLEET_PREWARM_DISPATCH_BATCH_MAX`) to batch company/global rebuild scheduling, and hardened runtime perf gate with required minimum samples (`portfolio/company_cockpit/branches`) plus authenticated load snapshot evidence (`tenants-perf-snapshot-after-dispatch-load-20260224.json`, `status=pass`).
- `2026-02-24`: Wave 3/4 continuation (part 4) — extracted operational KPI/alert/report computations from `tenants/page.tsx` into `use-tenants-operational-model.ts` (`1268 -> 1167` LOC), switched incremental prewarm dispatch from in-memory queue to durable DB-backed queue (`tenants_fleet_prewarm_jobs`, migration `041`) with processing auto-heal timeout + retry/completion markers, and added reproducible authenticated long-run perf lane (`ops/console_tenants_perf_long_run.py`) with green runtime artifact (`tenants-perf-long-run-20260224.json`, `status=pass`).
- `2026-02-24`: Wave 3/4/5 continuation (part 5) — extracted report/snapshot/ops actions into `use-tenants-page-operations.ts` (`tenants/page.tsx: 1167 -> 1064` LOC), introduced materialized fleet projection model (`tenants_fleet_client_projection`, migration `042`) with read-path fallback loader + background compaction/backpressure, and added deterministic business-copy e2e guard (`platform-admin.spec.ts`: no raw `TENANTS_V3_CONTROL_TOWER`/`trace_id`/`slug =`/`telegram_chat_id` markers on `/tenants`).
- `2026-02-24`: Wave 4/3 continuation (part 6) — added projection observability metrics + threshold gates (`coverage/fallback/freshness`) in `ops/console_tenants_perf_snapshot.py`/`ops/console_tenants_perf_long_run.py` backed by runtime metrics (`console_tenants_fleet_projection_last_*`), and extracted residual page orchestration glue (`reportValidation/reportProvisioning/refresh/audit`) into `use-tenants-page-orchestration.ts` to reduce `/tenants` compose complexity.
- `2026-02-24`: Wave 4 continuation (part 7) — added scheduled projection maintenance compaction (`_maybe_run_fleet_projection_maintenance`) wired into summary/attention refresh workers and prewarm dispatch worker, plus persistence observability metrics (`console_tenants_fleet_projection_compaction_*`) and contract tests for stale-row delete + interval throttling.
- `2026-02-24`: Wave 4 continuation (part 8) — enabled bounded request/cache-miss projection persist (`TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED`, `TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS`) in `list_clients` + `fleet_attention` + summary cache-miss path to reduce repeated request-time fallback compute while keeping response correctness.
- `2026-02-24`: Wave 4 continuation (part 9) — added fallback-triggered projection self-healing prewarm (`TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_*`): when request path falls back to compute and not all clients are persisted synchronously, company scopes are enqueued to durable incremental prewarm dispatch with per-company throttle, reducing repeated fallback on sustained large-scope reads.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP по Tenants/Platform Admin)
- `STRUCTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `SPECS/CONTROL_PLANE.md`
- `TECH.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`

## Product intent (смысл вкладки)
`/tenants` должен быть единой рабочей точкой для platform_admin:
1. Видеть портфель компаний/клиентов/филиалов и их состояние.
2. Быстро определять риск и следующий шаг по каждой единице управления.
3. Выполнять действия безопасно, с audit/evidence.
4. Масштабироваться до очень большого количества компаний и ниш без деградации UX и latency.

## Execution status (FACT, по текущему коду)
| Wave | Статус | Что подтверждено | Что не закрыто |
|---|---|---|---|
| Wave 1 API contract alignment | `done` | `branch_id` добавлен в `/admin/branches` + frontend pass-through + e2e Scenario B3; `company-cockpit` при `client_id=null` теперь остаётся в company scope; `include_branches=false` устраняет дубли branch payload в `/tenants` cockpit read path; large-scope contract tests добавлены (`truffles-api/tests/test_console_tenants_list.py`: `test_get_tenants_company_cockpit_passes_large_scope_pagination_contract`, `test_get_tenants_company_cockpit_rejects_oversized_limits_before_subqueries`) | Нет блокеров по API contract; дальнейшая работа смещена в Wave 4 runtime perf/read-model |
| Wave 2 Context kernel | `done` | Атомарный sync `company/client/branch`, orphan-branch guard, стабильные B/C/D + отключён конфликтующий header-edit контекста на `/tenants` (`context-managed-in-tenants`) (`console-web/src/app/tenants/page.tsx`, `console-web/src/components/ConsoleShell.tsx`, `console-web/e2e/platform-admin.spec.ts`) | Нет блокеров |
| Wave 3 Data contract | `done/partial` | Typed weekly snapshot schema + table/fallback (`truffles-api/app/schemas/console.py:249`, `truffles-api/app/routers/console.py:13434`); в `/tenants` добавлены decomposition hooks `useTenantsDataQueries`, `useTenantsActions`, `useTenantsScopeDerivedState`, `useTenantsActionQueue`, `useTenantsOperationalModel`, `useTenantsPageOperations`, `useTenantsPageOrchestration`, helper module `tenants-page-helpers.ts` (lifecycle audit / branch patch / formatters), `tenants/page.tsx` reduced `1883 -> 1064` | Для полного orchestration-only всё ещё остаются compose wiring и render orchestration в `page.tsx`; функциональный контроль оператора сохранён |
| Wave 4 Decomposition/perf | `done/partial` | Вынесены `OperationalKpi`, `FleetAttention`, `PortfolioCompanies`, `Clients`, `ChangeManagement`, `Decommission`, `ClientLifecycleModal` секции; page-filter race для Scenario C устранён в `use-tenants-page-filters.ts`; backend perf-track запущен через `console_tenants_endpoint_latency{endpoint=portfolio|company_cockpit}` + router instrumentation; внедрён read-model cache (`migration 038`) + async near-expiry refresh + scope-aware invalidation (`migration 039`) + durable prewarm queue (`migration 041`); добавлен materialized fleet projection layer (`tenants_fleet_client_projection`, `migration 042`) с fallback loader на compute path и scope compaction/backpressure; `/admin/branches` hot path переведён на `Client` join scope filtering + perf indexes (`migration 040`) с расширенными contract tests; perf snapshot gate дополнен minimum sample-size checks и projection observability gates (`coverage/fallback/freshness`) + long-run authenticated lane (`ops/console_tenants_perf_long_run.py`); scheduled projection maintenance compaction + compaction persistence metrics (`console_tenants_fleet_projection_compaction_*`) добавлены и покрыты тестами; request/cache-miss path materializes bounded fallback details в projection (`TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_*`) и fallback-triggered durable prewarm self-healing включён (`TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_*`) | Для 10M+ флота остаётся снизить fallback share дальше (в сторону fully async/offline materialization) и подтвердить это runtime метриками under sustained large-scope load |
| Wave 5 A11y/copy | `done/partial` | `A11Y_FAIL_ON_THRESHOLDS=1` проходит в deterministic lane (desktop/mobile), KPI contrast исправлен, business-copy упрощён в `TopControls`/`ActionQueue`/`Fleet`/`Company edit`, lifecycle audit очищен от raw `trace_id`, branch change copy переведён в business wording, добавлен e2e контракт на отсутствие raw technical markers в `/tenants` | Тех-термины допускаются только в целевых security/debug действиях (например sensitive-ID reveal), но не в основном операторском потоке |
| Wave 6 E2E realism | `done` | `platform-admin.spec.ts` стабилизирован: deterministic auth/session, нет `test.skip`, сценарии A/B/C/D/E hard-fail (`console-web/e2e/platform-admin.spec.ts`, `console-web/playwright.config.ts`) | Нет |
| Feature flag rollout | `done` | `NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER` в коде (`console-web/src/app/tenants/page.tsx:850`), rollout policy формализован (`shadow -> canary -> full` + rollback), post-merge canary evidence зафиксирован: live build stamp, live a11y green, runtime SLO snapshot pass | Нет блокеров |

## Critical problems (FACT, deep check)
### F1 (closed). Branch scope drift после `Взять из рабочего контура`
Evidence:
- `setBranchContextAndPageFilters` валидирует и применяет полную chain `company+client+branch` через `validateScopeForBranchActions` (`console-web/src/app/tenants/page.tsx`).
- `applyContextToPageFilters` валидирует scope перед apply и синхронизирует storage только при нормализованном различии (`console-web/src/app/tenants/page.tsx`).
- `ConsoleShell` сохраняет `stored.branchId`, если `/me` не прислал конкретный `selected_branch_id`, что устраняет silent wipe (`console-web/src/components/ConsoleShell.tsx`).
Impact:
- branch/page scope больше не сбрасывается молча при неполном `/me` контексте.
- действия `В контекст`/`Взять из рабочего контура` детерминированы в сценариях B/B2/B3.

### F2 (closed). Конфликт источников истины для контекста на `/tenants`
Evidence:
- На маршруте `/tenants` header больше не даёт editable context controls: вместо них показывается явное сообщение `context-managed-in-tenants` (`console-web/src/components/ConsoleShell.tsx`).
- Единая editable точка контекста для `/tenants` оставлена в page-level блоке `Рабочий контур` (`console-web/src/components/TenantsTopControls.tsx`).
Impact:
- Для `/tenants` устранена конкуренция контекст-контролов между header и страницей.
- Снижен риск ошибочного изменения scope из двух UI-источников.

### F3 (closed). Branch list contract в company scope
Evidence:
- `company-cockpit` передаёт `client_id` только если он явно выбран; при `client_id=null` работает company scope (`truffles-api/app/routers/console.py`).
- `company-cockpit` поддерживает `include_branches=false`; `/tenants` использует этот режим и не тянет дублирующий branches payload из cockpit (`truffles-api/app/routers/console.py`, `console-web/src/app/tenants/page.tsx`).
- Основной branch list в `/tenants` работает через `/admin/branches` с явными `company_id/client_id/branch_id` фильтрами и e2e контрактом B3 (`console-web/src/app/tenants/page.tsx`, `console-web/e2e/platform-admin.spec.ts`).
Impact:
- Ложный branch-slice "только первый клиент" больше не воспроизводится в текущем контракте `/tenants`.
- Убран лишний branch payload/compute из cockpit request path в company scope.
- Остаточная задача — perf/read-model для очень больших портфелей (`F5`).

### F4. Монолит страницы сохраняется (умеренный regression risk)
Evidence:
- `console-web/src/app/tenants/page.tsx` = ~1064 LOC (после выделения `useTenantsDataQueries` + `useTenantsActions` + `useTenantsScopeDerivedState` + `useTenantsActionQueue` + `useTenantsOperationalModel` + `useTenantsPageOperations` + `useTenantsPageOrchestration` + `tenants-page-helpers.ts`), но всё ещё частичный оркестрационный монолит.
- Query/context/intent/quick-create/company-client-save/editor bootstrap/lifecycle/branch-change + scope-derived names/maps/options + action-queue + operational KPI/alert/report/snapshot model вынесены в hooks (`console-web/src/app/tenants/use-tenants-data-queries.ts`, `console-web/src/app/tenants/use-tenants-actions.ts`, `console-web/src/app/tenants/use-tenants-scope-derived-state.ts`, `console-web/src/app/tenants/use-tenants-action-queue.ts`, `console-web/src/app/tenants/use-tenants-operational-model.ts`, `console-web/src/app/tenants/use-tenants-page-operations.ts`, `console-web/src/app/tenants/use-tenants-page-orchestration.ts`), helper/formatting и audit pipelines вынесены в `console-web/src/app/tenants/tenants-page-helpers.ts`; в странице остаются compose wiring и UI orchestration.
Impact:
- любое изменение цепляет много сценариев.
- сложнее изолировать баги и удерживать инварианты.
- это архитектурный риск сопровождения, а не потеря operator control: текущий UI уже даёт полный рабочий контур действий.

### F5. Серверные fleet-агрегации требуют дальнейшего масштабного precompute (частично закрыто)
Evidence:
- `_build_fleet_client_details_map` грузит branches для набора клиентов и считает агрегаты в Python (`truffles-api/app/routers/console.py:3281`).
- `_build_fleet_summary_for_scope` сканирует батчами клиентов и на каждый батч строит heavy details (`truffles-api/app/routers/console.py:3623`).
- `list_fleet_attention` проходит по всем active clients в scope и пересчитывает сигналы (`truffles-api/app/routers/console.py:15061`).
- Добавлен read-model cache `tenants_fleet_cache` с TTL и reuse в `list_clients(include_summary)` + `list_fleet_attention` (`truffles-api/migrations/038_add_tenants_fleet_cache.sql`, `truffles-api/app/routers/console.py`).
- Добавлен async cache refresh near-expiry на cache-hit с inflight-guard (`_schedule_fleet_summary_async_refresh`, `_schedule_fleet_attention_async_refresh`) для сдвига тяжелого precompute из hot request path (`truffles-api/app/routers/console.py`).
- Добавлен event-driven invalidation cache на mutation path (`_invalidate_tenants_fleet_cache_scope`) для `update_company/create|update|archive|restore_client`, `create|update_branch`, `branch go-live approve/reject/waive`, `integration_reconcile/provider_ops execute` (`truffles-api/app/routers/console.py`), с контрактными тестами в `truffles-api/tests/test_console_admin_provisioning.py`.
- Добавлен scope metadata contract (`scope_company_id/scope_client_id`) в cache table/model (`truffles-api/migrations/039_add_tenants_fleet_cache_scope_columns.sql`, `truffles-api/app/models/tenants_fleet_cache.py`) и scope-aware delete (`global + affected companies`) вместо полного wipe.
- Добавлен post-commit prewarm contract для affected company scopes: invalidation складывает `company_ids` в session queue, `after_commit` запускает async summary + attention rebuild workers (`_schedule_fleet_summary_prewarm_for_company_ids`, `_schedule_fleet_attention_prewarm_for_company_ids`) с inflight dedupe и scope keys на company active-client slice.
- Добавлен post-commit global prewarm contract: invalidation ставит `global prewarm` флаг, а `after_commit` запускает rate-limited async prewarm default portfolio cache (`fleet_summary` + `fleet_attention`) для active-client global scope.
- Добавлен incremental event metadata queue (`_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY`): invalidation path теперь пишет структурированные события (`reason + company_ids`), а `after_commit` строит scheduling summary/attention/global из event list и очищает legacy keys; `after_rollback` очищает event queue.
- Добавлен dispatch/coalescing слой для incremental prewarm: `after_commit` теперь enqueue-события в dispatch queue и worker коалесит батч (company_ids + global flag) до scheduler вызовов, чтобы снизить burst-шторм scheduling в write-heavy сценариях.
- Dispatch queue сделана durable: prewarm задачи пишутся в `tenants_fleet_prewarm_jobs` (migration `041`) и обрабатываются worker'ом через `pending -> processing -> done` с auto-heal stuck processing timeout и retry marker, что переживает процессные рестарты.
- Добавлен материализованный projection layer `tenants_fleet_client_projection` (migration `042`) с контуром `load_or_build`: read path сначала использует projection rows, а отсутствующие/устаревшие клиенты пересчитываются fallback-ом и могут быть добиты в projection в background контуре.
- Для company scope добавлен compaction guard (`keep_client_ids` + max threshold), чтобы удалять устаревшие projection rows без full-table операций.
- Добавлены runtime observability metrics для projection read-path: `console_tenants_fleet_projection_last_coverage_ratio`, `console_tenants_fleet_projection_last_fallback_ratio`, `console_tenants_fleet_projection_last_freshness_lag_seconds` + source counters.
- Perf gate расширен в `ops/console_tenants_perf_snapshot.py`: теперь контролируются не только latency/sample-size, но и projection gates (min coverage, max fallback, max freshness lag), с прокидкой в long-run lane (`ops/console_tenants_perf_long_run.py`).
- Perf snapshot gate усилен minimum sample-size контрактом (`portfolio >= 20`, `company_cockpit >= 20`, `branches >= 50/80` по run параметрам): low-sample snapshots больше не считаются валидными для SLO вывода.
- Добавлен reproducible long-run authenticated lane `ops/console_tenants_perf_long_run.py` (load profile + snapshot gate) с runtime evidence `tenants-perf-long-run-20260224.json` (`status=pass`, samples `portfolio=112`, `company_cockpit=111`, `branches=144`).
Impact:
- request-time нагрузка снижена за счёт cache-hit path.
- stale-window после admin мутаций снижен (invalidate сразу после write path), при этом нагрузка на другие company scopes снижена за счёт scope-aware delete.
- на read path часть fleet details теперь обслуживается из materialized rows, что уменьшает количество пересчётов в hot path и подготавливает переход к fully precomputed модели.
- cold-start после мутаций снижен для affected company scope и default global portfolio scope за счёт post-commit prewarm вместо первого "дорогого" запроса пользователя.
- для очень большого флота остаётся шаг до fully materialized precompute (prewarm уже durable, long-run SLO gate уже валиден).

### F6. A11y debt: контраст KPI карточек
Evidence:
- KPI-карточки переведены на статусные high-contrast labels (`kpiLabelClass`) вместо `text-muted-foreground` на tint background (`console-web/src/components/TenantsOperationalKpiPanel.tsx`).
- Локальный fail-closed a11y lane зелёный (`A11Y_FAIL_ON_THRESHOLDS=1`), artifacts обновлены (`docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-*-axe.json`).
Impact:
- Локальный fail-closed a11y gate закрыт.
- Runtime recheck после deploy закрыт: live lane `3 passed`, artifacts обновлены.

### F7. Смешение бизнес и технического copy (основной поток закрыт)
Evidence:
- Business-copy упрощён в `Action Queue` -> `Приоритетные задачи` (`console-web/src/components/TenantsActionQueuePanel.tsx`).
- KPI/alert copy очищен от тех-формулировок (`console-web/src/components/TenantsOperationalKpiPanel.tsx`).
- Fleet/Company секции переведены на business wording (`console-web/src/components/TenantsFleetAttentionPanel.tsx`, `console-web/src/components/TenantsPortfolioCompaniesPanel.tsx`).
- Deep lifecycle/editor copy очищен (`console-web/src/components/TenantsClientLifecycleModal.tsx`, `console-web/src/components/TenantsClientsPanel.tsx`, `console-web/src/app/tenants/page.tsx`).
Impact:
- Mainline операторский поток очищен от тех-шума.
- Остаточный тех-copy допускается только в platform preset/debug контексте.

### F8. E2E-контур не является жесткой страховкой от регрессий
Evidence:
- `platform-admin.spec.ts` работает в deterministic lane (`E2E_DETERMINISTIC_AUTH=1`) и проходит `14/14` без `test.skip`.
- `tenants-a11y.spec.ts` переведён на deterministic mocks + жёсткий `expect(tenantsAvailable).toBe(true)` вместо `test.skip`.
Impact:
- Контур стал воспроизводимым и fail-closed.
- Остаточный риск: warnings окружения (`NO_COLOR/FORCE_COLOR`, npm env warning) не влияют на pass/fail, но требуют отдельной hygiene-задачи.

## Root-cause map
1. Нет единой state machine для `global context` и `page filters`.
2. API `company-cockpit` требует cleanup/read-model hardening для больших объёмов, но блокирующий F3 bug закрыт.
3. Fleet аналитика рассчитывается синхронно "на лету" вместо read-model/предагрегации.
4. Страница остается orchestration-монолитом.
5. Тестовый контур допускает "soft skip", а не контрактную проверку.

## Invariant
1. Никакой скрытой фильтрации: пользователь всегда понимает, почему видит именно этот список.
2. Любое действие `platform_admin` имеет предсказуемую область (`company/client/branch`) и audit след.
3. Для `/tenants` источник фильтрации данных только явный `page filters` (query state), не implicit header drift.
4. Масштабирование не ломает UX: list/portfolio/cockpit работают курсорно и воспроизводимо.

## Scope
### In scope
1. Полный довод `Tenants V3` под `platform_admin`.
2. Исправление state drift между context и page filters.
3. Ревизия API контрактов для branches/cockpit/fleet summary под масштаб.
4. Завершение decomposition `tenants/page.tsx`.
5. Жесткие e2e + a11y + perf quality gates.

### Out of scope
1. Редизайн страниц owner/admin/manager вне `platform_admin`.
2. Изменение runtime LLM/core behavior.
3. Переписывание всей Console с нуля.
4. Жесткий LOC-лимит для `tenants/page.tsx` как самостоятельный gate.

## Recovery priority (2026-02-23)
1. P0: Убрать state-drift и silent reset (`company/client/branch`) — вкладка должна перестать "самопереключаться".
2. P0: Сделать действия на вкладке утилитарными:
- "В контекст",
- "Взять из рабочего контура",
- переходы в `Company Workspace` / `Integrations` / `Cases`.
3. P0: Зафиксировать контракт тестами A/B/C/D/E без skip.
4. P1: Упростить copy и убрать тех-шум из business режима.

## Scope state contract (single source of truth)
### Контуры
1. `Global context`:
- хранится в `localStorage` (`console:company_id/client_id/branch_id`).
- используется для межстраничной навигации и заголовков API.
2. `Page filters` (`/tenants`):
- хранится только в URL query (`company_id/client_id/branch_id`).
- определяет выборки таблиц и карточек Tenants.

### Приоритет
1. Данные `/tenants` читаются только из `page filters`.
2. `Global context` на `/tenants` не фильтрует списки "тихо".
3. `Взять из рабочего контура` = явный одноразовый sync из `global context` в `page filters`.

### Правило атомарности
1. `branch` нельзя устанавливать без согласованного `client/company` chain.
2. Если выбран branch, система должна либо:
- иметь валидную цепочку `company_id + client_id + branch_id`, либо
- отклонять действие с понятным сообщением, а не молча сбрасывать state.

## Control behavior matrix (целевой контракт)
| Контрол | Где | Меняет `global context` | Меняет `page filters` | Контракт |
|---|---|---|---|---|
| `В контекст` (client row) | Clients | Да | Да | `company+client` синхронизированы |
| `В контекст` (branch row) | Branches | Да | Да | `company+client+branch` синхронизированы |
| `Взять из рабочего контура` | Filters | Нет | Да | query получает полный валидный scope |
| `Сбросить фильтры` | Filters | Нет | Да | query очищен, global context сохранен |
| `Сбросить контур` | Context | Да | Нет | storage очищен, query не трогаем |

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/app/tenants/use-tenants-page-filters.ts`
- `console-web/src/components/TenantsTopControls.tsx`
- `console-web/src/components/TenantsOperationalKpiPanel.tsx`
- `console-web/src/components/TenantsActionQueuePanel.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/console-context-storage.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/e2e/tenants-a11y.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_tenants_*.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/REPORTS/2026-02-20-tenants-v3-redesign-plan.md`

## Plan (full implementation waves)
### Wave 0. Stop regression and state determinism (P0)
1. Fix `branch apply` drift:
- `setBranchContextAndPageFilters` должен писать полную chain (`company/client/branch`) на основе branch row.
- `applyContextToPageFilters` должен валидировать scope перед применением.
2. Убрать auto-wipe branch в `ConsoleShell` при `selected_branch_id = null`, если branch не требует принудительного выбора.
3. Внедрить unit+e2e state-machine тесты на A/B/C/D сценарии.
Expected result:
- кнопки и синхронизация работают предсказуемо, без silent reset.

### Wave 1. API contract alignment for portfolio scale (P0)
1. Расширить branches API:
- добавить server filter `branch_id` и `company_id` (без client lock-in).
2. Исправить cockpit contract:
- branch list не должен ограничиваться первым клиентом по умолчанию в портфельном сценарии.
3. В UI включить cursor pagination для всех server-contract веток (включая cockpit).
Expected result:
- список филиалов полный и управляемый на больших клиентах/компаниях.

### Wave 2. IA/UX simplification for platform_admin (P1)
1. Оставить один ясный сценарий:
- верх: `Фильтры страницы`;
- отдельный компактный блок: `Рабочий контур` только как cross-page state.
2. Удалить debug copy из business режима:
- `page filter client_id`, `Threshold drill-down`, `Action Queue` (заменить на RU business labels).
3. Убрать дублирующую информацию, которая не влияет на действие.
Expected result:
- оператор за 3 шага понимает "где я / что вижу / что делать дальше".

### Wave 3. Decomposition completion (P1)
1. Выделить остаточные секции в компоненты + hooks:
- `TenantsFleetAttentionPanel`
- `TenantsPortfolioCompaniesPanel`
- `TenantsClientsPanel`
- `TenantsChangeManagementPanel`
- `TenantsDecommissionPanel`
- `useTenantsDataQueries`
- `useTenantsActions`
2. Оставить `page.tsx` только orchestrator/composition.
Expected result:
- снижение regression surface, ускорение последующих итераций.

### Wave 4. Fleet read-model and performance hardening (P0 for 10M+)
1. Ввести read-model для портфеля:
- предагрегированные counters/scores по client/company (background refresh + incremental updates).
2. Перевести тяжелые вычисления fleet attention/summary из request-time в precompute.
3. Добавить индексы и verify планы запросов для `clients/branches/audit/outbox`.
4. Зафиксировать SLO:
- `/admin/tenants/portfolio` p95 < 1200ms (fleet slice),
- `/admin/tenants/company-cockpit` p95 < 1000ms,
- branch list page switch p95 < 800ms.
Expected result:
- управление не деградирует с ростом числа компаний и ниш.

### Wave 5. Quality gates hard close (P0)
1. A11y:
- устранить `critical/serious` (контраст KPI, focus, semantics).
2. E2E:
- убрать skip-зависимость от случайного контекста;
- сделать seed lane с фиксированными tenant fixtures.
3. Ввести обязательные contract checks для scenario A/B/C/D/E.
Expected result:
- зеленые и воспроизводимые проверки перед merge/release.

### Wave 6. Controlled rollout and guardrails (P1)
1. Добавить feature flag:
- `TENANTS_V3_CONTROL_TOWER`.
2. Rollout policy:
- shadow mode -> canary -> full.
3. Добавить dashboard наблюдения:
- state-drift incidents,
- cockpit pagination errors,
- a11y gate status,
- e2e scenario pass-rate.
Expected result:
- релиз контролируемый, откат предсказуемый.

## DoD (полный)
1. Scenario A/B/C/D/E проходят детерминированно без skip.
2. `branch` после `В контекст` + `Взять из рабочего контура` не теряется.
3. В `Tenants` нет технического copy в business режиме.
4. `/tenants` даёт операционную пользу: platform_admin может за <= 3 действия выбрать scope и перейти к следующему рабочему шагу без скрытых фильтров.
5. `portfolio/cockpit/branches` поддерживают курсорный скролл без "первого клиента" ловушки.
6. A11y: `critical=0`, `serious=0` для desktop/mobile.
7. Perf SLO выполняются на тестовом профиле крупного флота.
8. Feature flag rollout + rollback документированы и проверены.

## Checks
- `corepack pnpm -C console-web run lint`
- `corepack pnpm -C console-web run build`
- `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 corepack pnpm -C console-web exec playwright test e2e/platform-admin.spec.ts --project=chromium --workers=1`
- `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 A11Y_FAIL_ON_THRESHOLDS=1 corepack pnpm -C console-web exec playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1`
- `PLAYWRIGHT_BASE_URL=https://console.truffles.kz PLAYWRIGHT_WEB_SERVER=0 E2E_DETERMINISTIC_AUTH=0 E2E_USERNAME=admin E2E_PASSWORD=admin A11Y_FAIL_ON_THRESHOLDS=1 corepack pnpm -C console-web exec playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=line`
- `python3 ops/console_tenants_perf_snapshot.py --metrics-url https://api.truffles.kz/metrics --pretty --output /tmp/tenants_perf_snapshot_20260223_after_authload.json`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `pytest -q truffles-api/tests/test_console_tenants_list.py` (includes weekly-snapshot contract tests)
- `pytest -q truffles-api/tests/test_console_fleet_attention.py`
- `scripts/session_check.sh`

## Evidence
1. UI before/after screenshots:
- filters/context behavior,
- cockpit branches pagination,
- mode transitions,
- updated a11y artifacts: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop.png`, `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile.png`.
2. API evidence:
- openapi diff,
- sample requests/responses for portfolio/cockpit/branches.
3. Quality evidence:
- e2e logs по A/B/C/D/E (`14 passed`),
- axe JSON desktop/mobile (`critical=0`, `serious=0`),
- perf summary with p95,
- live canary artifacts:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-authenticated-perf-baseline-20260223.json`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-perf-snapshot-after-authload-20260223.json`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-live-build-20260223.json`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-runtime-health-20260223.json`.
4. State evidence:
- `localStorage scope` vs `query filters` trace before/after critical actions.

## Rollback
1. `TENANTS_V3_CONTROL_TOWER=0` возвращает предыдущий UI path.
2. API backward compatibility сохраняется минимум 1 release cycle.
3. Read-model fallback:
- при деградации precompute использовать текущий on-demand path временно.

## No-go
1. Нельзя мерджить с `test.skip` в ключевых сценариях A/B/C/D/E.
2. Нельзя оставлять mixed business/technical copy в default platform_admin UX.
3. Нельзя принимать release при `axe critical/serious > 0`.
4. Нельзя оставлять branch-list зависимым от "первого клиента" при company scope.
5. Нельзя считать масштабные fleet-агрегации только в request-time при целевом росте.

## Риски/блокеры
1. Большой blast radius у `tenants/page.tsx` и `console.py`.
2. Возможен drift контрактов при параллельной работе над API.
3. Риск скрытых state-регрессий при изменениях `ConsoleShell`/storage sync.
4. Риск ложного green без seed lane и hard-fail e2e/a11y.

## Worktree/branch policy
- Branch: `feat/2026-02-21-tenants-v3-ux-contract-a250`
- Worktree: `/home/zhan/worktrees/2026-02-21-tenants-v3-ux-contract-a250`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после полного закрытия waves
