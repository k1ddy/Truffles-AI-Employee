# TP-2026-02-14-universal-consultant-p0-contract-kernel-a1

- Название/цель: единый master Task Package для доведения платформы до практического уровня `99%+` по контракту поведения (`правильный ответ` или `безопасный handoff`) и корректного tool-use с LLM в runtime, без словарных костылей и подгонки под нишу.
- Canon refs: `STATE.md` (NOW/GAP), `AGENTS.md` (Canon gates, Local-first, Anti Test-Fitting), `SPECS/SYSTEM_REFERENCE.md` (trace/meta/tool contract), `TECH.md` (quality runner), `STRUCTURE.md`.
- Статус на момент обновления: frozen replay `offline-replay-20260214-p0-template-r11-local` имеет `strict_pass_rate=1.0`, `tool_evidence.valid=true`, `infra_valid=true`; открытый GAP: `semantic_valid=false` только из-за `degraded_fallback_rate`.

## Invariant
- FACT/COLLECT/HANDOFF не ломается.
- Любой рискованный action выполняется только через проверяемый контракт (trace/meta/tool outcome).
- Safety приоритетнее pass-rate (LAW/policy/pending/manager_active).
- Runtime-core остается pack-agnostic и tenant-agnostic.
- Никаких расширений лексиконов/regex как primary fix.
- Никакой подгонки под конкретный pack/нишу.

## Scope
- P0: контрактная надежность и управляемая деградация.
- P1: semantic устойчивость и long-dialog memory.
- P2: cross-business масштабирование и verifier-ensemble.
- В одном пакете, по фазам, в рамках 1-2 PR на одной ветке реализации.

## Out of scope
- Переписывание всей платформы через новый DEC.
- Замена provider stack целиком в рамках этого пакета.
- Обновление baseline по невалидным (`infra_valid=false` или `semantic_valid=false`) run.

## Touch-list (files/tables)
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/schemas/capabilities.py`
- `truffles-api/app/services/capabilities_runtime.py`
- `truffles-api/app/schemas/intent.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_booking_quality_progress_gate.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`

## Plan (1..N)
1. P0: error taxonomy + propagation (`intent_service -> decision_meta/trace`), убрать агрегированный `error`.
2. P0: intent-aware rescue matrix в `policy_core_guard` (info-first/handoff-safe/booking-safe), fail-closed.
3. P0: tool governance per tenant/branch (`allow/deny`) + runtime enforcement перед execute.
4. P0: strict tool-args/tool-outcome contracts + evidence hooks в quality runner.
5. P0: rollback flags (runtime kill-switch): `TOOL_POLICY_ENFORCEMENT`, `POLICY_CORE_RESCUE_MATRIX`.
6. P1: semantic parser contract (LLM structured JSON), снижение `degraded_fallback_rate` через budget/timing tuning и retry policy.
7. P1: memory layering для 30-80 turn диалогов (working memory + retrieval summary) без потери safety.
8. P1: stage-wise KPI в replay (`intent_parse`, `tool_select`, `args_valid`, `state_transition`, `reply_contract`).
9. P2: cross-business replay matrix + failure-ledger (root cause classes, priority fix order).
10. P2: verifier ensemble для low-confidence сложных кейсов (без side-effects до verification).

## DoD
- `contract_success_rate >= 0.99` на frozen replay (LLM runtime, не synthetic shortcuts).
- `tool_selection_accuracy >= 0.99`.
- `tool_args_valid_rate >= 0.995`.
- `missing_bot_reply = 0`.
- `tool_evidence.valid = true` и `infra_valid = true`.
- `degraded_fallback_rate <= 0.2` (или согласованный порог после review) с подтверждением root-cause trace.
- Для длинных диалогов (>=30 turns): без регресса `state_transition` и `reply_contract`.

## Checks
- Deterministic:
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- Realism + replay:
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id universal-lock-a1`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/universal-lock-a1/scenarios.json --baseline-summary /tmp/booking_quality/universal-lock-a1/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression`
- Manual verification (обязательно после каждого replay):
- `jq '.metrics.stages' /tmp/booking_quality/offline-replay-20260215-p0-r29-kernel/summary.json` и ручная проверка `controller/tool_selection/tool_args/state_transition/response_contract`.
- `jq -r 'select(.decision_meta.tool_args_contract==\"invalid\") | [.dialog_index,.turn_index,.decision_meta.tool_action,.decision_meta.tool_args_error] | @tsv' /tmp/booking_quality/offline-replay-20260215-p0-r29-kernel/responses.jsonl` (должно быть пусто либо с явным RCA).
- `jq -r '.decision_meta.controller_skipped_reason // empty' /tmp/booking_quality/offline-replay-20260215-p0-r29-kernel/responses.jsonl | sort | uniq -c | sort -nr` и ручной разбор top-skip.
- Ручная сверка `top_failures` и `brief.md` перед любым merge/rollout.

## Evidence
- `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl` для lock/replay.
- top-failures и failure-ledger по root cause классам.
- примеры `decision_meta/decision_trace` для критичных turn-типов (booking/info/handoff/tools).
- pytest outputs по таргетным suites.

## Rollback
- `git revert COMMIT_SHA` по фазам.
- Runtime flags:
- `TOOL_POLICY_ENFORCEMENT=0` (отключает policy block без отката кода).
- `POLICY_CORE_RESCUE_MATRIX=0` (отключает новый rescue path).
- При regression-breach: stop-the-line и возврат на последний valid lock-run.

## No-go
- Нельзя фиксить через расширение словарей/regex как primary approach.
- Нельзя подгонять под `demo_salon`/конкретный pack.
- Нельзя принимать DoD без trace/meta/tool-evidence.
- Нельзя обновлять baseline на INVALID run.

## Риски/блокеры
- Рост latency при verifier/memory/retrieval.
- Временный рост handoff при fail-closed policy.
- Нужна стабильная доступность LLM/judge ключей для валидных semantic-run.

## Branch / Worktree
- Branch: `feat/2026-02-14-universal-consultant-p0-impl-a1`
- Worktree: `/home/zhan/worktrees/2026-02-14-universal-consultant-p0-impl-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main`, no rebase
- Cleanup: `scripts/session_end.sh --status done` + cleanup worktree/branch после merge
