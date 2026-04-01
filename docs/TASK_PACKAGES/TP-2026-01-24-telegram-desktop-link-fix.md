# TP-2026-01-24 — Telegram desktop link + resolve error UX (P0)

- **Название/цель:** исправить deep‑link для Telegram Desktop (private topics) и показать корректную ошибку при повторном закрытии заявки.
- **Canon refs:** `SPECS/ESCALATION.md`, `docs/CONSOLE_GUIDE.md`, `contracts/console_api/openapi.v1.yaml`, `STATE.md`.

## Invariant
- Единый источник истины: все take/resolve идут через `state_service`.
- Trace/Audit обязателен для операций.
- Без ручных правок БД/trace ради evidence.

## Scope
- `telegram_desktop_link` строится через `tg://privatepost` с `thread` для топиков.
- UI показывает дружелюбное сообщение `CASE_ALREADY_RESOLVED`.
- Обновить docs с форматом desktop‑линка.

## Out of scope
- Изменение контракта Console API.
- Полный рефактор Telegram‑роутинга.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_telegram_helpers.py`
- `console-web/src/components/CaseView.tsx`
- `docs/CONSOLE_GUIDE.md`

## Plan
1) Обновить helper для desktop‑линка (`tg://privatepost`).
2) Обновить тесты helper‑функции.
3) Обработать `CASE_ALREADY_RESOLVED` в UI.
4) Обновить docs (format link).
5) Прогоны тестов.

## DoD
- Desktop‑линк открывает нужный пост/тред.
- При повторном закрытии в Console — “Заявка уже закрыта”.
- Тесты проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_telegram_helpers.py`

## Evidence
- Лог теста + CI run URL (после PR).

## Rollback
- Откат PR.

## No-go
- Любые изменения в `_legacy.py`.

## Риски/блокеры
- Поведение deep‑link зависит от клиента Telegram; fallback — web‑link.

## Branch / Worktree / Merge
- Branch: `fix/telegram-desktop-link-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
