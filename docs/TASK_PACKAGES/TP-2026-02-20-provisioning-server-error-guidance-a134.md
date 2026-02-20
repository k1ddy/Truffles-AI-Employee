# TP-2026-02-20-provisioning-server-error-guidance-a134

- Название/цель: Усилить обработку server-side ошибок provisioning в Console UX (`/tenants` + `ProvisioningWizard`) с actionable инструкцией и trace, чтобы platform admin быстрее закрывал инцидент без догадок.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`, `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-end2end-tz.md`.

- Invariant:
  - Онбординг-контракт и fail-closed gate не ослабляются.
  - Поведение provisioning API не меняется; меняется только UX-обработка ошибок.
  - Нет клиент-специфичных исключений/хардкодов.

- Scope:
  - Добавить единый механизм формирования next-step guidance для server/proxy/upstream ошибок provisioning.
  - Применить его в write-flow `Tenants` quick-create/change-management и `ProvisioningWizard` mutations.
  - Обновить e2e smoke покрытие `/tenants` на наличие контекста ошибок (trace/evidence блок) для provisioning потока.

- Out of scope:
  - Изменение backend API-кодов ошибок.
  - Перепроектирование layouts вкладок `tenants`/`settings`.
  - Изменения бизнес-логики onboarding throughput.

- Touch-list (файлы/таблицы):
  - `console-web/src/lib/use-inline-error-summary.ts`
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/e2e/platform-admin.spec.ts`

- Plan (1..N):
  1. Добавить опциональный режим `provisioning guidance` в inline error hook (server/proxy/upstream class).
  2. Подключить guidance в provisioning write actions `Tenants`.
  3. Подключить guidance в provisioning mutations `ProvisioningWizard`.
  4. Добавить e2e/assertions для наличия trace-aware error summary контракта в tenants onboarding flow.
  5. Прогнать lint + targeted e2e/ts checks и собрать evidence.

- DoD:
  - При server/proxy/upstream сбое provisioning в UI появляется явная инструкция “что делать сейчас” + trace/ref.
  - Ошибка по-прежнему логируется в inline summary, но теперь с actionable remediation шагом.
  - Existing flows (create/update/publish) не ломаются.
  - Проверки проходят локально.

- Checks:
  - `npm --prefix console-web run lint -- --file src/lib/use-inline-error-summary.ts --file src/app/tenants/page.tsx --file src/components/ProvisioningWizard.tsx --file e2e/platform-admin.spec.ts`
  - `npm --prefix console-web run build`
  - `npx --prefix console-web playwright test e2e/platform-admin.spec.ts --grep \"Tenants\" --reporter=line` (если env доступен; иначе фиксируем BLOCKED)

- Evidence:
  - Diff c измененными call-sites + guidance payload.
  - Lint/build output.
  - E2E output или `BLOCKED` с причиной среды.
  - Session/report artifacts в `docs/SESSIONS` + `docs/REPORTS`.

- Rollback:
  - `git revert SHA_ФИКСА`.

- No-go:
  - Не скрывать server-error и не “гасить” исключения без trace.
  - Не добавлять brittle эвристики по тексту конкретного провайдера.
  - Не менять backend contracts ради UI-обхода.

- Branch / Worktree / Base / Merge policy / Cleanup:
  - Branch: `feat/2026-02-20-provisioning-server-error-guidance-a134`
  - Worktree: `/home/zhan/worktrees/2026-02-20-provisioning-server-error-guidance-a134`
  - Base ref: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: после merge cleanup ветки/worktree по стандартному процессу.

- Риски/блокеры:
  - Нельзя деградировать текущие inline error потоки для non-provisioning разделов.
  - Playwright может быть ограничен окружением/логином; в этом случае явный `BLOCKED` с фиксацией причины.
