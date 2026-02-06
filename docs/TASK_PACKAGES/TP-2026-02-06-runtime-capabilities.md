# TP-2026-02-06-runtime-capabilities

- Название/цель: Подключить runtime capabilities (client_capabilities) в decision/booking, чтобы booking_mode и availability_provider брались из активных capabilities, а не только из branch.booking_settings.
- Canon refs: `STATE.md` (DEC‑015 capabilities model зафиксирован), `SPECS/CONTROL_PLANE.md`, `SPECS/SYSTEM_REFERENCE.md`, `contracts/capabilities/capabilities.v1.jsonschema`.
- Invariant:
  - Поведение не меняется, если `branch.booking_settings` заполнены.
  - decision_meta/decision_trace пишутся на каждое сообщение, outbox idempotency не затронута.
  - Изоляция по tenant: capabilities читаются только в рамках `client_id` + `branch_id`.
- Scope:
  - Добавить runtime‑capabilities context (ContextVar + builder) по аналогии с runtime truth.
  - Устанавливать runtime capabilities в webhook decision до входа в пайплайн и обновлять при смене branch.
  - Использовать runtime capabilities для `booking_mode`/`availability_provider` в booking и `calendar.list_slots`.
  - Добавить unit‑тесты для builder и booking fallback.
- Out of scope:
  - Изменение схемы capabilities или миграции БД.
  - Изменения в консоли/онбординге.
  - Любые изменения паков знаний.
- Touch-list (files/tables):
  - `truffles-api/app/services/capabilities_runtime.py` (new)
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/tests/test_capabilities_runtime.py` (new)
  - `docs/TASK_PACKAGES/TP-2026-02-06-runtime-capabilities.md`
  - `docs/SESSIONS/SESSION-2026-02-06-runtime-capabilities-a10.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md` (поведенческое изменение — фиксирует Top Architect после evidence)
- Plan:
  1) Реализовать `capabilities_runtime` (ContextVar + build_runtime_capabilities) на базе `client_capabilities` + merge.
  2) Прописать установку runtime capabilities в `decision.py` и обновление при смене branch.
  3) Использовать runtime capabilities в `_resolve_booking_settings` и в `tool_registry_service` для provider health gate.
  4) Добавить unit‑тесты для runtime builder + booking fallback.
  5) Прогнать тесты, зафиксировать evidence, обновить сессию и `STATE.md` (Top Architect).
- DoD:
  - При пустых `branch.booking_settings` runtime capabilities задают `booking_mode`/`availability_provider`.
  - `calendar.list_slots` учитывает runtime availability_provider для provider health gate.
  - `pytest -q truffles-api/tests/test_capabilities_runtime.py` проходит.
- Checks:
  - `python3 -m pytest truffles-api/tests/test_capabilities_runtime.py -q`
- Evidence:
  - `/tmp/pytest_capabilities_runtime_20260206.txt`
  - Запись в `STATE.md` с ссылкой на evidence (Top Architect, до merge).
- Rollback:
  - Откатить изменения в `capabilities_runtime`, `decision.py`, `booking.py`, `tool_registry_service.py`.
- No-go:
  - Логика/оркестрация в `_legacy.py`.
  - Изменение контрактов/схемы capabilities.
  - Ручные правки БД ради evidence.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-06-runtime-capabilities-a10`
  - Worktree: `/home/zhan/worktrees/2026-02-06-runtime-capabilities-a10`
  - Base: `origin/main`
  - Merge: PR (поведенческое изменение)
  - Cleanup: `scripts/session_end.sh --status done` + удалить worktree/branch
- Риски/блокеры:
  - Возможен невалидный payload в `client_capabilities` → fallback на дефолты.
