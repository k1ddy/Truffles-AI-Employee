# TP-2026-02-18-booking-stability-runtime-a102

## Название/цель
Стабилизировать booking/runtime quality-контур после merge `f40f8147`: добавить Redis fallback diagnostics, снизить timeout-degraded path в LLM-first, закрыть residual `booking_slot_stall`, усилить check/confirm контракт, и собрать полный replay evidence с ручной проверкой каждого файла/диалога.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: residual booking_slot_stall + degraded_fallback/timeouts + quality evidence gaps)
- `docs/TASK_PACKAGES/TP-2026-02-18-booking-context-style-handoff-r2-wt-a99.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Invariant
- Не ухудшить safety outcome-контракт (`FACT/COLLECT/HANDOFF`) и trace/meta полноту.
- Не добавлять hardcode-подгон под сценарии; resolver/policy остаются pack-agnostic.
- Не менять DB/trace вручную ради evidence.
- Все quality evidence в этой сессии собираются и принимаются только после ручной проверки каждого файла и каждого диалога.

## Scope
- `T0`: sync от `origin/main` (`f40f8147`) и запуск отдельной сессии.
- `T1`: Redis fallback instrumentation + diagnose aggregates.
- `T2`: root-cause residual `booking_slot_stall` (runtime vs evaluator).
- `T3`: LLM-first timeout stabilization (budget + payload trim + stage skip under budget pressure).
- `T4`: check/confirm contract hardening через policy validation.
- `T5`: полный локальный quality replay с `--judge-mode off` и `--allow-judge-off` + ручной аудит outputs.
- `T6`: Redis A/B replay (ON vs forced fallback) на идентичных сценариях.
- `T7`: handoff evidence bundle + session/state artifacts.

## Out of scope
- Редизайн provider adapters/gateway.
- Новые бизнес-фичи вне booking/runtime качества.
- Изменение policy канона в owner-доках.

## Touch-list
- `truffles-api/app/routers/webhook/dedup.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_webhook_dedup.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SESSIONS/SESSION-2026-02-18-booking-stability-runtime-a102.md`

## Plan
1. Sync base + старт одной сессии/worktree.
2. Реализовать Redis fallback diagnostics в dedup/meta/diagnose.
3. Протрассировать `booking_slot_stall` и зафиксировать runtime/evaluator root-cause, затем минимальный фикс.
4. Внести LLM timeout stabilization в `intent_service`/`decision` без hardcode маршрутов.
5. Усилить check/confirm policy validation path для verify/confirm turns.
6. Запустить LLM quality replay (`--judge-mode off --allow-judge-off`), затем ручной построчный аудит всех outputs (`responses.jsonl`, `summary.json`, `brief.md`, trace/meta audits, findings).
7. Запустить Redis A/B replay на frozen scenarios, сделать сравнительный brief.
8. Зафиксировать evidence bundle и session handoff.

## DoD
- В decision_meta/trace есть наблюдаемость dedup backend/fallback и latency.
- `booking_slot_stall` остаток классифицирован с доказательством root-cause и закрыт фиксом или корректным evaluator-guard.
- Timeout-induced degraded_fallback снижен в replay относительно pre-fix run при сопоставимых сценариях.
- Check/confirm turns не утекают в ложный booking_prompt при деградации.
- Сформирован полный quality evidence bundle; каждый output-файл и каждый диалог проверен вручную и отмечен в ручных audit файлах.

## Checks
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18086 --scenarios-file /tmp/booking_quality/booking-stability-a102-r10-redis-on/scenarios.json --count 10 --tool-hooks auto --manager-mode simulate --pending-mode ack --reset-before-dialog --timeout-profile fast-replay --poll-timeout 35 --trace-timeout 35 --poll-interval 2 --trace-interval 2 --judge-mode off --allow-judge-off --run-id booking-stability-a102-r12-redis-on-clean2`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/booking-stability-runtime-a102/scenarios.json --count 10 --tool-hooks auto --manager-mode simulate --pending-mode ack --reset-before-dialog --judge-mode off --allow-judge-off --run-id booking-stability-runtime-a102-redis-off --output-dir /tmp/booking_quality/booking-stability-runtime-a102-redis-off --allow-output-overwrite`

## Evidence
- `/tmp/booking_quality/booking-stability-runtime-a102/{summary.json,brief.md,responses.jsonl,manual_dialog_audit.tsv,manual_trace_audit.tsv,manual_findings.md}`
- `/tmp/booking_quality/booking-stability-runtime-a102-redis-off/{summary.json,brief.md,responses.jsonl,manual_dialog_audit.tsv,manual_trace_audit.tsv,manual_findings.md}`
- SQL/trace snippets for booking/media IDs + decision_meta on last inbound.
- Session log update with exact commands and artifacts.

## Rollback
- `git revert --no-edit COMMIT_SHA1 COMMIT_SHA2` для отдельных runtime-коммитов этой сессии (без затрагивания unrelated изменений).
- Вернуть только pre-session behavior для dedup/timeout/check-confirm path без отката unrelated файлов.

## No-go
- Не добавлять scenario-specific hardcode ответов.
- Не редактировать БД/trace вручную ради метрик.
- Не создавать второй worktree/ветку в этой сессии.
- Не использовать judge-on режим в этом Task Package (фиксирован `--judge-mode off`).

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-18-booking-stability-runtime-a102`
- Worktree: `/home/zhan/worktrees/2026-02-18-booking-stability-runtime-a102`
- Base ref: `origin/main` @ `f40f8147`
- Merge policy: merge commit by Brain/Top Architect, no rebase.
- Cleanup: после merge удалить ветку и worktree.

## Риски/блокеры
- Возможны длительные зависания quality-run из-за runtime pressure; при stop-the-line фиксировать partial evidence и перезапускать с frozen scenarios.
- Redis forced fallback может потребовать env-toggle/compose override.
