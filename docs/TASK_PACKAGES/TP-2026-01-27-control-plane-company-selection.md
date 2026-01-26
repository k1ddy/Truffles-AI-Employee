# TP-2026-01-27 — Company → Client → Branch selection (UI + API)

- **Название/цель:** реализовать company-level selection в Console (UI + API) с fail-closed гейтом и поддержкой X-Company-Id.
- **Invariant:** не нарушить tenant isolation и существующие selection gates (client/branch); без догадок о контексте.
- **Scope:** console auth/context, /console/v1/me schema, console-web context bar + selection gates, X-Company-Id header, Playwright e2e update, OpenAPI/types.
- **Out of scope:** миграции БД, новые роли/RBAC, Knowledge/Inbox/Calendar функционал, изменения CORE пайплайна.
- **Touch-list:**
  - `truffles-api/app/services/console_auth.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_auth_access.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `contracts/console_api/errors.v1.json`
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/components/LoginButton.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/lib/api.ts`
  - `console-web/src/app/api/proxy/[...path]/route.ts`
  - `console-web/e2e/auth.setup.ts`
  - `console-web/e2e/smoke.spec.ts`
  - `console-web/e2e/login.spec.ts`
  - `console-web/src/types/api.generated.ts` (generated)
  - `docs/CONSOLE_GUIDE.md`
  - `SPECS/CONTROL_PLANE.md`
  - `STRUCTURE.md`
  - `STATE.md`
- **Plan:**
  1) Backend: добавить X-Company-Id parsing + company selection gate в console_auth, расширить ConsoleMeResponse (companies + company_selection_required + selected_company_id + company_name).
  2) Contracts: обновить OpenAPI и errors.v1.json; сгенерировать `api.generated.ts`.
  3) UI: добавить Company selector в ContextBar + SelectionGate, localStorage `console:company_id`, прокинуть X-Company-Id через api-client + proxy.
  4) E2E: обновить Playwright селекторы/flow для company gate.
  5) Docs: обновить guide/specs (план → факт), зарегистрировать TP.
- **DoD:**
  - API возвращает companies list и company_selection_required, при multi-company без X-Company-Id → 400 COMPANY_SELECTION_REQUIRED.
  - UI умеет выбрать Company → Client → Branch, хранит выбор и отправляет X-Company-Id на все запросы.
  - Playwright smoke/login/auth.setup проходит локально (или зафиксирован waiver).
  - Контракты и типы обновлены, документы синхронизированы.
- **Checks:**
  - `pytest -q truffles-api/tests/test_console_auth_access.py`
  - `npm --prefix console-web run lint`
  - `npm --prefix console-web run generate:api`
- **Evidence:** вывод команд + ссылки на PR/CI; обновление `STATE.md` с evidence (до merge).
- **Rollback:** `git revert` PR; удалить `console:company_id` использование и `X-Company-Id` headers.
- **No-go:** не трогать `docs/CONSULTANT_CODEMAP.md` и CORE/LLM pipeline.
- **Риски/блокеры:** отсутствие company_id у клиентов (нужна договорённость по обработке "без компании"); конфликт с PR #375 (docs update).
- **Branch / Worktree:**
  - Branch: `feat/control-plane-company-selection`
  - Worktree: `/home/zhan/worktrees/control-plane-company-selection`
  - Base ref: `origin/main`
  - Merge policy: merge commit, no rebase
  - Cleanup: удалить ветку и worktree после merge (Brain)
