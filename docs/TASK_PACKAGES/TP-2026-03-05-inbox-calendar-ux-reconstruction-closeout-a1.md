# TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE4-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-DONE-A1

## Название/цель
Закрыть пост-wave4 release discipline для `Заявки/Записи`: закрепить canary/go-no-go/rollback runbook, сделать rollback управляемым через флаг realtime и зафиксировать live-no-mocks evidence с reason-codes.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`
- `docs/runbooks/INBOX_CALENDAR_WAVE4_RELEASE.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/hooks/useCaseData.ts`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/runbooks/INBOX_CALENDAR_WAVE4_RELEASE.md`
- `Baseline findings`:
  - realtime уже работает (`SSE-first + polling fallback`), но rollback-путь не был toggle-driven;
  - live-no-mocks lane нестабилен и терялся в неявных `skip`;
  - формальный closeout-артефакт wave4 отсутствовал.

## One web search (mandatory before implementation)
- **Query (exact):** `feature flag rollback playbook progressive delivery best practices`
- **Date/time (local):** `2026-03-05T18:10:00+05:00`
- **Sources opened:**
  - `https://cloud.google.com/architecture/devops/devops-tech-progressive-delivery`
  - `https://martinfowler.com/articles/feature-toggles.html`
- **Ready solutions found:** rollback для runtime-поведения должен быть быстрым через switchable flag + staged canary checkpoints.
- **Decision (`reuse/integrate/build`):** `integrate` — добавить флаг отключения SSE в существующий hook и формальный release runbook без нового runtime сервиса.
- **Rejected options:** rollback только через `revert` без быстрых runtime controls.
- **Source quality:** high-signal source = Google Cloud Architecture + Martin Fowler reference article.

## Root cause (mandatory)
- **Symptom:** после wave4 нет полностью завершенного операционного контура для rollout и моментального rollback.
- **Minimal reproduction:** при live auth/data нестабильности no-mocks e2e даёт `skip/fail`, а rollback требует full revert вместо runtime switch.
- **Evidence:** текущие wave4 evidence в session + live `inspect_case` skip path.
- **Five Whys:**
  1. Почему closeout не завершён? Не был оформлен отдельный post-wave4 block.
  2. Почему rollback медленный? Нет runtime flag для SSE path.
  3. Почему live evidence неустойчив? e2e skip/fail причины не структурированы.
  4. Почему это риск? canary decisions становятся ручными и неформальными.
  5. Почему это критично? Release safety gate требует проверяемый go/no-go + rollback.
- **Root cause statement:** отсутствовал формальный closeout-блок для release safety after wave4.
- **Fix mechanism:** добавить toggle-driven rollback, reason-coded live lane outcome и runbook с канарейкой.

## Reuse-first plan (mandatory)
- **Reuse:** существующий `useCaseData`, `inspect_case` e2e, wave4 TP.
- **Integrate:** флаг `NEXT_PUBLIC_CASE_SSE_ENABLED`, runbook и closeout TP.
- **Build only if needed:** нет новых сервисов/таблиц.

## Invariant
- Не менять бизнес-логику case/booking.
- Не удалять polling fallback.
- Не ослаблять wave4 acceptance критерии.

## Scope
- Добавить frontend toggle для мгновенного перехода в polling-only режим.
- Уточнить `inspect_case` live lane: явная фиксация auth-gate как reasoned skip.
- Оформить runbook canary/go-no-go/rollback с deterministic командами.

## Out of scope
- Новые backend endpoints.
- Масштабный рефакторинг Playwright framework.

## Touch-list
- `console-web/src/hooks/useCaseData.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/runbooks/INBOX_CALENDAR_WAVE4_RELEASE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md`

## Plan (1..N)
1. Ввести SSE feature flag rollback path (`NEXT_PUBLIC_CASE_SSE_ENABLED`).
2. Обновить `inspect_case` live lane на reason-coded skip для auth-gate.
3. Зафиксировать canary/go-no-go/rollback SOP в runbook.
4. Прогнать lint + inspect_case (mocked/live-no-mocks) + session gate.

## DoD
- Rollback до polling-only выполняется флагом без кода.
- Live no-mocks outcome даёт явный reason-code (`auth gate`) вместо немого skip.
- Есть runbook для `1 branch -> 25% -> 100%` с go/no-go и rollback.
- Session evidence обновлён и `session_check` зелёный.

## Checks
- `cd console-web && npm run lint -- --file src/hooks/useCaseData.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`
- `cd console-web && INSPECT_CASE_USE_MOCKS=0 PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Output checks.
- Скриншоты `case_inspection.png`, `calendar_case_context.png`, `live_cases_workspace_unavailable.png`.
- Runbook with go/no-go checklist.

## Release safety (mandatory)
- **Rollout:** `1 branch -> 25% branches -> 100%` по runbook.
- **Go/no-go:** lint/tests green + live lane outcome reasoned + KPI thresholds.
- **Rollback:** `NEXT_PUBLIC_CASE_SSE_ENABLED=0` + console-web restart; при необходимости revert PR.

## Rollback
- Установить `NEXT_PUBLIC_CASE_SSE_ENABLED=0`.
- Перезапустить console-web.
- При устойчивой деградации: `git revert` wave4 PR.

## No-go
- Деплой realtime без documented rollback flag.
- Продвижение canary при неявном/непонятном состоянии live lane.

## Риски/блокеры
- Live auth provider может давать нестабильный SSO flow.
- Слишком частые ручные перезапуски могут замаскировать системный auth issue.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: live lane зависит от внешнего auth состояния Keycloak/NextAuth.
- `Why not in this block`: инфраструктурный auth стабилизационный блок вне scope wave4 closeout.
- `Risk if deferred`: периодические `auth-gate` skip для live lane.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-console-e2e-live-auth-hardening-a1.md` (to be created if skips persist).
- `Expiry/trigger to stop deferral`: `2` подряд release циклов с `auth-gate` skip.

## Next-block contract (mandatory)
- `Next block objective`: стабилизировать live auth lane до устойчивого `pass`.
- `First deterministic check command`: `cd console-web && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/login.spec.ts --project=chromium-login`
- `Blocked-by conditions`: недоступны валидные `E2E_USERNAME/E2E_PASSWORD`.
- `Owner role for closure`: Brain / Top Architect.
