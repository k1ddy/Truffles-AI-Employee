# TP-2026-02-03-booking-confirm-unblock

- Название/цель: Разблокировать booking confirm проверку: обновить minimum_data_contract для demo_salon branch_b и обеспечить корректный ruff-check в контейнерных проверках.
- Canon refs: `STATE.md` (GAP minimum_data_contract safe-mode + ruff), `SPECS/VERTICAL_PACK_KIT.md`, `SPECS/ARCHITECTURE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/PROCESSES.md`, `TECH.md`.
- Invariant:
  - SAFE_MODE и minimum_data_contract правила не меняются.
  - Никакой ручной чистки БД/trace ради evidence.
  - Booking confirm логика не меняется, только условия данных/линта.
- Scope:
  - Обновить published knowledge pack для demo_salon branch_b до полного minimum data contract (на базе актуального demo_salon pack).
  - Обеспечить, чтобы ruff в контейнерных проверках использовал актуальную конфигурацию.
  - Повторить preflight health + рой тестов/ruff + live-check (CA05/CA05-commit/CA12) и собрать evidence.
- Out of scope:
  - Изменения в правилах safe-mode/booking confirm.
  - Любые новые фичи/миграции/оптимизации.
  - Настройка реального OAuth/Google Calendar токена (если блокер — фиксируем как GAP).
- Touch-list (files/tables):
  - `truffles-api/Dockerfile`
  - `docs/TASK_PACKAGES/TP-2026-02-03-booking-confirm-unblock.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `STATE.md`
  - Tables: `knowledge_versions`, `branches`
- Plan:
  1) Зафиксировать текущие missing_fields по `/admin/health` и SQL (branch_b).
  2) Опубликовать актуальный demo_salon pack в branch_b через `knowledge_versions` (publish_version) и проверить readiness.
  3) Добавить ruff config в контейнер (копия `truffles-api/pyproject.toml` в `/app`).
  4) Прогнать контейнерные тесты (booking/calendar) + ruff check.
  5) Повторить live-check CA05/CA05-commit/CA12 и SQL-проверки по booking/outbox.
  6) Обновить `STATE.md` и session log с evidence.
- DoD:
  - `/admin/health` показывает branch_b minimum_data_contract ready (missing_fields пуст).
  - `ruff check /app/app /app/tests` проходит в тест-контейнере с конфигом.
  - Live-check CA05/CA05-commit/CA12 не упирается в minimum_data_safe_mode; evidence сохранены.
- Checks:
  - `curl -s http://localhost:8000/admin/health`
  - `python3 ops/diagnose.py livecheck-auto --suite ca05-booking --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `python3 ops/diagnose.py livecheck-auto --suite ca05-booking-commit --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `docker run --rm truffles-api-test-truffles-api sh -lc "pytest -q /app/tests/test_booking_appointments.py"`
  - `docker run --rm truffles-api-test-truffles-api sh -lc "pytest -q /app/tests/test_calendar_provider_sync.py"`
  - `docker run --rm truffles-api-test-truffles-api sh -lc "python3 -m compileall /app/app/services /app/app/routers"`
  - `docker run --rm truffles-api-test-truffles-api sh -lc "pip install -q ruff && ruff check /app/app /app/tests"`
- Evidence:
  - /tmp SQL dumps + /admin/health JSON
  - /tmp pytest/ruff logs
  - /tmp livecheck jsonl + emit-evidence
  - `STATE.md` запись с ссылками
- Rollback:
  - Вернуть опубликованную knowledge_version для branch_b на предыдущую (archived) версию.
  - Откатить `truffles-api/Dockerfile` до предыдущего состояния.
- No-go:
  - Подмена safe-mode поведения или client_pack требований.
  - Ручная чистка БД/trace ради “красивого” результата.
  - Запуск pytest внутри прод-контейнера с прод `.env`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: PR required (code change in Dockerfile)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: отсутствие валидного календарного токена/синхронизации может блокировать provider-ready; фиксировать как GAP при необходимости.
