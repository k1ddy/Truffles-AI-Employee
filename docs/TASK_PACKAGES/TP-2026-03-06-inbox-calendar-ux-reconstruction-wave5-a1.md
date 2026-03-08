# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE5-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1

## Название/цель
Перевести `Заявки` с абстрактного SLA в action-driven операторский контракт: менеджер должен видеть не техническое состояние `ok/warning/breached`, а понятное следующее действие и срок этого действия.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/utils/labels.ts`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/components/CaseDetailsPanel.tsx`
  - `console-web/src/types/index.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - `labels.ts` все еще строит SLA по `created_at` через фиксированные пороги `60/120` минут.
  - `CaseConversation.tsx` и `CaseDetailsPanel.tsx` показывают `SLA` text badge вместо action-oriented формулировки.
  - `console.py` строит queue signals из age-threshold и выдает только `sla_status/priority_tier/attention_reason/target_response_at`.
  - В backend уже есть provider-side паттерн `on_track/due_soon/overdue`, но он не применен к case workspace.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk SLA policies due soon overdue pending requester status`
- **Date/time (local):** `2026-03-06T07:00:00+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408829459866-Defining-SLA-policies`
  - `https://support.zendesk.com/hc/en-us/articles/4408836052506-Understanding-how-SLA-policies-are-applied-to-tickets`
  - `https://support.zendesk.com/hc/en-us/articles/4408839203226-Viewing-SLA-targets-and-breaches`
- **Ready solutions found:** operator UI должен показывать `due soon/overdue/pending on requester` как action state; SLA должен быть связан с конкретным дедлайном/паузой, а не с абстрактным цветом.
- **Decision (`reuse/integrate/build`):** `integrate` — добавить case-level action SLA contract в текущий read-model и отрисовывать его в существующих `Заявки` surfaces без новой вкладки.
- **Rejected options:** оставить SLA только как тех-лейбл `ok/warning/breached` или решать SLA copy только на фронтенде без server contract.
- **Source quality:** high-signal primary source = official Zendesk documentation.

## Root cause (mandatory)
- **Symptom:** менеджер видит `SLA: Нужен ответ менеджера` или `В рабочем окне`, но не понимает точное действие и срок.
- **Minimal reproduction:** открыть кейс на вкладке `Заявки`; увидеть верхние бейджи `SLA: ...` и список слева, где SLA строится от возраста кейса, а не от формального next action.
- **Evidence:** `console.py` age-threshold helper, `labels.ts` fixed minute thresholds, `CaseConversation.tsx`/`CaseList.tsx`/`CaseDetailsPanel.tsx` current usage.
- **Five Whys:**
  1. Почему SLA кажется бесполезным? Потому что он описывает внутреннее состояние, а не действие менеджера.
  2. Почему это не исправляется одним UI-текстом? Потому что backend не отдает action contract как часть case read-model.
  3. Почему список и детальная карточка расходятся? Потому что список считает SLA локально по `created_at`, а detail опирается на `sla_status` string.
  4. Почему это влияет на бизнес? Потому что оператор тратит время на интерпретацию UI вместо ответа клиенту.
  5. Почему нельзя отложить? Потому что пользовательский ТЗ прямо называет SLA misleading и без бизнес-ценности.
- **Root cause statement:** отсутствует единый backend-first SLA action contract для case workspace; из-за этого UI вынужден показывать абстрактные и местами локально посчитанные сигналы.
- **Fix mechanism:** ввести action-driven SLA поля в case read-model, затем перевести список, карточку и детали на этот контракт.

## Reuse-first plan (mandatory)
- **Reuse:** текущие `target_response_at`, `priority_tier`, `attention_reason`, provider-side vocabulary `due_soon/overdue`, существующие case surfaces.
- **Integrate:** расширить `ConsoleCase` и `_build_case_queue_signals`, чтобы фронтенд перестал гадать по времени сам.
- **Build only if needed:** новые case SLA fields, минимальные helper/tests, без новой сущности и без полного SLA policy registry rollout в этом блоке.

## Invariant
- Не добавлять новый top-level экран для SLA.
- Не рассчитывать главный SLA indicator только на фронтенде.
- Не ломать существующие queue filters, realtime и navigation between `Заявки/Записи`.
- Не утверждать, что full policy-driven SLA уже реализован; в этом блоке закрывается action contract для operator workspace.

