# TP-2026-02-14-ux-unify-workspace-a1

- Название/цель: Упростить управление компаниями в Console Plane: оставить provider execute-операции в одном месте (`Company Workspace`), а `Integrations` сделать операционным реестром и точкой навигации.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по onboarding + provider ops), `STRATEGY/REQUIREMENTS.md`.

- Invariant:
  - Безопасность execute-гейтов (`confirmation`, tenant access, hard-stop) не ослабляется.
  - `Start Rebind` hotfix в `main` сохраняется.
  - API контракты backend не меняются.

- Scope:
  - UX-unification фронтенда между `Integrations` и `Company Workspace`.
  - Удаление дублирующих execute-механик из `Integrations`.
  - Явный переход в `Company Workspace` с сохранением company/client/branch scope.

- Out of scope:
  - Изменение backend схем/моделей provider binding.
  - Редизайн всей консоли.
  - Миграции БД.

- Touch-list:
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/e2e/smoke.spec.ts` (или иной e2e smoke по навигации)
  - `docs/SESSIONS/SESSION-2026-02-14-ux-unify-workspace-a1.md`
  - `docs/SESSION_INDEX.md`

- Plan:
  1. Подтвердить текущую стабильность `Start Rebind` после merge через целевые проверки.
  2. Перевести `Integrations` в read-only registry + CTA "Manage in Workspace".
  3. Реализовать автоперенос scope в localStorage и переход на `/company-workspace`.
  4. Обновить e2e smoke/покрытие UX-потока, прогнать проверки.

- DoD:
  - В `Integrations` отсутствуют дублирующие execute-действия provider ops.
  - Есть понятный путь к управлению через `Company Workspace` для конкретного филиала.
  - Минимум один тест покрывает новый UX-путь.
  - Таргетные тесты проходят.

- Checks:
  - `pytest -q truffles-api/tests/test_console_integrations_registry.py -q`
  - `cd console-web && npm run test:e2e -- --grep "@smoke"`

- Evidence:
  - Логи таргетных тестов.
  - Diff с удалением дублей execute из `Integrations` и добавлением перехода в Workspace.

- Rollback:
  - Revert коммита UX-unification и возврат прежнего поведения `Integrations`.

- No-go:
  - Не дублировать execute-мутации между страницами.
  - Не обходить confirmation/hard-stop на UI.

- Риски/блокеры:
  - Возможна зависимость старых e2e-тестов от прежних кнопок действий в `Integrations`; потребуется синхронное обновление тестов.
