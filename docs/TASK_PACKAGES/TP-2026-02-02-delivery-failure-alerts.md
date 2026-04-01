# TP-2026-02-02-delivery-failure-alerts

- Название/цель: Зафиксировать delivery‑failure поведение (fallback клиенту + Telegram алерт + метрики/трейсы) и убрать 500 на webhook из‑за устаревшего CHECK constraint.
- Canon refs: `STATE.md` (GAP: webhook delivery failures), `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`, `docs/runbooks/DIALOG_REPORT.md`.
- Invariant: trace/meta пишутся на ранних возвратах; никаких изменений логики в `_legacy.py`/entrypoints; outbox idempotency сохраняется.
- Scope:
  - Обновить CHECK constraint `handovers_trigger_type_check` (добавить новые trigger_type из runtime).
  - Добавить error‑fallback в webhook: ответ клиенту при внутренней ошибке + Telegram alert.
  - Логи/метрики/OTel атрибуты для delivery‑failure (server/chatflow/provider/outbox).
  - Настроить Prometheus alert rule для `delivery_failure_count_total`.
  - Зафиксировать media‑only payload без падений + тест.
- Out of scope: provider‑side автоответы при полном недоступе сервера (ChatFlow UI/ops‑настройка), крупные архитектурные изменения, новые каналы.
- Touch-list:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/services/chatflow_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/logging_config.py`
  - `truffles-api/migrations/019_add_handover_trigger_types.sql`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_branch_routing_instance.py`
  - `STRUCTURE.md`
  - `/home/zhan/infrastructure/alert_rules.yml`
- Plan:
  1) Добавить миграцию для `handovers_trigger_type_check`.
  2) Добавить delivery‑failure метрики/логи/alert‑service hooks.
  3) Catch‑all fallback в reasoning_core (rollback + ответ клиенту + Telegram).
  4) Усилить обработку media‑only preflight + тесты.
  5) Добавить alert rule в Prometheus и перезагрузить конфиг (если доступно).
  6) Обновить STRUCTURE.md и зафиксировать evidence (логи/тесты).
- DoD:
  - Webhook не падает на `minimum_data_contract` (constraint обновлён).
  - При исключении в pipeline клиент получает fallback‑сообщение (если есть instance_id + remote_jid).
  - Telegram‑алерт уходит на delivery‑failure.
  - Метрики/OTel фиксируют delivery‑failure.
  - Prometheus alert rule для `delivery_failure_count_total` добавлен и применён.
  - Тесты (min 2) проходят.
- Checks:
  - `pytest -q truffles-api/tests/test_reasoning_core.py`
  - `pytest -q truffles-api/tests/test_branch_routing_instance.py`
  - `curl -X POST http://localhost:9090/-/reload` (если Prometheus запущен)
- Evidence:
  - Логи webhook/error + alert send (docker logs).
  - Метрика delivery‑failure в `/metrics` (sample output).
  - Вывод pytest.
  - Prometheus reload (200) или `docker logs prometheus` с `Loading configuration file`.
- Rollback: откат коммита + откат миграции constraint.
- No-go: изменение поведения `/webhook`/`_legacy.py` вне необходимого; правки БД ради “красивого” evidence.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-delivery-failure-alerts-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-delivery-failure-alerts-a1`
  - Base: `origin/main`
  - Merge: PR to `main` (code)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: provider‑side автоответ при полной недоступности сервера остаётся вне scope (нужна настройка в ChatFlow).
