# TP-2026-02-19-llm-first-firebreak-program

## Название/цель
Антикризисная программа стабилизации ядра консультанта в режиме "дом горит": быстро снизить долю неправильных ответов и ошибочных tool-вызовов, затем закрепить LLM-first архитектуру без semantic-хардкодов в deterministic слое.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: booking/manual non-replay regressions)
- `STRATEGY/REQUIREMENTS.md` (запрет подгона под тесты/хардкод)
- `SPECS/SYSTEM_REFERENCE.md`
- `SPECS/CONSULTANT.md`
- `/tmp/booking_quality/booking-nonreplay-manual-a120-llm-r5/manual_summary.json`
- `/tmp/booking_quality/booking-nojudge-manual-a120-r7-replay-nonreplay/manual_summary.json`
- `/tmp/booking_quality/booking-nojudge-manual-a120-r7-replay-nonreplay/manual_findings.md`

## Incident context (факты)
- На сегодняшней траектории виден прогресс, но остаётся блокирующий semantic дефект `master -> location/hours` в manual replay.
- В текущем runtime присутствуют deterministic переопределения semantics после LLM-плана.
- Часть эвристик даёт ложные сигналы и недетерминизм порядка intent-refs.
- Бизнес-риск: неправильный ответ в критических turns -> потеря доверия/лида/записи.

## Invariant
- Продуктовый контракт строго сохраняется: `FACT / COLLECT / HANDOFF`.
- Safety/LAW/contract gates не ослабляются.
- Deterministic слой валидирует и страхует, но не подменяет смысл без high-certainty основания.
- Никакого client-specific hardcode в runtime-core.
- Любая core-правка проходит local-first realism + deterministic + replay evidence.

## Scope
- Runtime decision arbitration (`decision.py`, `info.py`, `booking.py`, `ai_service.py`).
- Tool governance (selection/args/verification/degradation).
- Chaos/interruption continuity для booking/info/handoff.
- Quality pipeline (lock/replay/manual forensic, anti-drift).
- Observability и incident response для semantic/tool regressions.

## Out of scope
- Переписывание всей платформы с нуля.
- Изменение бизнес-LAW/коммерческих правил.
- Косметический UI-polish вне связи с quality core.

## Единый рабочий протокол (обязателен)
1. `Preflight sync`:
- Работать только в актуальном `main` + целевой ветке с `Task Package`.
- Любой core-fix без канонического контекста (`STATE.md`, `AGENTS.md`, `SPECS/*`) = `BLOCKED`.

2. `LLM key contract`:
- Канонический источник ключа: `/home/zhan/truffles-main/truffles-api/.env`.
- Перед LLM quality-run ключ должен быть в окружении процесса (`OPENAI_API_KEY` непустой).
- Если ключ отсутствует, статус проверки: `BLOCKED` (не `PASS`).

3. `Container freshness gate`:
- До тестов сверять код в рабочем дереве и контейнере (`decision.py` минимум).
- При mismatch: обязательная пересборка/перезапуск тестового или runtime контейнера.
- Для детерминированных прогонов предпочтителен fresh запуск через `scripts/test_api_container.sh`.

4. `Validation order`:
- Порядок неизменный: `local realism (LLM+tools+chaos)` -> `local deterministic` -> `CI deterministic smoke`.
- Deterministic pass без LLM realism для core-поведения не принимается.
- Judge optional по режиму, но LLM run обязателен для LLM-first проверки.

5. `Evidence contract`:
- Для каждой волны фиксировать: run-команды, run-id, summary/brief, `decision_trace`, `decision_meta`, PR/CI ссылки.
- Любой вывод без evidence считается `PLAN/GAP`, а не `FACT`.

6. `Plan-vs-final delta gate`:
- Для каждого inbound с `llm_policy_core.payload.tool_action` обязателен audit `plan -> final`.
- Любой post-LLM override допускается только по whitelist reason-code (см. раздел `Override whitelist (contract v1)`).
- Override без reason-code или вне whitelist = `NO_GO` для релиза.

## Problem decomposition
1. Semantic misroute:
- mixed-intent turns с ложным доминированием non-target intent.

2. Post-LLM overwrite:
- deterministic arbitration перезаписывает валидный LLM-план.

