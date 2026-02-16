# TP-2026-02-16-llm-reliability-kernel-a88

- Название/цель: LLM reliability kernel (P0) — закрыть критичный разрыв между LLM policy output и безопасным tool execution через typed contracts + verifier, и добавить минимальные улучшения memory/timeout recovery без новой архитектуры.
- Canon refs: `STATE.md` NOW/GAP (LLM-first reliability), `AGENTS.md` (Quality Validity Gate, Local-first validation law), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не добавлять нишевые хардкоды и новые лексиконы.
- Не ломать текущие guard/policy/law ветки и decision_meta trace-контракты.

## Scope
- Typed tool args contracts для policy-core payload на schema-уровне.
- Явный verifier-stage перед execute tool (trace/meta + safe degrade).
- Минимальное enrichment memory hints для policy-core (`active_slots`, `expected_reply_type`).
- Timeout recovery для booking expected-reply без side-effects.

## Out of scope
- Полный новый verifier framework как отдельный сервис.
- Полная иерархическая память с отдельным storage/index.
- Переписывание router/controller flow.

## Touch-list
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-02-16-llm-reliability-kernel-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-llm-reliability-kernel-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить централизованный validator для `tool_action -> tool_args` и подключить в policy-core schema.
2. Добавить verifier-stage в decision перед `execute_tool_action` с детерминированной деградацией.
3. Расширить memory profile hints и timeout recovery path для booking expected-reply.
4. Добавить/обновить контрактные тесты.
5. Прогнать целевые тесты и открыть PR.

## DoD
- Невалидный `tool_args` от policy-core отсекается до side-effect стадии.
- В `decision_meta/trace` есть явный verifier outcome (ok/invalid + reason).
- При timeout/deadline policy-core в booking expected-reply ветке срабатывает controlled collect recovery.
- Memory hints в policy-core включают `active_slots` и `expected_reply_type` (если применимо).
- Целевые тесты зелёные.

## Checks
- `pytest -q truffles-api/tests/test_llm_policy_core.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k \"llm_policy_core and (contract or timeout or memory)\"`
- `python3 -m py_compile truffles-api/app/schemas/intent.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/intent_service.py`

## Evidence
- Тест-вывод команд из секции Checks.
- decision_meta/trace assertions в тестах на verifier + timeout recovery.

## Rollback
- Revert commits этой ветки.

## No-go
- Не расширять scope за пределы verifier/contracts/memory-hints/timeout-recovery.
- Не менять поведение через demo-only pack hacks.
- Не трогать unrelated файлы.

## Risks/блокеры
- Слишком строгая валидация может отфильтровать легитимные tool payload; держать правила минимально необходимыми.
- Timeout recovery не должен перезаписывать корректный handoff flow.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-llm-reliability-kernel-a88`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect после merge.
