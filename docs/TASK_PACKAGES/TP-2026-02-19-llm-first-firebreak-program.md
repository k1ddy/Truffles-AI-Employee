# TP-2026-02-19-llm-first-firebreak-program

> Update 2026-02-21: для текущей remediation wave использовать contract-first execution TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md` (supersedes operational plan этого документа для HQ1 closure).

## Forensic addendum (2026-03-03, mandatory sync with active canon)

### New findings (code-fact/document-fact)
1. Status drift persists between historical sections and active status matrix:
- `P0` marked `partial` in historical section but `done` in `Open Blocks Matrix`.
- `P12` marked `BLOCKED` in `STATE.md` while marked `de-scoped` for current release scope in active matrix.
2. Acceptance-chain drift in `STATE.md`:
- simultaneous `DONE` and `GAP` entries for lock/replay on different run ids make active blocker ambiguous.
3. Global requirements closure gap:
- `STRATEGY/REQUIREMENTS.md`: `checked=5`, `unchecked=50`; no machine-readable fail-closed matrix `requirement -> TP -> tests -> runtime evidence`.
4. CI realism gap:
- current CI gates do not include mandatory booking-chaos lane (`test_booking_chaos_dialogs`) as blocking release evidence.
5. Runtime reliability gap remains open:
- repeated outbox/health degradations still present in active `STATE` GAP entries.

### Program-level priority order (A->F, binding)
1. `A`: Status canon sync (`STATE` vs active matrix precedence).
2. `B`: Acceptance chain canonicalization (single active lock/replay line + historical isolation).
3. `C`: Requirements traceability fail-closed gate.
4. `D`: CI realism lane (nightly canonical chaos + regression lane).
5. `E`: LLM-first firebreak closure (staged runtime migration from deterministic semantic routing).
6. `F`: Runtime reliability closure (SLO/error-budget go/no-go + rollback contract).

### A/B status sync resolution (2026-03-03, code-fact)
- Release-scope status source of truth: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md` (`Open Blocks Matrix (code-fact, 2026-03-03)`).
- Program-scope interpretation:
  - `P0`: `done` (release + program).
  - `P12`: `release=de-scoped`, `program=blocked` (external onboarding dependency).
- `STATE.md` must not mark `P12` as `done` for current release scope; deterministic hardening artifacts are program evidence only and do not close blocked business dependency.

### Block E start status
- `E1` completed (feature-flag firebreak slice) via:
  - `docs/TASK_PACKAGES/TP-2026-03-03-e1-llm-first-firebreak-action-router-a1.md`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_message_endpoint.py`
- Scope of `E1`: env-gated blocking of deterministic semantic override branches in `_resolve_action` (`OOD/escalation/rejection`) by routing to `ai_response` path; observability added via `llm_first_firebreak_*` decision metadata.
- `E2`/`E3` remain mandatory: canary enablement with guarded runtime evidence, then extraction of remaining semantic branches from legacy router.
- `E2a` completed (point-1 remediation slice) via:
  - `docs/TASK_PACKAGES/TP-2026-03-04-e2a-interrupt-arbitration-owner-a1.md`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - Scope of `E2a`: single owner rewrite `collect -> info` for booking-active info/master interrupt turns + terminal expected-reply clear guard (`expected_reply_contract_terminal_clear`) to prevent same-turn follow-up re-derivation after `clear_expected_reply`.
- `E2b` completed (lexicon/resolver hardening slice) via:
  - `docs/TASK_PACKAGES/TP-2026-03-04-e2b-lexicon-resolver-hardening-a1.md`
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/services/pack_runtime_neutral_adapter.py`
  - `truffles-api/tests/test_pack_runtime_service.py`
  - Scope of `E2b`: RU morphology hardening for price/master interrupts (`по цене`, `к специалисту/к мастеру`) in data+adapter signal layer without new NLP runtime dependency.