3. Tool misuse:
- неверный tool_action при корректном пользовательском смысле.

4. State continuity:
- перебивки/expected-reply/queue/reset ломают progression.

5. Infra-induced semantic drift:
- timeout/fallback режут quality и увеличивают keyword routing.

6. Evidence gap:
- недостаёт унифицированной heatmap по реальному ущербу и распределению классов ошибок.

## Required analysis (обязательно до/параллельно внедрению)
1. Production error heatmap (7-14 days):
- Раскладка по классам: `semantic_misroute`, `tool_action_mismatch`, `expected_reply_stall`, `handoff_state_error`, `timeout_fallback`, `pack_data_gap`.
- Сегментация по каналу, клиенту, языку, типу сценария, времени суток.

2. Business impact mapping:
- Для каждого класса: доля потерянных booking progression turns, handoff leakage, unresolved loops.

3. Plan-vs-final delta audit:
- Для inbound turns собрать `llm_policy_core.payload.tool_action` vs `final decision_meta.tool_action`.
- Выделить deterministic rewrite причины и частоту.

4. Tool reliability matrix:
- Success/fail/timeout/pending по каждому tool_action.
- Contract invalid reasons + post-verifier outcomes.

5. Latency budget pressure:
- p50/p95 по `multi_intent_llm`, `policy_core_llm`, `tool_exec`.
- Частота fallback/degradation и корреляция с quality fail.

6. Pack sufficiency audit:
- Какие фейлы обусловлены `pack_data_gap`, а не router/arbitration.

7. Language robustness slice:
- RU/KK/mixed/noisy/ASR отдельно.

8. Top-fail forensic set:
- Топ-100 провальных диалогов с ручной разметкой root-cause (не только judge).

9. Gate integrity:
- Проверка сопоставимости replay-run с lock-run: сценарии, seed, reset, preflight validity.

10. Canon hygiene:
- Устранить merge-marker/док-дрифт блокеры в каноне до запуска широкого remediation wave.

## Program tracks

### Track A — Firebreak 48h (быстрая остановка кровотечения)
1. Цель:
- Срочно уменьшить самые дорогие semantic misroute/tool misuse без разрушения safety.

2. Изменения:
- Сузить semantic-remap `catalog.service_query -> catalog.location` до explicit-only.
- Убрать ложные anchor совпадения на коротких префиксах (boundary-safe matching).
- В mixed `master + hours/location` при non-explicit сигнале дать приоритет `master`.
- Стабилизировать порядок derived info refs (убрать nondeterministic `set` iteration).
- Ввести runtime kill-switch для semantic arbitration mode (safe fallback strategy).

3. DoD:
- На контрольном non-replay сценарии блокирующий `master`-defect закрыт.
- `master_control_failures == 0` на lock/replay контрольном наборе.
- `tool_action_mismatch_rate` и `info_section_miss_rate` не хуже baseline более чем на `+0.5pp`.
- Нет новых hard-fail по LAW/contract.

### Track B — LLM-first arbitration redesign (7 days)
1. Цель:
- Перевести deterministic слой из semantic decider в contract validator.

2. Изменения:
- Явно разделить стадии:
- `LLM semantic plan`
- `contract validator`
- `safety gate`
- `tool executor`
- `post-tool verifier`
- Определить whitelist случаев, где deterministic может override (только high-certainty + safety critical).
- В остальных случаях: `clarify/abstain` вместо silent reroute.
- Добавить confidence-aware arbitration и fallback policy.

3. DoD:
- `post_llm_semantic_rewrite_rate <= 2%` на сопоставимом replay.
- `post_llm_semantic_rewrite_rate <= 5%` на multilingual/chaos battery.
- 100% rewrites имеют whitelist reason-code + trace evidence.

### Track C — Tool governance hardening (7-10 days)
1. Цель:
- Правильное использование инструментов по назначению даже при хаотичных turns.

2. Изменения:
- Для каждого tool_action: строгий pre/post контракт + классификация ошибок.
- Retry/timeout стратегии по class of failure.
- Явные правила escalation на contract failure.
- Нормализованный `tool_outcome taxonomy` для наблюдаемости и triage.

3. DoD:
- `tool_action_mismatch_rate` снижен минимум на `30%` от lock-baseline.
- `tool_contract_invalid_rate` снижен минимум на `25%` от lock-baseline.

