# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-PARTB-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1

## Название/цель
Подключить action-macros к реальному операторскому UI: менеджер должен видеть, что именно сделает макрос, сохранить/редактировать это в форме и применять макрос к открытой заявке без ручного дублирования действий.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/InboxMacros.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseView.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSION_INDEX.md`
- `Baseline findings`:
  - `InboxMacros.tsx` умеет только выбрать `body` и вставить текст в draft; action contract из Wave7 Part A ещё не используется.
  - Form state для макросов хранит только `scope/label/body`, поэтому action-macro нельзя ни создать, ни отредактировать из UI.
  - `inboxApi` уже знает `list/create/update`, но не знает `executeMacro`.
  - `CaseView` и `InboxView` уже подают branch context в `InboxMacroChips`, значит можно добавить case-scoped apply flow без новой top-level IA.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk macros compose reply agent workspace official documentation`
- **Date/time (local):** `2026-03-06T10:09:17+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4410326550554-Enabling-agents-to-use-quick-reply-and-macro-shortcuts-in-tickets`
  - `https://support.zendesk.com/hc/en-us/articles/4408829341978-Why-isnt-macro-available-for-plain-text-comments`
- **Ready solutions found:** mature helpdesk UX keeps macros directly in the reply workspace, makes keyboard/apply access obvious, and ties availability to an explicit compose surface instead of hidden background automation.
- **Decision (`reuse/integrate/build`):** `integrate` — расширить текущий `InboxMacros` как один compose-side control: action builder в manage mode + execute/apply semantics в use mode.
- **Rejected options:** отдельный modal wizard для macro apply; silent auto-action без явного UI hint; новый самостоятельный macros screen.
- **Source quality:** high-signal primary sources = official Zendesk support docs.

## Root cause (mandatory)
- **Symptom:** backend уже умеет хранить и исполнять action-macros, но менеджер в UI продолжает видеть только текстовые быстрые ответы.
- **Minimal reproduction:** открыть заявку, перейти в `Все ответы`, попытаться создать макрос `Закрыть заявку + ответ`; интерфейс не даёт выбрать действие, а existing chips только подставляют текст.
- **Evidence:** current `InboxMacros.tsx` form/use cards use `label/body` only; `api-client.ts` lacks execute method; no e2e asserts for action-macro UI.
- **Five Whys:**
  1. Почему action-macro не даёт UX value? Потому что его нельзя настроить и применить из интерфейса.
  2. Почему менеджер продолжает делать лишние клики? Потому что макрос и case action остаются разными потоками.
  3. Почему нельзя просто auto-run action в фоне? Потому что менеджер должен видеть, какое действие выполнится, и понимать бизнес-эффект.
  4. Почему не нужен новый экран? Потому что macro use/manage уже живут рядом с composer, и это правильная operator surface.
  5. Почему нужен bounded Part B? Потому что надо подключить только create/edit/apply flow, не расширяя scope до advanced previews, undo и новых action types.
- **Root cause statement:** UI слой не использует backend action-macro contract, поэтому macro flow остаётся текстовым и не сокращает операторский цикл.
- **Fix mechanism:** добавить form fields для optional action config, явные action hints в macro cards и case-scoped execute/apply flow поверх текущего composer-side control.

## Reuse-first plan (mandatory)
- **Reuse:** `InboxMacros` panel/use/manage layout, existing query/mutation cache flow, Wave7 Part A `execute` endpoint, existing case/cases query invalidation pattern.
- **Integrate:** добавить action config в существующую форму и use cards, не создавая новый route.
- **Build only if needed:** новый `executeMacro` API method и local UI helpers for action labels/hints.

## Invariant
- Не ломать text-only macros.
- Не отправлять сообщение автоматически при применении macro action.
- Не выполнять action silently: у карточки и формы должен быть понятный action label/hint.
- Не открывать новый экран или modal-only flow для макросов.

## Scope
- `Part B (this TP)`:
  - добавить action builder в manage form (`none/take/resolve/return/reopen/snooze`);
  - показать action badge/hint в use/manage cards;
  - подключить `executeMacro` при применении action-macro к открытому кейсу;
  - после успешного action сохранить body как draft и обновить case queue/detail;
  - закрыть детерминированным e2e mock lane.

## Out of scope
- Новые action types beyond Wave7 Part A.
- Auto-send message after macro apply.
- Undo history, audit timeline UI, advanced preview modal.
- New standalone macros page.

## Touch-list
- `console-web/src/components/InboxMacros.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseView.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Открыть Wave7 Part B TP и перевести session canon на новый active block.
2. Добавить `executeMacro` в `inboxApi` и типизированный apply contract во frontend.
3. Расширить `InboxMacros` form/use/manage flow action builder-ом и human-readable hints.
4. Подключить case-scoped apply flow: execute action -> update case cache/queue -> prefill draft.
5. Зафиксировать поведение в `inspect_case` mock lane.

## DoD
- Менеджер может создать/изменить макрос с optional action config из текущего UI.
- Менеджер видит, что конкретно сделает action-macro.
- Применение action-macro к открытому кейсу вызывает backend execute endpoint и не ломает text-only macros.
- После apply case/detail/queue синхронизируются без ручного refresh.
- `inspect_case` mock lane покрывает новый UI flow.

## Checks
- `cd console-web && npm run lint -- --file src/components/InboxMacros.tsx --file src/lib/api-client.ts --file src/components/InboxView.tsx --file src/components/CaseView.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd truffles-api && pytest -q tests/test_console_inbox_macros.py tests/test_console_openapi_calendar_contract.py`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Lint + Playwright output.
- Session log with Wave7 Part A closure and Part B progress.

## Release safety (mandatory)
- **Rollout:** frontend-only integration over already merged backend contract; text-only macros remain supported.
- **Go/no-go:** text-only macros still insert body, action-macros apply successfully in mock lane, no broken composer flow.
- **Rollback:** revert this bounded frontend diff; backend contract stays dormant and harmless.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave7 Part B checks.

## No-go
- Выполнять action и отправлять сообщение одним silent-click without hint.
- Прятать action config only in internal labels without explicit UI explanation.
- Тянуть в этот блок новые backend action types или routing logic.

## Риски/блокеры
- Нельзя терять draft/body при успешном apply action.
- Нужно избегать двойного apply при repeated click; apply button state must be pending-safe.
- `snooze_case` требует понятного minutes input, иначе UX станет ambiguous.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: нет advanced preview/undo, нет assign-to-other-manager action-macro, нет analytics по macro usage.
- `Why not in this block`: это уже отдельные operator optimization blocks, не обязательные для первого полноценного UX closure.
- `Risk if deferred`: macro flow будет рабочим, но без supervisor-grade observability и расширенного контроля.
- `Linked follow-up Task Package(s)`: `TBD wave8`, `TBD macro-analytics follow-up`.
- `Expiry/trigger to stop deferral`: если macro usage начнёт влиять на массовые процессы или появятся ошибки применения без объяснений, нужен отдельный block на preview/analytics.

## Next-block contract (mandatory)
- `Next block objective`: открыть Wave8 и довести `Заявки/Записи` до единого workspace shell без route-level friction.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave7 Part B must keep text-only macros intact and show stable action apply flow.
- `Owner role for closure`: Brain / Top Architect.
