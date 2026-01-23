# TP-2026-01-23 — Telegram onboarding checklist + Telegram link fix + webhook health semantics (P0)

- **Название/цель:** добавить единый onboarding чек-лист и требования для Telegram‑связки, исправить ссылку “Открыть в Telegram” для топиков, убрать ложный “degraded” от старых ошибок webhook.
- **Canon refs:** `STATE.md` (NOW: Console↔Telegram workstream), `SPECS/ESCALATION.md`, `docs/PROCESSES.md`, `docs/CONSOLE_GUIDE.md`, `contracts/console_api/openapi.v1.yaml`.

## Invariant
- Web‑Console остаётся источником истины; Telegram — paging/fallback.
- Любые изменения без влияния на core‑pipeline (`_legacy.py` untouched).
- Никаких изменений БД/trace ради evidence.

## Scope
- Добавить onboarding чек‑лист + требования/входные данные в `docs/CONSOLE_GUIDE.md`.
- Исправить генерацию Telegram‑ссылки для топиков (добавить thread для topic_id).
- Улучшить health‑семантику: “degraded” только при свежей ошибке, не при устаревшей.
- Обновить unit‑тест для Telegram link helper.

## Out of scope
- Новые Telegram‑фичи (rules/quiet hours/on‑call).
- Изменение логики эскалации или state_machine.
- UI‑редизайн.

## Touch-list
- `docs/CONSOLE_GUIDE.md`
- `STRUCTURE.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_telegram_helpers.py`

## Plan
1) Добавить раздел “Onboarding Telegram” в `docs/CONSOLE_GUIDE.md` (требования, шаги, ожидаемый результат).
2) Исправить `_build_telegram_link` → учитывать `topic_id`.
3) Обновить health‑статус на “degraded” только при свежей ошибке webhook.
4) Обновить unit‑тесты для Telegram link helper.

## DoD
- В `docs/CONSOLE_GUIDE.md` есть чек‑лист onboarding с явными входными данными и шагами.
- `telegram_link` корректно открывает топик (thread) при наличии `topic_id`.
- Telegram health не показывает “degraded” на устаревшей ошибке.
- Тесты проходят; CI зелёный.

## Checks
- `pytest -q truffles-api/tests/test_console_telegram_helpers.py`
- (CI) `.github/workflows/ci.yml`

## Evidence
- CI run URL + фиксация в `STATE.md` после merge.

## Rollback
- Откат PR; восстановить прежнюю логику `_build_telegram_link` и health‑статус.

## No-go
- Изменения в `_legacy.py` или state_machine.
- Любые ручные правки БД ради “evidence”.

## Риски/блокеры
- Telegram link format для топиков зависит от клиента (web/desktop); нужно принять `?thread=` как стандарт.
- Старые ошибки Telegram webhook могут всплывать после deploy; статус должен учитывать “freshness”.

## Branch / Worktree / Merge
- Branch: `fix/telegram-onboarding-link`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