- `E2c` attempted and currently blocked (process-layer, not yet semantic verdict) via:
  - `docs/TASK_PACKAGES/TP-2026-03-04-e2c-canonical-replay-canary-a1.md`
  - Attempts:
    - `booking-lock-20260304-firebreak-e2-a1-r14` -> `system_exit` (early failure)
    - `booking-lock-20260304-firebreak-e2-a1-r15` -> `invalid_preflight`
    - `booking-lock-20260304-firebreak-e2-a1-r16` -> interrupted/incomplete
    - `booking-lock-20260304-firebreak-e2-a1-r17` -> `invalid_run_economy_preflight`
    - `booking-lock-20260304-firebreak-e2-a1-r18` -> `invalid_quality_constant_preflight`
    - `booking-lock-20260304-firebreak-e2-a1-r19`, `booking-lock-20260304-firebreak-e2-a1-r21` -> manual abort due scenario-generation SLA stall (`quality_chain_controller abort` reason `manual_stop_scenario_generation_sla`)
  - Process root cause: acceptance path coupling (`chain lock precondition` + `run_economy` + `quality_constant`) plus long opaque `booking_dialog_scenarios.py` phase prevented canonical lock/replay progression.
- `E2d` completed (process-unblock slice, local/code+tests) via:
  - `docs/TASK_PACKAGES/TP-2026-03-05-e2d-acceptance-process-unblock-a1.md`
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
  - Scope of `E2d`: introduced explicit narrow override `--allow-non-canonical-lock-retry` for acceptance lock reruns with unchanged fingerprint only when previous lock is non-canonical because of process/preflight stop reasons; acceptance quality-constant keeps fail-closed by allowing this override only for lock mode (not replay), so `allow_no_code_delta` remains disallowed.
