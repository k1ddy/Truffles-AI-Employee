# TP-2026-01-27 — Console Contract Stabilization

- Название/цель: стабилизировать console-contract (Schemathesis) и синхронизировать OpenAPI с фактическим API.
- Invariant: не ослаблять RBAC/selection gating; не менять поведение прод-эндпойнтов кроме безопасной валидации.
- Scope: валидация `q` в `/cases`, OpenAPI (nullable name + maxLength), CI шаг для selection headers, регенерация типов.
- Out of scope: UI/UX правки, миграции БД, изменения ролей/онбординга, новые секреты.
- Touch-list: `.github/workflows/ci.yml`, `contracts/console_api/openapi.v1.yaml`, `truffles-api/app/routers/console.py`,
  `truffles-api/tests/test_console_cases_helpers.py`, `console-web/src/types/api.generated.ts`.
- Plan:
  1) Добавить нормализацию/валидацию `q` для `/cases`.
  2) Обновить OpenAPI (nullable agent name, maxLength для `q`).
  3) Добавить шаг выборки `X-Client-Id`/`X-Branch-Id` в console-contract CI.
  4) Перегенерировать `api.generated.ts`.
  5) Прогнать локальные проверки.
- DoD:
  - `pytest -q truffles-api/tests/test_console_cases_helpers.py` проходит.
  - Schemathesis GET-only smoke локально проходит с токеном.
  - OpenAPI и типы синхронизированы; CI console-contract зелёный.
- Checks:
  - `pytest -q truffles-api/tests/test_console_cases_helpers.py`
  - Schemathesis (как в CI) с `Authorization` + `X-Client-Id` + `X-Branch-Id`.
- Evidence:
  - Локальный вывод pytest + Schemathesis.
  - CI run URL console-contract (после PR).
- Rollback: откатить коммит; удалить новый helper; вернуть OpenAPI/CI шаги.
- No-go: не трогать CODEMAP, не менять RBAC/flows, не запускать CI для docs-only.
- Риски/блокеры:
  - Нет токена Keycloak → Schemathesis не запустится.
  - /console/v1/me не отвечает → headers не получатся, CI может упасть.
