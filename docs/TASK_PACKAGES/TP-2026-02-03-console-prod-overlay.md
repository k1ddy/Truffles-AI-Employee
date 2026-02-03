# TP-2026-02-03-console-prod-overlay

- Название/цель: Проверить свежесть prod console-web контейнера после merge и найти причину блокирующего overlay на https://console.truffles.kz/ (невозможно выбрать клиента/действовать), при необходимости исправить.
- Canon refs: `STATE.md` (BLOCKERS: CLIENT_SELECTION_REQUIRED / console UI), `SPECS/CONTROL_PLANE.md` §9, `SPECS/SYSTEM_REFERENCE.md` (console SOP), `TECH.md` (prod env), `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.
- Invariant:
  - Handover state machine без дрейфа.
  - RBAC fail-closed.
  - Никаких изменений данных в проде (только read-only диагностика).
- Scope:
  - Проверить build SHA/time console-web контейнера и соответствие `origin/main`.
  - Диагностировать UI overlay блокировки на главном экране (selection/guards/network/permissions).
  - Исправить причину (UI/конфиг/API) либо зафиксировать конкретный blocker с evidence.
- Out of scope:
  - Новые фичи Console и изменения в data packs.
  - Миграции БД.
- Touch-list:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/app/layout.tsx`
  - `truffles-api/app/routers/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/types/api.generated.ts`
  - `STATE.md`
- Plan:
  1. Проверить свежесть контейнера (docker exec/curl) и записать build SHA/time + сравнение с `origin/main`.
  2. Воспроизвести overlay на prod (console web) + собрать network/console evidence (ошибки, response codes).
  3. Локализовать источник блокировки (selection_required, missing X-Client-Id, auth, role gating, JS overlay).
  4. Исправить в UI/API/конфиг (минимальная правка) или зафиксировать blocker с evidence.
  5. Обновить OpenAPI/types (если нужно) + тесты/линт.
- DoD:
  - Подтверждён build SHA/time console-web на проде и соответствие `origin/main`.
  - Причина overlay понятна и устранена (или зафиксирована как blocker с evidence).
  - Проверки пройдены, запись в `STATE.md` сделана (Brain/Architect).
- Checks:
  - `curl -s https://console.truffles.kz/api/health/full`
  - `docker ps` / `docker exec truffles-console-web ...`
  - `npm --prefix console-web run lint` (если код менялся)
  - целевые pytest (если затронут backend)
- Evidence:
  - /tmp/* (curl/docker outputs, logs), скрин/текст ошибок, `STATE.md` запись.
- Rollback:
  - Revert коммита или rollback контейнера на предыдущий образ.
- No-go:
  - Любые write-операции в продовой БД.
  - Обход RBAC.
- Риски/блокеры:
  - Если overlay связан с auth/selection на уровне OIDC/instances — может потребоваться решение Brain/Owner.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-prod-overlay-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-prod-overlay-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