- `E2` forensic status (2026-03-04, updated after `E2e` runtime run):
  - Historical lock `booking-lock-20260304-firebreak-e2-a1-r13` stayed semantic-invalid (`wrong_action=3`, `booking_flow_break=1`, `judge_fail=1`) and served as pre-E2e baseline.
  - Fresh lock `booking-lock-20260305-firebreak-e2-a1-r22` completed with full integrity (`infra_valid=true`, `run_integrity.valid=true`, `responses=142/142`, `trace=142/142`), but remains semantic-invalid with new blocking reasons: `calendar_tool_contract_miss=2`, `stale_booking_carryover=1`, `judge_fail=1`.
  - Threshold breaches on `r22`: `hard_fail_rate=0.0141 (>0.0)` and `degraded_fallback_rate=0.1783 (>0.05)`.
  - Runtime artifact signal on `r22`: `policy_core_mode=degraded_fallback` observed on `23` turns with unresolved degrade reason-code (`policy_core_guard=unknown`).
  - Strict audit completed: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22 --status done --strict-artifacts` (`artifact_integrity.valid=true`, `manual_audit=done`).
  - Acceptance replay in same chain is fail-closed blocked: `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-20260305-firebreak-e2-a1-r22 ...` -> `chain_step_order_violation:replay:lock` because lock step status is `failed` in `/tmp/booking_quality/_chain/20260305-firebreak-e2-a1-r22.json`.
  - E2 remains open with semantic (not process) blockers; next block is targeted `E2f` contract remediation.
  - `E2f.1` deterministic slice completed locally (2026-03-04): fixed calendar outcome derivation in quality evaluator so generic `booking_blocked_reason` does not override explicit successful `calendar.get_booking` decisions (`not_found/ok/time_mismatch/...`), and expanded discounts-path booking sidecar suppression for `expected_reply_type=intent_choice` / queue-transition turns to prevent stale `Ещё был вопрос по записи...` carryover in FACT/info responses. Evidence: `ops/diagnose.py`, `truffles-api/app/routers/webhook/decision.py`, tests `truffles-api/tests/test_booking_quality_response_guard.py`, `truffles-api/tests/test_message_endpoint.py`.

### E2 Root cause (mandatory, 2026-03-04)
- Symptom:
  - Canonical lock `booking-lock-20260304-firebreak-e2-a1-r13` is infra-valid but semantic-invalid (`wrong_action=3`, `booking_flow_break=1`, `judge_fail=1`).
- Minimal reproduction:
  - Run acceptance lock with firebreak-on runtime (`LLM_POLICY_CORE_ENABLED=1`, `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=1`) and inspect failed turns from `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r13/summary.json`.
- Evidence:
  - `LLM-QUAL-...-004-13-52edaf` (`Как можно записаться к специалисту?`) -> `decision_meta.action=booking_prompt`, no `master` info section.
  - `LLM-QUAL-...-008-03-100de8` (`У меня есть вопросы по цене.`) -> `policy_core_mode=degraded_fallback`, `decision_meta.action=booking_prompt`, no `pricing` info section.
  - `LLM-QUAL-...-009-11-51f75d` (`Есть ли возможность выбрать мастера?`) -> `decision_meta.intent=service_clarify`, no `master` info section.
  - `LLM-QUAL-...-010-10-892d78` (`Я хочу записаться на 3 часа дня.`) -> `tool_action=calendar.book_slot`, `tool_decision=ok`, but turn still asks exact time (`booking_slot_stall`).
  - Code anchors:
    - Info intent detection relies on `question_like/short_query/anchor_boost` plus strict `master_resolution.explicit` in `truffles-api/app/routers/webhook/info.py` and `truffles-api/app/services/pack_runtime_service.py`.
    - Direct info reply in policy-core runs only when `not booking_wants_flow`; otherwise path goes to booking interrupt/booking flow in `truffles-api/app/routers/webhook/decision.py`.
    - `expected_reply_contract_clear` can be overwritten later by booking follow-up derivation in the same turn in `truffles-api/app/routers/webhook/decision.py`.
    - Chaos/eval deterministic suites still run with policy-core disabled (`LLM_POLICY_CORE_ENABLED=False`) in `truffles-api/tests/test_booking_chaos_dialogs.py` and `truffles-api/tests/test_demo_salon_eval.py`.
- Five Whys:
  1. Why `wrong_action` on `master/price` turns?
     - Interrupt classifier misses these phrases in active booking context.
  2. Why classifier misses?
     - Price/master recognition depends on strict lexical forms and boost gates; phrases like `по цене`, `к специалисту`, `выбрать мастера` under-trigger.
  3. Why miss escalates into booking prompt instead of info answer?
     - Routing precedence is booking-first when `booking_wants_flow=true`; direct info fast-path is gated by `not booking_wants_flow`.
  4. Why `booking_slot_stall` appears after successful tool outcome?
     - `clear_expected_reply` from tool contract is not terminal; downstream follow-up derivation can reintroduce booking prompt expectations.
  5. Why this reached acceptance late?
     - Existing deterministic chaos/eval lanes mainly exercised legacy/off-policy behavior and mocked paths, not policy-core-on runtime continuity.
- Root cause statement:
  - The system has split semantic ownership for interrupt turns (`info classifier`, `booking_wants_flow gate`, `policy tool_action`, `post-tool follow-up derivation`) without a single conflict resolver. This creates consistent false negatives for natural-language info interrupts during active booking and allows follow-up contract drift after successful calendar actions.
- Fix mechanism:
  1. Introduce a single `interrupt arbitration contract` owner before booking flow execution:
     - inputs: `message_text`, `expected_reply_type`, `booking_state`, `policy plan`, `info_signals`.
     - output: one of `info_interrupt_reply | booking_collect | handoff`, plus required `info_sections`.
  2. Move master/price robustness from ad-hoc code branches to data lexicon + resolver thresholds:
     - expand `SYSTEM_LEXICONS.yaml` entries for inflections and request forms.
     - keep `resolve_master_intent` strict mode but add explicit intent class for `choose specialist` requests via lexicon-backed signals.
  3. Enforce terminal clear rule for expected-reply:
     - if `tool_expected_contract.clear_expected_reply=true` and no conflict outcome, block downstream follow-up re-derivation in same turn.
  4. Add policy-core-on chaos lane as mandatory acceptance precondition:
     - no closure evidence from lanes where `LLM_POLICY_CORE_ENABLED=False`.
  5. Keep timeout gate fail-closed (already delivered) and add dedicated timeout-degrade info-interrupt replay scenarios.

### E2 Next-block contract (mandatory)
- Next block objective:
  - Execute `E2f` targeted semantic remediation (`calendar_tool_contract_miss`, `stale_booking_carryover`, degraded fallback budget) and re-run canonical acceptance lock.
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_calendar_book_slot_ok_terminal_clear_blocks_followup_expected_reply or policy_collect_interrupt_arbitration_rewrites_master_query_to_info"`
- Runtime check command (canonical):
  - `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-20260305-firebreak-e2-a1-r23 --pg-checklist /tmp/booking_quality/pg_checklist-firebreak-e2-a1.json --allow-pending-previous -- --base-url http://127.0.0.1:18184 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --allow-non-allowlist --judge-mode all --quality-lane acceptance --run-economy-gate block --allow-non-canonical-lock-retry --fail-on-thresholds`
