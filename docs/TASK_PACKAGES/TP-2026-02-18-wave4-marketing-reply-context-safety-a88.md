# TP-2026-02-18-wave4-marketing-reply-context-safety-a88

- Название/цель: Гарантировать корректную обработку ответов клиентов на маркетинговые outbound сообщения без потери контекста консультанта (FACT/COLLECT/HANDOFF).
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP, `SPECS/ARCHITECTURE.md` (decision_meta/decision_trace invariants), `SPECS/CONSULTANT.md` (product contract), `SPECS/SYSTEM_REFERENCE.md` (trace/meta evidence), `TECH.md` (local-first realism gate).
- CA_ID: N/A.

## Invariant
- `decision_meta` обязателен на inbound user message.
- `decision_trace` пишется на каждом релевантном early-return и route path.
- Никаких hardcoded test-fitting веток под eval-oracle.

## Scope
- Runtime context wiring:
  - сохранять marketing outbound context (campaign/message/objective/expected-reply contract),
  - на inbound reply резолвить и подмешивать этот context в decision pipeline.
- Trace/meta:
  - дописать обязательные поля в `decision_meta` и stage marker в `decision_trace`.
- Safety behavior:
  - правильный action selection (`FACT/COLLECT/HANDOFF`) для reply на маркетинг,
  - анти-раздражение: без повторной нерелевантной рассылочной реплики.
- Tests:
  - contract tests на context-match/mismatch и fallback-safe path.

## Out of scope
- Создание кампаний/аудиторий/доставки (Wave 3).
- Новая маркетинговая контент-стратегия.
- Полный рефактор webhook decision entrypoint.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/intent_service.py` (если нужен contract extension)
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py` (контрактные кейсы без test-fitting)
- `STATE.md`

## Plan
1. Зафиксировать marketing-reply context contract (meta + trace fields + fallback rules).
2. Реализовать context resolve/inject в decision path.
3. Добавить trace/meta instrumentation и negative guards.
4. Добавить deterministic tests на matched/mismatched context.
5. Прогнать mandatory local-first behavior contour + anti-drift replay.
6. Зафиксировать evidence и обновить `STATE.md`.

## DoD
- На reply к маркетинговому outbound консультант использует корректный context.
- `decision_meta` содержит marketing context contract fields.
- `decision_trace` содержит stage для marketing-context resolve/apply.
- Нет регрессий в booking/info/handoff по обязательному local contour.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/response.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id marketing-reply-lock-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/marketing-reply-lock-<id>/scenarios.json --baseline-summary /tmp/booking_quality/marketing-reply-lock-<id>/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20`

## Evidence
- deterministic test outputs
- local realism lock + replay artifacts (`scenarios.json`, `summary.json`, `brief.md`)
- SQL/trace evidence:
  - inbound message `decision_meta` with marketing context
  - conversation `decision_trace` with marketing context stage
- `docs/REPORTS/<date>-wave4-marketing-reply-context-safety-a88.md`
- `STATE.md` FACT/GAP update (до merge для core behavior)

## Rollback
- Revert PR commit(s).
- Отключить marketing-context apply path feature flag (если введен).
- Вернуть предыдущую безопасную fallback обработку без context injection.

## No-go
- Нельзя принимать wave без local-first realism evidence.
- Нельзя менять behavior только под must_include/judge без contract tests.
- Нельзя удалять/затирать trace/meta ради "чистых" метрик.

## Риски/блокеры
- Отсутствие `OPENAI_API_KEY`/judge key блокирует валидный quality run.
- Несинхронный rollout Wave 3 может дать пустой context на части сообщений.
- Высокий runtime backlog может осложнить воспроизводимость reply timing.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave4-marketing-reply-context-safety-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave4-marketing-reply-context-safety-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