### Track D — Chaos continuity engine (7-14 days)
1. Цель:
- Устойчивый progress при перебивках/interruptions/long dialogs.

2. Изменения:
- Пересмотр expected-reply blockers по intent class.
- Защита booking slot continuity при info interrupts.
- Ограничение destructive resets контекста в pending/handoff переходах.
- Явная state-machine таблица переходов с invariant tests.

3. DoD:
- `expected_reply_stall_rate` снижен минимум на `40%` от lock-baseline.
- `booking_progression_success_rate` улучшен минимум на `+15pp` на chaos suite.

### Track E — Quality & anti-drift operating system (постоянно)
1. Цель:
- Не возвращаться в "фикснули, снова сломалось".

2. Изменения:
- Обязательный lock/replay контур с фиксированными сценариями.
- Multilingual chaos battery (RU/KK/mixed, media, interrupts, handoff, booking).
- Gate: semantic validity + tool evidence + regression tolerance.
- Weekly forensic review топ-провалов с owner sign-off.

3. DoD:
- Нет релизов без lock/replay + multilingual battery + forensic sign-off.
- Weekly forensic review закрывается owner sign-off с action items.

## Override whitelist (contract v1)
Разрешённые deterministic override reason-codes:
1. `safety_policy_block`:
- Нарушение LAW/policy/safety, подтверждённое валидатором.
2. `contract_validation_failure`:
- Невалидные/неполные аргументы tool_action, без безопасного auto-fix.
3. `required_slot_missing`:
- Для выбранного tool отсутствует обязательный слот, fallback только в `clarify/collect`.
4. `tool_unavailable`:
- Tool disabled/down/timeout budget exceeded, переход в controlled degrade.
5. `timeout_degrade`:
- LLM/tool timeout, разрешён только `clarify` или `handoff`, запрещён silent semantic reroute.
6. `idempotency_replay_guard`:
- Дедупликация/защита от повторной отправки, без изменения пользовательского смысла.

Запрещено:
- Любой override по keyword-only эвристике без reason-code.
- Подмена `catalog.service_query -> catalog.location` без explicit location/hours сигнала.

## Timeout & Degrade policy
1. При timeout `multi_intent_llm` или `policy_core_llm`:
- Не выполнять keyword-driven semantic reroute.
- Разрешены только `clarify` или `handoff` с reason-code `timeout_degrade`.
2. При timeout tool executor:
- Один контролируемый retry по policy.
- При повторном fail перевод в `handoff` или безопасный FACT fallback без выдуманных данных.
3. Все timeout/degrade события обязаны писать trace/meta и участвовать в KPI (`timeout_fallback_rate`).

## Multilingual adversarial battery (mandatory)
Минимальные классы покрытий для каждого wave release:
1. `RU`, `KK`, `mixed RU+KK` в одном сообщении.
2. Транслит и code-switch (`ru+en`, `kk+ru`, mixed slot names).
3. ASR/noise: опечатки, пропуски, перестановки, шумные токены.
4. Interruptions: booking -> info -> booking, booking -> handoff -> booking resume.
5. Adversarial phrasing: подмена букв/слов, синонимы, сокращения, многосмысленные вопрос-утверждения.
6. Long dialogs: 10-15 turns с перебивками и media turns.

## Architecture decisions (принципы реализации)
1. LLM принимает semantic решение; deterministic подтверждает корректность и безопасность.
2. Rules-as-data допустимы для safety и high-precision anchors, но не как основной semantic router.
3. Любой override должен иметь trace reason + deterministic proof.
4. Нет "невидимого" переопределения: все arbitration events обязаны логироваться в decision_trace/meta.

## Touch-list (program-level)
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `ops/diagnose.py`
- `docs/REPORTS/*` (forensic/run summaries)
- `docs/SESSIONS/*` and `docs/SESSION_INDEX.md`

## Metrics (SLO/KPI)
1. Semantic routing:
- `semantic_misroute_rate` (target: минимум `-30%` от lock-baseline на wave).

2. Tool correctness:
- `tool_action_mismatch_rate` (target: минимум `-30%` от lock-baseline).
- `tool_contract_invalid_rate` (target: минимум `-25%` от lock-baseline).

