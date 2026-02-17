# TP-2026-02-17-memory-policy-kernel-a88

- Название/цель: Полноценно усилить memory-контур для policy-core без смены продуктового контракта: добавить детерминированный retrieval из `memory_profile.items`, передавать его в LLM policy input в нормализованном виде и фиксировать это в `decision_meta/decision_trace`.
- Canon refs: `AGENTS.md` (quality contract + local-first), `STATE.md` (remaining memory/systemic gaps), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять LAW/policy gates и handoff safety.
- Не вводить нишевой хардкод/лексикон для memory retrieval.

## Scope
- Добавить deterministic memory retrieval для policy-core:
  - выбор релевантных элементов из `memory_profile.items` по текущему сообщению/goal/expected-reply,
  - ограничение размера и нормализация payload,
  - прозрачная observability в trace/meta.
- Улучшить актуальность memory summary после сохранения memory items (без дорогостоящих LLM-summary).
- Добавить контрактные тесты на retrieval+meta и на нормализацию memory payload.

## Out of scope
- Векторная long-term memory с отдельным storage/index.
- Изменение consent-UX и legal/policy retention модели.
- Полная переработка planner/controller.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_intent.py`
- `docs/TASK_PACKAGES/TP-2026-02-17-memory-policy-kernel-a88.md`
- `docs/SESSIONS/SESSION-2026-02-17-memory-policy-kernel-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Реализовать helper-слой memory retrieval в `decision.py` и подключить его в сборку `policy_memory_profile`.
2. Добавить в `llm_policy_core` meta/trace поля про retrieved memory keys/count.
3. Расширить нормализацию memory profile в `intent_service.py` для безопасной передачи retrieved items.
4. Обновить существующие тесты и добавить новые контрактные кейсы.
5. Прогнать целевые проверки + один короткий replay-контур для anti-drift.

## DoD
- Policy-core получает `memory.profile.retrieved_items` (детерминированно, bounded, sanitized) при `consent_status=granted`.
- `decision_meta.llm_policy_core` и `decision_trace(stage=llm_policy_core)` содержат retrieval observability (`memory_profile_retrieved_keys`/count).
- Нет регрессии verifier/tool-routing и expected-reply contract в затронутых тестах.
- Сформирован evidence-пакет команд/результатов для PR.

## Checks
- `pytest -q truffles-api/tests/test_intent.py -k "policy_core_includes_memory_payload_when_provided"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_receives_memory_hints_and_writes_meta or memory_profile_retrieves_relevant"`
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/services/intent_service.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/offline-replay-20260215-p0-r27/scenarios.json --baseline-summary /tmp/booking_quality/offline-replay-20260215-p0-r27/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20 --run-id memory-policy-kernel-a88 --output-dir /tmp/booking_quality/memory-policy-kernel-a88 --allow-output-overwrite`

## Evidence
- `pytest` outputs for touched contracts.
- `py_compile` output.
- Replay artifacts:
  - `/tmp/booking_quality/memory-policy-kernel-a88/summary.json`
  - `/tmp/booking_quality/memory-policy-kernel-a88/brief.md`
  - `/tmp/booking_quality/memory-policy-kernel-a88/responses.jsonl`
- `STATE.md` update by Brain/Top Architect before merge (core behavior change).

## Rollback
- Revert PR commits (no schema migration in this TP).

## No-go
- Не трогать `_legacy.py` orchestration.
- Не менять packs/lexicon под тесты.
- Не делать широкие refactor вне memory path.

## Risks/блокеры
- Риск раздутия policy input -> ограничить retrieved_items по count/chars.
- Риск утечки лишних profile полей -> строгая allowlist нормализация в `intent_service.py`.
- Возможный replay noise при infra/judge нестабильности -> фиксировать `infra_valid`/`semantic_valid` в evidence.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-17-memory-policy-kernel-a88`
- Worktree: `/home/zhan/worktrees/2026-02-17-memory-policy-kernel-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks и evidence.
- Cleanup: Brain/Top Architect after merge.