## Scope
- `Part A (mandatory if split; backend-first)`:
  - расширить case queue/read-model action SLA полями.
  - унифицировать backend helper так, чтобы он отдавал action state, action label, deadline и overdue minutes.
  - обновить schema/openapi/tests.
- `Part B (mandatory if split; frontend surfaces)`:
  - убрать абстрактные SLA labels из `CaseConversation`, `CaseList`, `CaseDetailsPanel`.
  - показывать одно главное действие: `Ответить до HH:MM`, `Просрочено на Xm`, `Ожидаем клиента`, либо fallback business copy.
  - синхронизировать inspect-case mocks/assertions.

## Out of scope
- Полноценный SLA policy registry для case workspace.
- `reassign/snooze/reopen/bulk` actions.
- Action macros.
- Full single-workspace layout merge between `Заявки/Записи`.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/utils/labels.ts`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/CaseDetailsPanel.tsx`
- `console-web/src/types/index.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Plan (1..N)
1. Добавить backend helper для case SLA action contract.
2. Расширить `ConsoleCase` schema и response serialization.
3. Зафиксировать helper behavior тестами и OpenAPI contract checks.
4. Перевести ключевые Inbox surfaces на новый action contract.
5. Обновить inspect-case mocks/assertions и выполнить targeted checks.

## DoD
- Case list, case header и details panel больше не показывают абстрактный `SLA: ok/warning/breached` как главный сигнал.
- Главный SLA indicator показывает action-oriented формулировку и использует server contract.
- Backend schema отражает action state и deadline fields.
- Contract tests, frontend lint и targeted inspect-case lane зеленые.
- Если wave5 split нужен, это явно отражено в PR/TP как `Part A` и `Part B`; не допускается неявное смешение частей.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run lint -- --file src/utils/labels.ts --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/CaseDetailsPanel.tsx --file src/types/index.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## Evidence
- Git diff по touch-list.
- Output checks.
- Screenshot of updated Inbox first-screen showing action-driven SLA.
- Session log with wave5 progress/evidence.

## Release safety (mandatory)
- **Rollout:** one bounded PR preferred; if split is required, `Part A` merges first, `Part B` only after green contract checks.
- **Go/no-go:** backend contract tests + openapi check + frontend lint + inspect-case lane pass.
- **Rollback:** revert current PR; frontend falls back to previous labels once API contract is restored.

## Rollback
- `git revert REVISION_SHA`
- Re-run wave5 checks.
- Restore previous session note if block returns to `planned`.

## No-go
- Исправлять SLA только текстами на фронтенде без backend contract.
- Смешивать wave5 с `reassign/snooze/reopen` scope.
- Добавлять больше одного главного SLA indicator на карточке.

## Риски/блокеры
- Неправильная бизнес-интерпретация `resolved_on_time` без полного resolution SLA; этот кейс не закрывается в этом блоке.
- Возможен drift между mocked inspect-case data и новым schema contract.
- Монолитность `console.py` и `CaseList.tsx` повышает стоимость локальных изменений.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: case SLA все еще не будет policy-driven/admin-configurable; wave5 закрывает action contract, а не full registry-managed SLA.
- `Why not in this block`: приоритет — убрать misleading SLA из operator workspace без расползания в admin configuration subsystem.
- `Risk if deferred`: часть SLA логики еще останется fixed-rule, хотя UI уже станет action-driven.
- `Linked follow-up Task Package(s)`: `TBD wave6`, `TBD wave7`, отдельный follow-up для policy-driven inbox SLA при owner approval.
- `Expiry/trigger to stop deferral`: если после wave5 потребуется branch/client-specific SLA behavior, нужен отдельный SLA policy TP, а не точечный hotfix.

## Next-block contract (mandatory)
- `Next block objective`: либо завершить `Part B` wave5, либо открыть wave6 с `reassign/snooze/reopen/bulk` после полного green closeout wave5.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/utils/labels.ts --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/CaseDetailsPanel.tsx`
- `Blocked-by conditions`: backend contract must be stable and inspect-case lane must have updated mocks.
- `Owner role for closure`: Brain / Top Architect.
