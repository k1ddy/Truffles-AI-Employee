# TP-2026-02-09-console-build-hotfix-a20

- Название/цель: Исправить падение production сборки `console-web` (TypeScript) и восстановить обновление Console Plane build.
- Canon refs: AGENTS.md; STATE.md (актуальный контекст PR-3A и post-merge deploy).
- Invariant: Не ломать tenant isolation и существующие go-live API контракты; не менять бизнес-логику approvals/rejections.
- Scope: Только типобезопасность отображения go-live полей в `ProvisioningWizard` и проверка сборки/перезапуска console-web.
- Out of scope: Изменение backend API, миграций, livecheck suite логики, CI policy.
- Touch-list (файлы/таблицы):
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `docs/SESSIONS/SESSION-2026-02-09-console-build-hotfix-a20.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-09-console-build-hotfix-a20.md`
- Plan (1..N):
  1. Локализовать точку TypeScript ошибки сборки.
  2. Нормализовать типы go-live полей из `unknown` в безопасные значения для JSX.
  3. Прогнать `lint` и `build` для `console-web`.
  4. Перезапустить `console-web` с актуальным SHA/BUILD_TIME.
  5. Проверить build metadata в рантайме.
- DoD:
  - `npm --prefix console-web run build` проходит.
  - `truffles-console-web` стартует на новом build.
  - В контейнере выставлены `NEXT_PUBLIC_BUILD_SHA` и `NEXT_PUBLIC_BUILD_TIME` с актуальными значениями.
- Checks:
  - `npm --prefix console-web run lint`
  - `npm --prefix console-web run build`
  - `bash scripts/restart_console_web.sh`
  - `docker exec truffles-console-web /bin/sh -lc 'echo NEXT_PUBLIC_BUILD_SHA=$NEXT_PUBLIC_BUILD_SHA; echo NEXT_PUBLIC_BUILD_TIME=$NEXT_PUBLIC_BUILD_TIME'`
- Evidence:
  - Логи успешной сборки `next build`.
  - Лог рестарта `console-web` с `GIT_COMMIT`/`BUILD_TIME`.
  - Рантайм значения build env из контейнера.
  - Запись в `STATE.md` выполняет Brain/Top Architect при приемке.
- Rollback:
  - `git revert` hotfix коммита и повторный `bash scripts/restart_console_web.sh`.
- No-go:
  - Не вносить изменения в backend contracts/DB.
  - Не обходить TypeScript через `any`/disable checks.
- Риски/блокеры:
  - Если сборка падает на других типовых ошибках, потребуется отдельный scoped hotfix.
