Title: Console Web Deploy — /team route in prod
Owner: Brain
Date: 2026-01-25

Canon refs:
- TECH.md (deploy rules + CI gates)
- docs/DEPLOYMENT_RUNBOOK.md (console-web Docker deploy)
- SPECS/CONTROL_PLANE.md (Phase 4 Team/Calendar UI)
- STATE.md (Control Plane roadmap + blockers)

Invariant:
- Не менять backend/DB/контракты.
- Не трогать Keycloak/Traefik конфиги.
- Не запускать CI (ручной deploy только для console-web).

Scope:
- Исправить build‑ошибку в Team UI (nullable `expires_at`).
- Пересобрать и задеплоить console-web с актуального `main`.
- Убедиться, что `/team` больше не 404.
- Зафиксировать evidence в `STATE.md`.

Out of scope:
- Любые изменения backend/DB.
- Backend/API изменения.

Touch-list:
- `console-web/src/app/team/page.tsx`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-web-deploy-team.md`
- `STRUCTURE.md`
- `STATE.md`

Plan:
1) Исправить nullable `expires_at` в Team UI.
2) Подтвердить SHA `main` для build info (Settings).
3) Собрать и поднять console-web через Docker compose.
4) Проверить `/team` (200) и bundle‑строки Team/Calendar.
5) Обновить `STATE.md` evidence + снять blocker.

DoD:
- `/team` возвращает 200 в проде.
- Build info в Settings показывает актуальный SHA/time.
- Evidence записан в `STATE.md`.

Checks:
- `npm --prefix console-web run lint` (optional, build covers typecheck)
- `GIT_COMMIT=$(git rev-parse HEAD) BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml build console-web`
- `docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web`
- `curl -I https://console.truffles.kz/team`

Evidence:
- Curl /team (HTTP 200).
- Settings build info line (SHA/time).

Rollback:
- Повторный deploy console-web на предыдущем commit (git checkout + build/up).

No-go:
- Любые изменения в API/DB.
- Использование `pm2` для console-web.

Branch / Worktree / Merge:
- Branch: ops/console-web-deploy-team
- Worktree: /home/zhan/worktrees/console-web-deploy-team
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
