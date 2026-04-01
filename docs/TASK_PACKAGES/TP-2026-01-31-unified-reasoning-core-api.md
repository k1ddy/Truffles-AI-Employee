# TP-2026-01-31-unified-reasoning-core-api

- Название/цель: Unified Reasoning Core module/API (signals → gates → actions → compose → trace) + stage-order snapshot regression gate.
- Canon refs: `STATE.md` (DEC-018 PLAN), `docs/IMPERIUM_DECISIONS.yaml` (DEC-018), `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Детерминированный core; без оркестрации в entrypoints; decision_meta/trace на каждом раннем возврате; порядок стадий меняется только с snapshot+evidence.
- Scope: добавить core module/API; зафиксировать единый stage order snapshot + hash gate; подключить entrypoints к core; тесты на core contract.
- Out of scope: изменения паков/контента; pack-compiler/DSL; shadow-replay; DB миграции; бизнес-лексиконы в коде.
- Touch-list:
  - `truffles-api/app/services/reasoning_core.py` (new)
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/routers/decision_core.py`
  - `truffles-api/app/routers/provider_gateway.py`
  - `truffles-api/app/routers/message.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/tests/test_outbox_payload_contract.py`
  - `truffles-api/tests/test_reasoning_core.py` (new)
  - `truffles-api/tests/test_message_endpoint.py`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-01-31-unified-reasoning-core-api-a4.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Определить core API (input/output + stage order snapshot reference).
  2) Реализовать core module (детерминированный вход → оркестратор; trace/meta сохранены).
  3) Подключить entrypoints к core без изменения поведения.
  4) Добавить/проверить stage-order snapshot hash regression gate.
  5) Добавить unit tests для core contract.
- DoD:
  - Core module/API добавлен и используется entrypoints.
  - Stage order snapshot защищён hash-тестом.
  - Тесты зелёные, evidence зафиксирован в `STATE.md` до merge.
- Checks:
  - `pytest -q truffles-api/tests/test_reasoning_core.py`
  - `pytest -q truffles-api/tests/test_outbox_payload_contract.py::test_stage_order_snapshot_hash`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot"`
- Evidence:
  - CI run URL + логи тестов.
  - Запись в `STATE.md` по DEC-018 (Top Architect/Brain, до merge).
- Rollback: `git revert COMMIT_SHA`.
- No-go: entrypoint orchestration; бизнес-лексиконы в коде; изменение порядка стадий без snapshot+hash.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-01-31-unified-reasoning-core-api-a4`
  - Worktree: `/home/zhan/worktrees/2026-01-31-unified-reasoning-core-api-a4`
  - Base ref: `origin/main`
  - Merge policy: PR → main
  - Cleanup: удалить worktree/branch после merge
- Риски/блокеры:
  - Возможны неявные изменения порядка стадий; нужен hash gate + review.