- Blocked-by conditions:
  - Missing follow-up TP execution: `docs/TASK_PACKAGES/TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1.md`.
  - Missing firebreak runtime/profile alignment for acceptance lock rerun (`:18184` with `LLM_POLICY_CORE_ENABLED=1` and `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=1`).
- Owner role for closure:
  - Brain + Top Architect (acceptance sign-off), Hands (implementation + evidence bundle).

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

## Critical unresolved tails (forensic snapshot: 2026-02-20)
1. `calendar_tool_contract_miss`:
- Подтверждающий текст записи допускается при неуспешном tool outcome в части сценариев.
2. Exact-time booking gaps:
- Для запросов `Можно на 17:45?` / `Можно на 18:30?` текст уже корректный, но в части turns ломается follow-up contract (`expected_reply_type_mismatch`).
3. Contract drift `tool executor vs verifier`:
- `catalog.service_query` может вернуть валидный info outcome, который post-verifier помечает как `contract_invalid`.
4. Demo-coupling в runtime-core:
- Non-demo ветка фактически наследует demo knowledge путь через fallback adapters.
5. Timeout purity не гарантирована end-to-end:
- При timeout в `detect_multi_intent` сохраняется keyword fallback, что нарушает требование `clarify/handoff only`.
6. Release gate слишком мягкий:
- Прогон может быть `semantic_valid=true`, но содержать блокирующие strict-fail классы.

## Invariant
- Продуктовый контракт строго сохраняется: `FACT / COLLECT / HANDOFF`.
- Safety/LAW/contract gates не ослабляются.
- Deterministic слой валидирует и страхует, но не подменяет смысл без high-certainty основания.
- Никакого client-specific hardcode в runtime-core.
- Любая core-правка проходит local-first realism + deterministic + replay evidence.
- Runtime-core pack-agnostic: demo-specific knowledge допускается только в pack-adapter слоях.
- `expected_reply_type` ведётся как единый контракт состояния, а не разрозненные эвристики.
- При timeout любой semantic reroute запрещён: только `clarify/handoff` с trace reason-code.

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
- Hash mismatch `worktree vs runtime/test container` = `BLOCKED` для replay/evidence (не informational warning).

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

7. `Quality budget policy (cost-aware, mandatory)`:
- `L0` (cheap, always): static/deterministic checks (`py_compile`, `ruff`, targeted pytest for touched contracts).
- `L1` (cheap-medium, always for core): replay on canonical blocking scenarios with `--judge-mode off --allow-judge-off --max-failures 5`, manual forensic by `responses.jsonl + trace_bundle.jsonl`.
- `L2` (medium, integration cadence): replay on canonical blocking scenarios with `--judge-mode critical`, only if `L1` passed and no freshness violations.
- `L3` (expensive, release only): full lock/replay with `--judge-mode all` once per release candidate.
- `L1/L2/L3` runs are valid only with fixed scenarios (`--scenarios-file`) and `--reset-before-dialog`.

8. `Judge-off evidence contract`:
- `judge-mode off` runs are debug-only and must be marked `comparison_blocked=true` in acceptance discussion.
- `judge-mode off` evidence cannot be used to declare release readiness or canonical baseline updates.

9. `Escalation criteria L0 -> L1 -> L2 -> L3`:
- Any changes in `decision.py`, `tool_registry_service.py`, `ai_service.py`, `pack_runtime_*` => at least `L1`.
- Any behavior diff in blocking reasons, expected-reply flow, or tool contract outcomes => escalate to `L2`.
- Release candidate, baseline update, or canary go/no-go => `L3`.

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

7. Demo-neutrality gap:
- generic/fallback runtime path зависит от demo adapter и demo knowledge imports.

8. Contract schema fragmentation:
- нет единого канонического enum/schema для `tool_decision` и success outcomes.

9. Expected-reply contract fragmentation:
- `expected_reply_type` проставляется не во всех success/failure путях tool execution.

