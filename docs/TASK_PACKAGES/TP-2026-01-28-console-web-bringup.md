# TP-2026-01-28-console-web-bringup

- Название/цель: Запустить console-web по канону (Traefik → console.truffles.kz) и снять 404 на login.
- Canon refs: `TECH.md` (Console Web), `docs/DEPLOYMENT_RUNBOOK.md` (Console Web), `STATE.md` (GAP: console.truffles.kz 404).
- Invariant: Auth остаётся fail-closed; core-сервисы не трогаем; только запуск console-web.
- Scope: Запуск `console-web` через `truffles-api/docker-compose.yml`, проверка доступности и фиксация evidence.
- Out of scope: изменение доменов, RBAC, API, лендинг, иные сервисы.
- Touch-list (файлы):
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-01-28-console-web-bringup-a2.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-01-28-console-web-bringup.md`
- Plan:
  1) Проверить `console-web/.env.local` (NEXTAUTH_URL/KEYCLOAK/NEXT_PUBLIC_API_URL).
  2) `docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web`.
  3) Проверить `curl -I https://console.truffles.kz` и `/api/auth/signin` (не 404).
  4) Зафиксировать evidence в `STATE.md`.
- DoD:
  - `console.truffles.kz` отвечает не 404.
  - `/api/auth/signin` отвечает не 404.
  - Контейнер `truffles-console-web` запущен.
  - `STATE.md` обновлён с evidence.
- Checks:
  - `docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web`
  - `curl -I https://console.truffles.kz`
  - `curl -I https://console.truffles.kz/api/auth/signin`
- Evidence:
  - Вывод `docker ps | rg truffles-console-web`.
  - Заголовки `curl -I` для console.truffles.kz и /api/auth/signin.
- Rollback:
  - `docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml stop console-web`
- No-go:
  - Сервис не стартует или остаётся 404.
- Риски/блокеры:
  - Неверный `NEXTAUTH_URL`/OIDC env.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-01-28-console-web-bringup-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-console-web-bringup-a2`
  - Base ref: `origin/main`
  - Merge policy: PR (Top Architect)
  - Cleanup: удалить ветку и worktree после merge
