# TP-2026-02-14-universal-consultant-p1-scale-memory-eval-a1

> Superseded: канонический единый пакет ведется в `docs/TASK_PACKAGES/TP-2026-02-14-universal-consultant-p0-contract-kernel-a1.md`.
> Этот файл оставлен только как исторический контекст.

- Название/цель: построить масштабируемый контур универсального консультанта для любых бизнесов и инструментов: `semantic parser -> planner -> tool executor -> verifier -> response composer`, с управляемой памятью длинных диалогов и cross-business quality loop, чтобы удерживать `99%` контрактной надежности на сопоставимых replay-run.
- Canon refs: `STATE.md` (NOW/GAP по quality stability), `AGENTS.md` (Local-first realism law, Anti Test-Fitting Gate, Demo-Neutral Gate), `SPECS/SYSTEM_REFERENCE.md` (decision/meta/trace контракт), `TECH.md` (quality runner и окружение).

## Invariant
- Runtime-core остается pack-agnostic и tenant-agnostic.
- Инструменты используются только по runtime capabilities и контрактам, не по нишевым эвристикам.
- Ответы опираются на проверенные tool/truth outcomes; без verified outcome нельзя выполнять рискованные действия.
- Память диалога не должна нарушать privacy/safety и не должна подменять source-of-truth.
- Никаких лексиконных расширений/подгонки под eval-набор как primary fix.

## Scope
- Ввести канонический semantic contract для intent/slots/tool-needs (языконезависимое представление).
- Добавить verifier stage после каждого tool-call с обязательным postcondition check.
- Реализовать memory layering:
- short-term working memory для текущего потока;
- retrievable long-term memory summary для длинных диалогов.
- Добавить dynamic tool routing profile:
- capability graph с учетом client/branch/channel/tool readiness.
- Расширить quality runner на stage-wise KPI и cross-business replay-matrix.
- Ввести failure-ledger pipeline (кластеризация корневых причин + приоритетный backlog фиксов).

## Out of scope
- Полный перенос на новую платформу/инфраструктуру за один цикл.
- Обучение собственной foundation-model в рамках этой фазы.
- Подмена production-governance экспериментальными offline метриками без evidence.

## Touch-list (files/tables)
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_progress_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- (если потребуется) `truffles-api/tests/test_runtime_capabilities.py`

## Plan (1..N)
1. Зафиксировать semantic contract v1 (normalized intents/slots/tool-needs) и подключить его в decision meta.
2. Добавить verifier stage для tool outcomes и fail-closed response routing при postcondition mismatch.
3. Перестроить memory path: увеличить устойчивость длинных диалогов через summarized retrieval вместо reliance на короткое history window.
4. Подключить dynamic capability graph в pre-tool routing (client/branch/channel aware).
5. Расширить `ops/diagnose.py llm-quality`:
- stage-wise метрики (`intent/tool/args/state/response`);
- cross-business replay matrix;
- regression gate на stage метриках.
6. Запустить anti-drift цикл (lock -> replay -> failure-ledger -> patch-priority).

## DoD
- На frozen replay и cross-business matrix сохраняется `contract_success_rate >= 0.99`.
- `tool_selection_accuracy >= 0.99`, `tool_args_valid_rate >= 0.995`.
- Длинные диалоги (>=30 turns) проходят без деградации state/context contracts.
- Любой рискованный tool action проходит через verifier postcondition или безопасный fallback/handoff.
- Failure-ledger автоматически строится из replay результатов и приоритизирует top regressions.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id universal-scale-lock-20260214-a1`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/universal-scale-lock-20260214-a1/scenarios.json --baseline-summary /tmp/booking_quality/universal-scale-lock-20260214-a1/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20`

## Evidence
- lock/replay artifacts: `summary.json`, `brief.md`, `responses.jsonl`, `scenarios.json`.
- stage-wise KPI report и regression diff against baseline.
- trace/meta examples для long-dialog continuity и verifier-safe fallback.
- failure-ledger (top classes, frequency, root cause, suggested fix order).

## Rollback
- `git revert SHA_FROM_THIS_BRANCH` для каждой итерации.
- Feature flags для semantic contract/verifier/memory-layer.
- При ухудшении replay относительно baseline: stop-the-line и возврат к последнему stable lock.

## No-go
- Запрещено фиксить качество через добавление нишевых словарей как основного механизма.
- Запрещено обновлять baseline при `infra_valid=false` или `semantic_valid=false`.
- Запрещено принимать изменения без evidence из trace/meta/tool outcomes.

## Риски/блокеры
- Рост latency из-за verifier и memory retrieval потребует budget tuning.
- Cross-business matrix увеличит стоимость прогонов; нужен fail-fast при регрессиях.
- Для устойчивого judge-loop требуется стабильный ключ/квоты и preflight discipline.

## Branch / Worktree
- Branch: `feat/2026-02-14-universal-consultant-p1-scale-memory-eval-a1`
- Worktree: `/home/zhan/worktrees/2026-02-14-universal-consultant-p1-scale-memory-eval-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main`, no rebase
- Cleanup: `scripts/session_end.sh --status done` + cleanup worktree/branch после merge