10. Release quality gate gap:
- aggregate thresholds не блокируют critical reason-set (`expected_action_mismatch`, contract drift и др.).

11. Quality budget gap:
- нет формального cost-aware протокола для частоты дорогих `judge-mode all` прогонов.

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

### Track F — Demo-neutral runtime decoupling (P0, 3-5 days)
1. Цель:
- Убрать demo-specific поведение из runtime-core и восстановить pack-agnostic контракт.

2. Изменения:
- Запретить прямые импорты `demo_salon_knowledge` вне adapter-модуля для demo pack.
- Разорвать цепочку `generic -> fallback -> demo` и ввести нейтральный generic fallback.
- Перенести pack-specific heuristics в pack-runtime adapters/data packs.

3. DoD:
- `demo_core_import_violations == 0` (core runtime modules).
- Non-demo pack path не вызывает demo adapter/knowledge.
- Replay без regressions по booking/info/handoff на lock scenarios.

### Track G — Unified tool contract schema (P0, 3-5 days)
1. Цель:
- Синхронизировать tool executor/post-verifier на единой схеме outcome.

2. Изменения:
- Ввести канонический enum/schema `tool_decision` + allowed outcomes per `tool_action`.
- Использовать один источник схемы в executor и verifier.
- Добавить contract tests на drift (`tool_decision_mismatch`, missing required fields, inconsistent success criteria).

3. DoD:
- `tool_decision_mismatch == 0` на lock/replay.
- `tool_contract_invalid_rate` не растёт и снижается минимум на `25%` от lock-baseline.
- Все `catalog.service_query` info outcomes корректно классифицируются как valid/invalid по схеме, без ad-hoc расхождений.

### Track H — Expected-reply state machine unification (P0, 3-5 days)
1. Цель:
- Устранить `expected_reply_type` drift между context/meta/tool result.

2. Изменения:
- Определить single owner для `expected_reply_type` state transitions.
- На все booking-critical tool outcomes (`ok/conflict/missing_slot/verifier_blocked`) проставлять next expected reply deterministically.
- Убрать разрозненные side-effects, где expected-reply не обновляется после содержательного ответа.

3. DoD:
- `expected_reply_type_mismatch == 0` на blocking replay scenario set.
- Все critical turns имеют согласованный `turn_expectations.reply_type` vs runtime `expected_reply_type`.
- Добавлены deterministic regression tests минимум для: `17:45`, `18:30`, `reschedule interruption`.

### Track I — Timeout purity and fail-closed routing (P0, 2-4 days)
1. Цель:
- Исключить keyword semantic routing на timeout paths.

2. Изменения:
- В `multi_intent/policy_core` timeout fallback возвращать только neutral degrade contract.
- Разрешить только `clarify/handoff` при reason-code `timeout_degrade`.
- Запретить tool-action derivation из keyword fallback при timeout.

3. DoD:
- `timeout_semantic_reroute_count == 0` в forced-timeout tests.
- Все timeout turns пишут trace/meta с `timeout_degrade`.
- Нет роста `timeout_fallback_rate` выше baseline `+0.5pp`.

### Track J — Blocking quality gate hardening (P1, 2-3 days)
1. Цель:
- Закрыть "ложно-зелёные" прогоны, где aggregate pass скрывает critical failures.

2. Изменения:
- Ввести blocking reason-set для release acceptance:
- `calendar_tool_contract_miss`
- `expected_action_mismatch`
- `tool_decision_mismatch`
- критичные `judge_fail` по booking intent contract
- Добавить gate: run invalid для release при любом reason из blocking set.

3. DoD:
- `blocking_reason_count == 0` для release replay.
- `semantic_valid=true` недостаточно без прохождения blocking gate.
- `brief.md` автоматически отражает blocking verdict.

### Track K — Deterministic budget and anti-hardcode governance (P1, ongoing)
1. Цель:
- Контролировать рост lexical hardcode в semantic path.

2. Изменения:
- Ввести budget метрики на post-LLM rewrites и keyword-driven overrides.
- Добавить static/runtime checks на regex/lexicon deltas без контрактных тестов.
- Обязать архитектурный review для каждого расширения словарей/regex в core path.

3. DoD:
- `post_llm_semantic_rewrite_rate <= 2%` (overall), `<= 5%` (chaos battery).
- `rewrite_reason_coverage == 100%`.
- Любой regex/lexicon delta в core сопровождается resolver update + regression tests.

