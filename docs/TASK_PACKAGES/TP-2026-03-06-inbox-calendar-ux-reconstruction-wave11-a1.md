# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE11-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE11-PARTB-A1

## Название/цель
Закрыть два live-операционных пробела после merge Waves 1-10: сделать `Вернуть в работу` и related case-action sync action-correct, без ложных Telegram/client ошибок, и перестроить левую очередь `Заявки`, чтобы менеджер видел режим, фильтры и карточки без сжатия и потери смысла.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred; split only if `Part A action-sync correctness` is ready earlier than `Part B queue rail UX`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_inbox_macros.py`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
  - `console-web/case_inspection.png`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
- `Baseline findings`:
  - `POST /cases/{case_id}/reopen` и macro `reopen_case` сейчас повторно используют connected-sync ветку от `take`, включая `editMessageReplyMarkup` и client notify, хотя reopen — это внутренний возврат кейса в рабочий цикл, а не новая handoff-эскалация.
  - Именно поэтому live ошибка `Telegram: telegram_edit_failed · Клиент: chatflow_failed` объясняется текущим кодом, а не случайной сетью: reopen пытается синхронизировать уже закрытый Telegram alert и отправить внешнее сообщение клиенту там, где это не обязательно и часто ложно.
  - Левая колонка inbox в compact/workspace режиме слишком узкая (`220px`) и пытается уместить queue modes, поиск, sort и owner filters в один сжатый control-row; из-за этого менеджеру трудно понять текущий режим очереди и быстро читать карточки.

## One web search (mandatory before implementation)
- **Query (exact):** `Telegram Bot API editMessageReplyMarkup official documentation editable messages limits`
- **Date/time (local):** `2026-03-06T17:07:00+05:00`
- **Sources opened:**
  - `https://core.telegram.org/bots/api#editmessagereplymarkup`
- **Ready solutions found:** Telegram явно описывает `editMessageReplyMarkup` как редактирование reply markup только у сообщений, отправленных ботом или via bot; это подтверждает, что повторное редактирование закрытого/неподходящего escalation message не должно быть обязательной частью reopen path.
- **Decision (`reuse/integrate/build`):** `integrate` — не строить новый sync engine, а сделать существующий case-action sync action-aware: `take` сохраняет внешние side effects, `reopen` становится internal-only reopen without false Telegram/client sync.
- **Rejected options:** silent ignore всех sync ошибок без смены семантики action; retry loop поверх reopen; новый отдельный Telegram workflow только для reopen.
- **Source quality:** high-signal primary source = official Telegram Bot API documentation.

## Root cause (mandatory)
- **Symptom:** после `Вернуть в работу` менеджер видит `telegram_edit_failed · chatflow_failed`, хотя сам case state меняется и интерфейс создаёт ложное ощущение частичного провала/ложной синхронизации.
- **Minimal reproduction:** открыть resolved case -> нажать `Вернуть в работу` -> backend переводит case в `active`, затем пытается повторно выполнить `take`-style sync (Telegram markup edit + client connected message) и может вернуть fail even when reopen as an internal action actually succeeded.
- **Evidence:** `truffles-api/app/routers/console.py` reopen path вызывает тот же connected sync, что и `take`; `notify_client_manager_status(... status=\"connected\")` всегда отправляет внешнее сообщение клиенту; compact `InboxView + CaseList` используют узкий rail и горизонтальный filter row.
- **Five Whys:**
  1. Почему `Вернуть в работу` даёт ложный sync fail? Потому что reopen переиспользует side effects от `take`.
  2. Почему это неверно по бизнес-смыслу? Потому что reopen — это внутренний возврат resolved кейса в рабочий цикл, а не новая первичная handoff-эскалация.
  3. Почему Telegram edit падает? Потому что reopen трогает старое escalation message, которое уже не обязано оставаться редактируемым/актуальным.
  4. Почему `chatflow_failed` тоже появляется? Потому что reopen пытается отправить клиенту `manager connected` сообщение даже там, где это не нужно или канал/flow уже не соответствует этому контракту.
  5. Почему UX левой очереди остаётся плохим? Потому что после product waves добавились queue modes, filters и bulk-controls, а compact rail остался рассчитан на старую плотность и слишком узкую колонку.
- **Root cause statement:** reopen path использует не свой action contract, а унаследованный `take` sync contract; parallelly inbox left rail накопил больше операционных controls, чем может безопасно нести текущая ширина и горизонтальная layout-модель.
- **Fix mechanism:** разделить case-action sync по semantic mode (`take` vs `reopen`) и для reopen сделать explicit internal-only sync; отдельно перестроить queue rail в inbox на более широкую и вертикально сгруппированную IA.