3. Continuity:
- `booking_progression_success_rate` (target: `+15pp` на chaos suite).
- `expected_reply_stall_rate` (target: минимум `-40%` от lock-baseline).

4. Reliability:
- `timeout_fallback_rate` (target: не выше baseline `+0.5pp`).
- `policy_core_degraded_rate` (target: не выше baseline `+0.5pp`).

5. User-impact:
- `hard_fail_rate` (target: не выше baseline `+0.2pp`).
- `handoff_correct_rate` (target: не ниже baseline `-0.5pp`).

6. Observability integrity:
- `decision_meta_coverage` (target: `>= 99%` inbound turns).
- `decision_trace_coverage` (target: `>= 99%` inbound turns).

7. Arbitration integrity:
- `post_llm_semantic_rewrite_rate` (target: `<= 2%` overall, `<= 5%` chaos battery).
- `rewrite_reason_coverage` (target: `100%` whitelist reason-code coverage).

## Execution plan (phased)
1. Phase 0 (Day 0-1):
- Baseline extraction + heatmap + top-100 forensic.
- Fix canon blockers (including merge-marker/doc consistency blockers).

2. Phase 1 (Day 1-2):
- Firebreak patch set + targeted contract tests + replay on blocking scenario.

3. Phase 2 (Day 3-7):
- LLM-first arbitration redesign + tool governance updates + expanded chaos tests.

4. Phase 3 (Day 8-14):
- Stabilization, canary rollout, regression burn-down, finalize operating runbook.

## Checks (minimum mandatory)
- `test -f /home/zhan/truffles-main/truffles-api/.env`
- `grep -q '^OPENAI_API_KEY=' /home/zhan/truffles-main/truffles-api/.env`
- `sha256sum truffles-api/app/routers/webhook/decision.py`
- `docker exec truffles-api sha256sum /app/app/routers/webhook/decision.py` (если используется runtime контейнер)
- `python3 -m py_compile` for touched runtime modules.
- `ruff check` for touched runtime/tests.
- `PROJECT_NAME=truffles-api-test-firebreak PYTEST_ARGS='/app/tests/test_booking_info_interrupt_contract.py' scripts/test_api_container.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id booking-lock-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality ... --scenarios-file <lock> --baseline-summary <lock_summary> --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression`

## Evidence package (for each wave)
- `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl`
- manual forensic artifacts (`manual_findings.md`, audit TSV)
- top-failures taxonomy with owner-ready interpretation
- explicit `plan-vs-final tool_action delta` table
- run command and environment matrix

## Rollout
1. Canary on controlled scenario set and selected tenants.
2. Canary `GO`:
- Нет `P0`/LAW regressions.
- Все release gates в пределах порогов.
- `rewrite_reason_coverage == 100%`.
3. Canary `NO_GO`:
- Любой override без whitelist reason-code.
- Рост `hard_fail_rate` выше `+0.2pp` от baseline.
- Рост `post_llm_semantic_rewrite_rate` выше порога.
4. Progressive rollout with kill-switches:
- semantic arbitration mode
- strict explicit routing mode
- fallback policy mode
5. Stop-the-line on regression breach.

## Rollback
- Feature-flag rollback for arbitration changes.
- Git revert by wave commits if contract/safety regression detected.
- Revert to previous stable lock baseline for release gate.

## No-go
- Нельзя лечить проблему массовым хардкодом фраз/вариаций как основной механизм.
- Нельзя отключать safety/LAW ради pass-rate.
- Нельзя принимать release без сопоставимого lock/replay evidence.
- Нельзя обновлять baseline с `INVALID`/несопоставимых run.

## Risks / blockers
- Риск локального "перефикса" одного кейса без покрытия общего распределения ошибок.
- Риск latency pressure (timeouts) как скрытого источника semantic деградации.
- Риск data-pack quality gaps, маскирующих core regressions.
- Риск процессного дрейфа (неконсистентные сценарии/базлайны).

## Ownership
- Top Architect: архитектурные решения, invariant контроль, final go/no-go.
- Brain: программа, приоритизация, acceptance, evidence completeness.
- Hands: реализация, тесты, replay, forensic artifacts.

## Acceptance
- Программа принимается только при выполнении DoD по всем трекам и подтверждённом снижении инцидентности на сопоставимых прогонах и production heatmap.