### Wave HQ1 — Human quality firebreak (P0, immediate)
1. Цель:
- Остановить релиз при "плохих ответах консультанта", даже если структурные/контрактные метрики выглядят зелёными.

2. Источники правды:
- `/tmp/booking_quality/analysis-postfix-v7-strict-fails.tsv`
- `/tmp/booking_quality/manual-strict-fails-v7.tsv`
- `/tmp/booking_quality/booking-nojudge-manual-a120-r7-replay-nonreplay/manual_findings.md`
- `/tmp/booking_quality/booking-blocking-nojudge-trackk-smoke-a1/summary.json`
- `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv`

3. Blocking classes (release NO_GO):
- `wrong_action`: выбран не тот продуктовый исход (FACT/COLLECT/HANDOFF) относительно смысла запроса.
- `handoff_miss`: запрос на менеджера/перенос/изменение записи не приводит к `handoff` и `pending`.
- `non_actionable_reply`: ответ уклончивый/бесполезный для следующего шага клиента.
- `hallucinated_fact`: недоказанные/выдуманные факты в ответе.
- `booking_flow_break`: ответ/действие ломает ожидаемую прогрессию записи.

4. Изменения:
- Ввести обязательный `bad-turn catalog` из ручного форензика и последних replay-run.
- Ввести отдельный канонический сценарный файл `blocking_scenarios_human.json` для повторяемого replay.
- Считать run `semantic_valid=false`, если обнаружен любой class из `Wave HQ1` blocking set.
- Требовать ручной sign-off Brain/Top Architect по каталогу плохих turns перед GO.

5. DoD:
- `hq1_bad_turn_count == 0` на каноническом human-blocking сценарном наборе.
- `expected_action_mismatch == 0` и `judge_fail == 0` на `blocking_scenarios_human.json`.
- Для `reschedule/change booking` путь завершает в `handoff + pending` (без silent degrade).
- Для `master/specialist` вопросов отсутствует route в `catalog.location` без explicit location/hours anchors.
- Evidence-пакет содержит `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl`, `bad-turn catalog`.

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
- Не вычислять `tool_action`/intent через lexical fallback.
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
5. Pack-agnostic core: pack/domain специфичность живёт в adapters/packs, не в core routers/services.
6. Tool outcome schema едина для executor/verifier/evaluator.
7. Expected-reply state machine централизована и покрыта invariant tests.
8. Timeout paths fail-closed: без keyword semantic reroute.

## Touch-list (program-level)
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_generic_adapter.py`
- `truffles-api/app/services/pack_runtime_fallback_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
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

8. Demo-neutrality:
- `demo_core_import_violations` (target: `0`).
- `demo_path_usage_non_demo_tenants` (target: `0`).

9. Contract consistency:
- `tool_decision_mismatch_count` (target: `0` on lock/replay).
- `blocking_reason_count` (target: `0` for release replay).

10. Expected-reply integrity:
- `expected_reply_type_mismatch` (target: `0` на blocking scenario set).

11. Timeout purity:
- `timeout_semantic_reroute_count` (target: `0`).

12. Budget efficiency:
- `llm_quality_run_cost_per_wave` (target: controlled and pre-approved by Brain/Top Architect).
- `L3_runs_per_wave` (target: `1` for release candidate, unless explicit incident waiver).

## Execution plan (phased)
1. Phase 0 (Day 0-1):
- Baseline extraction + heatmap + top-100 forensic.
- Fix canon blockers (including merge-marker/doc consistency blockers).

2. Phase 1 (Day 1-2):
- Firebreak patch set + targeted contract tests + replay on blocking scenario.

3. Phase 2 (Day 3-7):
- LLM-first arbitration redesign + tool governance updates + expanded chaos tests.

4. Phase 3 (Day 8-10):
- Demo-neutral decoupling + unified tool contract schema (`Track F + Track G`).

5. Phase 4 (Day 10-12):
- Expected-reply unification + timeout purity hardening (`Track H + Track I`).

6. Phase 5 (Day 12-14):
- Blocking gates + deterministic budget governance + final canary (`Track J + Track K`).