## Reuse-first plan (mandatory)
- **Reuse:** existing case action endpoints, `ConsoleCaseActionSync`, `_build_sync_status`, current `CaseList` queue view model, current `inspect_case` lane.
- **Integrate:** внедрить action-aware sync helper вместо нового transport layer; пересобрать текущий compact rail на существующих queue/filter primitives без новой вкладки и без нового queue engine.
- **Build only if needed:** один dedicated reopen sync helper и bounded queue summary/layout helpers inside `CaseList`.

## Invariant
- Не менять бизнес-семантику `take`, `resolve`, `return` без RCA-based причины.
- Не скрывать реальные sync ошибки у `take/resolve/return` под видом общего silent fallback.
- Не добавлять новые top-level tabs или отдельный queue route.
- Не ломать mobile/workspace layout при расширении desktop rail.

## Scope
- `Part A (this TP)`:
  - action-aware sync contract for `reopen`;
  - audit `take/reopen/resolve/return` call sites so only reopen changes semantics;
  - targeted backend tests for reopen sync correctness and macro parity;
  - user-facing success path without false failed-sync toast on reopen.
- `Part B (allowed split if needed)`:
  - widen desktop inbox rail;
  - separate queue mode summary, primary filters and card list into clearer vertical blocks;
  - improve case card readability in compact mode;
  - revalidate with screenshot and existing inspect-case lane.

## Out of scope
- Policy-based routing automation.
- New queue columns or new admin/governance features.
- Rewriting full calendar or case details shell.
- Global transport retry framework for Telegram/Chatflow.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_inbox_macros.py`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Зафиксировать Wave11 TP и перевести session canon с closeout-review на новый post-merge hardening block.
2. Реализовать action-aware reopen sync на backend и покрыть unit tests.
3. Проверить macro `reopen_case`, чтобы он наследовал ту же reopen-safe semantics.
4. Перестроить inbox left rail: ширина, вертикальная группировка controls, более читаемые compact cards.
5. Обновить inspect-case lane и screenshot evidence.

## DoD
- `Вернуть в работу` больше не пытается притворяться новым `take` и не выдаёт ложный failed-sync из-за reopen-internal action.
- `take`/`resolve`/`return` сохраняют текущие внешние sync side effects.
- Macro `reopen_case` использует ту же reopen-safe semantics.
- Левая очередь на desktop заметно читаемее: режим, фильтры и карточки не выглядят сжатыми.
- Targeted backend/frontend checks зелёные, screenshot показывает improved rail composition.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `cd console-web && npm run lint -- --file src/components/InboxView.tsx --file src/components/CaseList.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Targeted pytest output with reopen-safe semantics.
- Lint/build/Playwright output.
- Updated `console-web/case_inspection.png`.
- Session log with Wave11 evidence.

## Release safety (mandatory)
- **Rollout:** same endpoints/UI surfaces, no contract expansion; behavior change is limited to reopen sync side effects and inbox desktop layout.
- **Go/no-go:** reopen shows success without false failed sync; `take/resolve/return` still return sync payloads; inbox desktop remains usable and no regression in inspect-case lane.
- **Rollback:** revert bounded diff; reopen falls back to old semantics, inbox rail returns to previous width/layout.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave11 checks.

## No-go
- Гасить все sync failures общим `try/except` без разделения semantic modes.
- Менять `take` semantics вместе с reopen "на всякий случай".
- Добавлять второй queue screen вместо исправления текущей левой колонки.
- Раздувать block новыми supervisor features.

## Риски/блокеры
- Нужно не замаскировать реальную transport проблему для `take`, где клиент действительно должен получить connected signal.
- Reopen-safe semantics должны совпасть и для direct action, и для action macro.
- При расширении rail нельзя сломать 1280px desktop breakpoint и mobile drawer behavior.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: transport-specific retry/repair policies for failed `take/resolve/return` syncs; richer queue customization beyond this rail cleanup.
- `Why not in this block`: сейчас нужен semantic correctness и usability fix, а не новый reliability framework или новая governance wave.
- `Risk if deferred`: отдельные transport failures на других actions всё ещё будут нуждаться в отдельном RCA/runbook, а queue UX может требовать ещё одну cosmetic pass на smaller desktop widths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`, `TBD follow-up if any remaining transport anomalies stay reproducible after Wave11`.
- `Expiry/trigger to stop deferral`: если после merge Wave11 live backend всё ещё даёт ложные sync errors на `take/resolve/return`, нужен отдельный RCA TP, а не silent acceptance.

## Next-block contract (mandatory)
- `Next block objective`: после Wave11 merge провести live validation того же сценария `resolved -> reopen` и оценить, нужен ли отдельный follow-up только на transport retry/runbook или текущая semantic correction закрыла bug.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `Blocked-by conditions`: Wave11 must keep existing inspect-case lane green and must not regress case action permissions or compact queue selection.
- `Owner role for closure`: Brain / Top Architect.
