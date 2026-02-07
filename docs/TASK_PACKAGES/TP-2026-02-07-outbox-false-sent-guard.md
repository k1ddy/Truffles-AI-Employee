# TP-2026-02-07-outbox-false-sent-guard

- Название/цель: Устранить ложные маркеры доставки (`outbox=SENT` без реальной отправки) и закрыть канал повторения инцидента с test-worker на прод БД.
- Canon refs: `AGENTS.md` (P0/P1 fitness, stop-the-line), `STATE.md` (NOW: outbox/trace инварианты), `SPECS/SYSTEM_REFERENCE.md` (live-check/evidence), incident evidence `message_id=AC4EE36C8772FF23CCA84AEB1F0223ED`, `outbox_id=fe52bed9-6cdf-474a-94a4-91b9e5e21896`.
- Invariant:
  - `SENT` выставляется только при подтвержденном provider success.
  - `decision_meta/trace` и outbox observability не деградируют.
  - test-контур не должен потреблять прод outbox.
- Scope:
  - Исправить ChatFlow text send контракт: HTTP 200 + `success=false` => ошибка, не успех.
  - Исправить `TEST_MODE` guard для outbound: skip не маскируется под доставку.
  - Добавить targeted тесты на оба сценария.
  - Закрыть операционный риск drift: test stack не оставляет активный worker, способный читать прод outbox.
- Out of scope:
  - Полный редизайн delivery status lifecycle (`QUEUED/ATTEMPTED/DELIVERED`) и provider delivery callbacks.
  - Глобальная миграция всех исторических `SENT` записей.
  - Рефактор core orchestration.
- Touch-list (files/tables):
  - `truffles-api/app/services/chatflow_service.py`
  - `truffles-api/tests/test_chatflow_contract.py`
  - `truffles-api/docker-compose.test.yml`
  - `scripts/test_api_container.sh`
  - `truffles-api/app/workers/outbox.py` (только если нужен fail-fast guard)
  - `STATE.md` (фиксация evidence до merge)
- Plan:
  1) Внести contract-fix в ChatFlow send path (text) и `TEST_MODE` guard поведение.
  2) Добавить unit tests: `success=false` и `TEST_MODE skip` не дают success-result.
  3) Убрать повторяемость drift: выключить test outbox worker по умолчанию + авто-cleanup тестового compose.
  4) Прогнать targeted pytest и зафиксировать evidence.
  5) Обновить `STATE.md` (FACT + evidence + остаточные риски).
- DoD:
  - Для text-send `response.status=200` и `{"success": false}` возвращается error (`Result.err` / `False`), не success.
  - `TEST_MODE` skip не приводит к `outbox=SENT` как к ложному success.
  - Test stack после запуска `scripts/test_api_container.sh` не оставляет активные test-worker контейнеры.
  - Targeted tests green.
- Checks:
  - `pytest -q truffles-api/tests/test_chatflow_contract.py`
  - `pytest -q truffles-api/tests/test_ports.py`
  - `bash -n scripts/test_api_container.sh`
  - `cd truffles-api && docker compose -p truffles-api-test -f docker-compose.yml -f docker-compose.test.yml config`
- Evidence:
  - `/tmp/pytest_chatflow_contract_false_sent_20260207.txt`
  - `/tmp/pytest_ports_false_sent_20260207.txt`
  - `/tmp/compose_test_config_false_sent_20260207.txt`
  - `/tmp/docker_ps_after_test_compose_cleanup_20260207.txt`
  - запись в `STATE.md` (Brain/Top Architect, до merge).
- Rollback:
  - `git revert SHA_ФИКСА` в рабочей ветке; затем `ops/restart_api.sh && scripts/restart_workers.sh`.
- No-go:
  - Не трогать `_legacy.py` orchestration.
  - Не менять БД/trace руками ради evidence.
  - Не расширять scope до большого архитектурного redesign без DEC.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-outbox-false-sent-a15`
  - Worktree: `/home/zhan/worktrees/2026-02-07-outbox-false-sent-a15`
  - Base: `origin/main`
  - Merge policy: PR в `main` после green CI и фиксации evidence.
  - Cleanup: `scripts/session_end.sh --status done` + удаление worktree/branch после merge.
- Риски/блокеры:
  - Возможны existing flows, где ожидался permissive `HTTP 200` без `success`; после фикса станут явными fail cases (это ожидаемо и полезно).