## Checks (minimum mandatory)
- `test -f /home/zhan/truffles-main/truffles-api/.env`
- `grep -q '^OPENAI_API_KEY=' /home/zhan/truffles-main/truffles-api/.env`
- `sha256sum truffles-api/app/routers/webhook/decision.py`
- `docker exec truffles-api sha256sum /app/app/routers/webhook/decision.py` (если используется runtime контейнер)
- `python3 -m py_compile` for touched runtime modules.
- `ruff check` for touched runtime/tests.
- `rg -n "demo_salon_knowledge" truffles-api/app/routers truffles-api/app/services | rg -v "pack_runtime_demo_adapter.py"` (должно быть пусто после Track F).
- `rg -n "tool_decision_mismatch|expected_reply_type_mismatch|expected_action_mismatch|calendar_tool_contract_miss" /tmp/booking_quality/booking-replay-42/responses.jsonl`
- `test -f /tmp/booking_quality/blocking_scenarios.json`
- `test -f /tmp/booking_quality/blocking_scenarios_human.json`
- `PROJECT_NAME=truffles-api-test-firebreak PYTEST_ARGS='/app/tests/test_booking_info_interrupt_contract.py' scripts/test_api_container.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id booking-lock-42`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/booking-lock-42/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-42/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode off --allow-judge-off --max-failures 5 --run-id booking-blocking-nojudge-42`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode critical --fail-on-thresholds --max-failures 10 --run-id booking-blocking-critical-42`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 5 --tool-hooks auto --reset-before-dialog --judge-mode off --allow-judge-off --max-failures 5 --run-id booking-human-nojudge-42`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 5 --tool-hooks auto --reset-before-dialog --judge-mode critical --fail-on-thresholds --max-failures 10 --run-id booking-human-critical-42`
- `jq '.quality_status' /tmp/booking_quality/booking-replay-42/summary.json` (в dry-run обязателен `comparison_blocked=true`).

## Canonical blocking scenarios (mandatory artifact)
- Canonical path: `/tmp/booking_quality/blocking_scenarios.json`.
- Source: lock/replay forensic turns containing `calendar_tool_contract_miss`, `expected_action_mismatch`, `expected_reply_type_mismatch`, `tool_decision_mismatch`, critical `judge_fail`.
- Human-quality canonical path: `/tmp/booking_quality/blocking_scenarios_human.json`.
- Human source: `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv` + manual forensic artifacts.
- Ownership: Brain/Top Architect approve updates; Hands cannot silently replace this file during bugfix waves.
- Update policy: only when root-cause class changes or scenario invalidated by confirmed product decision.

## Evidence package (for each wave)
- `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl`
- `blocking_scenarios.json` checksum and generation command
- `blocking_scenarios_human.json` checksum and generation command
- manual forensic artifacts (`manual_findings.md`, audit TSV)
- `bad-turn catalog` with class labels (`wrong_action`, `handoff_miss`, `non_actionable_reply`, `hallucinated_fact`, `booking_flow_break`)
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
- Любой `blocking_reason` в release replay (`calendar_tool_contract_miss`, `expected_action_mismatch`, `tool_decision_mismatch`, critical `judge_fail`).
- `expected_reply_type_mismatch` в blocking scenario set.
- Любой `Wave HQ1` class (`wrong_action`, `handoff_miss`, `non_actionable_reply`, `hallucinated_fact`, `booking_flow_break`) в human-blocking replay.
- Dry-run evidence, поданный как quality acceptance.
4. Progressive rollout with kill-switches:
- semantic arbitration mode
- strict explicit routing mode
- fallback policy mode
- timeout purity mode
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
- Риск migration debt при выносе demo-specific логики из core.
- Риск временного роста clarify/handoff при включении timeout fail-closed без донастройки prompts.

## Ownership
- Top Architect: архитектурные решения, invariant контроль, final go/no-go.
- Brain: программа, приоритизация, acceptance, evidence completeness.
- Hands: реализация, тесты, replay, forensic artifacts.

## Acceptance
- Программа принимается только при выполнении DoD по всем трекам и подтверждённом снижении инцидентности на сопоставимых прогонах и production heatmap.
- Для acceptance обязательно: `L0 + L1 + L2`; `L3` обязателен только для release candidate / baseline update / canary go-no-go.
