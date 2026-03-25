# TP-2026-02-17-platform-ux-wave123-a88

- Название/цель: Закрыть системные UX-пробелы Console Plane для всех бизнес-ниш: прозрачный контекст, предсказуемая загрузка и единый контракт provider-ошибок.
- Canon refs: `AGENTS.md`, `STATE.md` (UX complaints + platform clarity gaps), `STRUCTURE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Не менять backend RBAC и tenant-фильтрацию; не менять продуктовый контракт `FACT/COLLECT/HANDOFF`; не вводить нишевые хардкоды.
- Scope:
  - `1` Единый блок Context Health в shell с понятными предупреждениями и next-actions.
  - `2` Единый performance-profile для query + skeleton strategy на ключевых owner/admin страницах.
  - `3` Единый provider error UX contract (billing blocked vs unavailable vs auth vs rate-limit) и применение в Business/Ops.
- Out of scope:
  - Изменения схем БД и backend API контракта.
  - Редизайн всех страниц платформы.
  - Изменение прав доступа ролей.
- Touch-list (файлы/таблицы):
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/app/business/page.tsx`
  - `console-web/src/app/subscription/page.tsx`
  - `console-web/src/app/business/data-trust/page.tsx`
  - `console-web/src/app/business/team-performance/page.tsx`
  - `console-web/src/components/PageStates.tsx` (new)
  - `console-web/src/lib/query-profiles.ts` (new)
  - `console-web/src/lib/provider-error-contract.ts` (new)
  - Session docs: `docs/TASK_PACKAGES/*`, `docs/SESSIONS/*`, `docs/SESSION_INDEX.md`
- Plan (1..N):
  1. Добавить reusable контракты (`query-profiles`, `provider-error-contract`, `PageStates`).
  2. Внедрить Context Health в `ConsoleShell` для всех ролей (с ролевыми подсказками).
  3. Применить performance profile + skeleton strategy на выбранных страницах.
  4. Применить provider-error-contract в Business и Ops с явной дифференциацией типов причин.
  5. Запустить локальные проверки и оформить evidence.
- DoD:
  - Context Health показывает состояние контекста и не скрывает роль/фильтр active entities.
  - Для provider-инцидентов UI явно различает `provider_billing_blocked`, `provider_unavailable`, `provider_auth`, `provider_rate_limited`.
  - Ключевые страницы используют единый query/perf профиль и единый skeleton pattern.
  - `npm run lint` и `npm run build` в `console-web` проходят.
- Checks:
  - `cd console-web && npm run lint`
  - `cd console-web && npm run build`
- Evidence:
  - `git diff --stat`
  - Логи локальных проверок
  - PR URL + CI URL
- Rollback:
  - Выполнять `git revert` по фактическому hash коммита после merge.
- No-go:
  - Не объединять разные provider-причины в один generic текст.
  - Не делать full-page reload для nav.
  - Не менять backend filtering contract ради UI-эффекта.
- Риски/блокеры:
  - Потенциальные E2E дрейфы по тест-id/текстам; минимизировать обратной совместимостью data-testid.
