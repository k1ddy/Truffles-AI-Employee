Title: Control Plane TP‑C — Destructive‑change safeguards
Owner: Top Architect
Date: 2026-01-26

Canon refs:
- SPECS/CONTROL_PLANE.md (Knowledge safety + Go/No‑Go)
- SPECS/MULTI_TENANT.md (fail‑closed + audit)
- STRATEGY/REQUIREMENTS.md (safety + no silent changes)
- docs/CONSOLE_GUIDE.md (Console actions)
- STATE.md (roadmap)

Dependencies:
- TP‑A RBAC matrix enforcement (PR #383 merged).
- TP‑B onboarding state machine (recommended before applying destructive guards).

Invariant:
- Любое destructive изменение требует явного подтверждения + reason.
- Аудит на каждый destructive action.
- Никаких silent‑rollback или скрытых изменений.

Scope:
- Ввести единый confirm‑guard для destructive операций (2‑step confirm или explicit reason).
- Детект destructive‑diff (Knowledge publish/rollback).
- Guard для отключения ключевых capabilities или деактивации branch.
- UI подтверждение (modal + reason) в Knowledge/Settings.
- Тесты на confirm‑flow.

Out of scope:
- Новый бизнес‑процесс или AI‑логика.
- Полный UI‑редизайн.
- Изменения provider adapters.

Touch-list (files/tables):
- truffles-api/app/services/confirm_guard.py (new)
- truffles-api/app/routers/console.py (knowledge/capabilities/branch guards)
- truffles-api/app/schemas/console.py (confirm payload)
- truffles-api/app/models/audit_event.py (если нужен новый тип)
- console-web/src/app/knowledge/page.tsx (confirm + reason)
- console-web/src/app/settings/page.tsx (confirm + reason)
- console-web/src/lib/api-client.ts (error code + confirm flow)
- contracts/console_api/openapi.v1.yaml
- truffles-api/tests/test_console_destructive_guards.py (new)
- SPECS/CONTROL_PLANE.md, docs/CONSOLE_GUIDE.md
- STATE.md, STRUCTURE.md

Plan:
1) Определить перечень destructive‑действий и критерии:
   - Knowledge publish/rollback с удалением/обнулением критичных полей.
   - Capabilities disable (channels/providers/features off).
   - Branch deactivate / instance_id removal.
2) Реализовать confirm‑guard:
   - первый запрос → 409 `CONFIRM_REQUIRED` + summary + confirm_token.
   - второй запрос с token + reason → выполняется.
3) Добавить audit events (type + payload).
4) UI:
   - modal подтверждения + обязательный reason.
   - отображение summary/diff.
5) Тесты:
   - запрет без confirm;
   - success с confirm + reason;
   - audit записан.
6) Документация + STATE.

DoD:
- Destructive операции нельзя выполнить без confirm + reason.
- Audit лог содержит reason + summary.
- UI показывает подтверждение и требует reason.
- Тесты проходят.

Checks:
- pytest -q truffles-api/tests/test_console_destructive_guards.py
- npm --prefix console-web run lint
- npm --prefix console-web run generate:api (если OpenAPI менялся)

Evidence:
- CI run URL + test output.
- Обновление STATE.md с PR/CI evidence.

Rollback:
- Revert PR; rollback confirm‑guard.

No-go:
- Не отключать guards через feature‑flag без решения Owner/Brain.
- Не выполнять destructive‑операции через direct DB.

Branch/Worktree:
- Branch: feat/control-plane-destructive-guards
- Worktree: /home/zhan/worktrees/control-plane-destructive-guards
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch/worktree after merge
