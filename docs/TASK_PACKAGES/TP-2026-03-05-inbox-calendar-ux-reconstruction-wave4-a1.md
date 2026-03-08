# TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE4-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE3-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1

## Название/цель
Довести вкладки `Заявки` и `Записи` до production-grade: снизить queue lag через realtime обновления, ввести наблюдаемую операционную метрику и закрыть rollout/rollback дисциплину для live backend без route mocks.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/hooks/useCaseData.ts`
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/calendar.py`
  - `truffles-api/tests/test_console_audit_api.py`
  - `truffles-api/tests/test_console_analytics.py`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Обновления кейсов и записей выполняются polling-моделью.
  - Нет формального queue-lag SLI/SLO для вкладок `Заявки`/`Записи`.
  - Live e2e без mocks выполняется нерегулярно и не встроен в волновой go/no-go.

## One web search (mandatory before implementation)
- **Query (exact):** `Google SRE alerting on SLOs burn rate best practices`
- **Date/time (local):** `2026-03-05T09:37:36+05:00`
- **Sources opened:**
  - `https://sre.google/workbook/alerting-on-slos/`
  - `https://sre.google/sre-book/service-level-objectives/`
- **Ready solutions found:** прод-устойчивость должна измеряться через SLI/SLO + burn-rate alerts; rollout без наблюдаемого SLO состояния недопустим.
- **Decision (`reuse/integrate/build`):** `integrate` — добавить SLI/SLO и realtime-витрину в текущие вкладки, не создавая отдельный "операционный" продукт.
- **Rejected options:** оставить polling-only модель без измеримого queue lag SLO.
- **Source quality:** high-signal primary source = Google SRE official book/workbook.

## Root cause (mandatory)
- **Symptom:** даже с улучшенным UX при пиковых нагрузках менеджер может видеть устаревший статус кейса/записи и реагировать с задержкой.
- **Minimal reproduction:** параллельные обновления статусов в нескольких диалогах; polling не всегда отображает изменения в целевом интервале.
- **Evidence:** текущий polling-паттерн в `useCaseData.ts`/`CaseList.tsx` и отсутствие queue-lag SLO.
- **Five Whys:**
  1. Почему статус устаревает? Нет push-driven доставки событий.
  2. Почему это не контролируется? Нет SLI/SLO queue lag и ошибок синхронизации.
  3. Почему это влияет на бизнес? Менеджер может отвечать не по актуальному контексту.
  4. Почему риск растет? При увеличении потока polling даёт больше окон рассинхронизации.
  5. Почему нельзя оставить как есть? Это нарушает целевую операционную предсказуемость платформы.
- **Root cause statement:** отсутствует наблюдаемый realtime reliability-контур для case/booking updates на проде.
- **Fix mechanism:** добавить event-driven обновления с fallback, SLI/SLO и обязательный live validation в release gate.

## Reuse-first plan (mandatory)
- **Reuse:** текущие роуты/контракты wave3, существующие e2e сценарии `inspect_case`, текущий dashboard/analytics контур.
- **Integrate:** встроить event stream и lag-metrics в текущие `Заявки/Записи`.
- **Build only if needed:** минимальный transport слой (SSE или эквивалент) + метрики/алерты.

## Invariant
- Не добавлять новые top-level вкладки.
- Не ломать fallback на polling при временной недоступности realtime канала.
- Не отключать deterministic quality gates ради скорости релиза.

## Scope
- Runtime/transport:
  - добавить realtime обновления кейсов/записей (SSE preferred) с idempotent reconnect.
  - оставить polling как controlled fallback с reason_code в meta.
- Observability:
  - добавить SLI: `queue_lag_seconds`, `stale_view_rate`, `case_action_apply_latency`.
  - настроить SLO + burn-rate alerts для операторского контура.
- Release discipline:
  - внедрить обязательный live e2e прогон без Playwright route mocks в go/no-go.
  - описать canary rollout и rollback protocol для wave4 изменений.

## Out of scope
- Полная замена transport стека во всем console-web.
- Переписывание всех исторических e2e наборов.
- Новый мониторинговый продукт вне текущего observability контура.

## Touch-list
- `console-web/src/hooks/useCaseData.ts`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/CaseList.tsx`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/tests/test_console_audit_api.py`
- `truffles-api/tests/test_console_analytics.py`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Plan (1..N)
1. Добавить realtime endpoint/consumer с безопасным reconnect и fallback.
2. Встроить SLI/SLO метрики и alert правила.
3. Обновить UI-хуки для приоритета realtime events над polling.
4. Обновить live e2e сценарий и release gate.
5. Провести canary rollout с go/no-go замерами и rollback rehearsal.

## DoD
- Queue updates видны в UI в пределах целевого SLO-интервала.
- Реaltime имеет наблюдаемый fallback и не ломает существующий polling путь.
- Есть SLI/SLO dashboard и alerting по queue lag/stale view.
- Live e2e без route mocks проходит как обязательный gate.
- Есть документированный canary + rollback сценарий с evidence.

## Checks
- `cd truffles-api && pytest -q tests/test_console_audit_api.py tests/test_console_analytics.py`
- `cd console-web && npm run lint -- --file src/hooks/useCaseData.ts --file src/app/calendar/page.tsx --file src/components/CaseList.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && INSPECT_CASE_USE_MOCKS=0 PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`

## Evidence
- Git diff по touch-list.
- Output checks.
- SLI/SLO snapshot до/после canary.
- Live e2e artifact без route mocks.
- Canary decision log (`go/no-go`) и rollback rehearsal output.

## Release safety (mandatory)
- **Rollout:** canary `1 branch -> 25% branches -> 100%` только при стабильном SLO.
- **Go/no-go:** wave4 checks green + burn-rate alert status normal + live e2e pass.
- **Rollback:** мгновенный возврат на polling-only режим + revert wave4 PR.

## Rollback
- Отключить realtime feature toggle/fallback to polling.
- Revert wave4 PR.
- Подтвердить восстановление по `inspect_case` live run.

## No-go
- Продвижение rollout при SLO breach.
- Удаление polling fallback без подтвержденной устойчивости realtime.
- Merge без live e2e evidence.

## Риски/блокеры
- Нестабильность live стенда для e2e без mocks.
- Риск повышенной сложности дебага при смешанном realtime/polling.
- Риск шумных алертов без калибровки burn-rate порогов.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: монолитность `calendar/page.tsx` и `CaseList.tsx` сохраняется частично.
- `Why not in this block`: приоритет — runtime reliability и прод-контроль, не UI decomposition.
- `Risk if deferred`: стоимость будущих изменений queue UX останется высокой.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md`.
- `Expiry/trigger to stop deferral`: следующий крупный UX change request в календаре.

## Next-block contract (mandatory)
- `Next block objective`: closeout — завершить hardening и декомпозицию UI после стабилизации realtime.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseList.tsx`
- `Blocked-by conditions`: wave4 must pass live e2e + SLO canary evidence.
- `Owner role for closure`: Brain / Top Architect.
