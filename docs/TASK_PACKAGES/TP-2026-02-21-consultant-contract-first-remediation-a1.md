# TP-2026-02-21-consultant-contract-first-remediation-a1

- Название/цель: Contract-first remediation консультанта по форензике прогонов (базовое окно 11h + addendum 2026-02-24). Цель: закрепить `LLM-first semantic owner`, исключить text-fitting/hardcode в core, перевести доменную интерпретацию на `semantic-first + resolver + contracts`, масштабировать поведение на multi-niche runtime без нишевого кода в core, и вернуть устойчивое качество `>=95%` на валидном full critical replay.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`.
- STATE refs: текущий GAP по quality/run-integrity/semantic drift и architecture drift (hardcode/text-coupling).
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Problem Snapshot (FACT, forensic window = 11h)

Период: `2026-02-23T11:17Z`..`2026-02-23T22:17Z`.

Evidence (forensics):
- `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.json`
- `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.md`
- `/tmp/booking_quality/analysis-last-11h-runs-20260223T221713Z.tsv`
- `/tmp/booking_quality/analysis-last-11h-dialogs-20260223T221713Z.tsv`
- `/tmp/booking_quality/analysis-last-11h-files-20260223T221713Z.tsv`
- `/tmp/booking_quality/analysis-last-11h-bad-turns-20260223T221713Z.jsonl`

Факты:
- total_runs: `13`
- total_turns_from_responses: `314`
- strict_fail_turns: `5`
- hard_fail_turns: `1`
- judge_fail_turns: `4`
- missing_bot_reply_turns: `1`
- webhook_error_turns: `2`
- weak_oracle_turns: `21`
- Есть run-папки без полного артефакт-пакета (`summary+brief` есть, но нет `scenarios/responses/trace_bundle`).
- Критичные semantic-провалы концентрируются в `calendar.get_booking/time_mismatch` и `master`-ветке с нерелевантным `not_found_fallback`.

Системные причины (root causes):
1. В runtime есть text-coupling и phrase-sensitive branching в core-пути (архитектурный drift).
2. В тестах часть проверок все еще опирается на текстовые фразы вместо структурного контракта (`decision_meta/decision_trace`).
3. Run-economy/preflight ранее блокировал не все бесполезные replay цепочки (baseline quality/readability/canonicality).
4. Нет hard-fail инфраструктурного запрета на внесение новых keyword/regex веток в core-файлы.
5. Доменные слова/жаргон местами решаются ad-hoc в коде, а не через resolver/data contract.

## Problem Snapshot Addendum (FACT, forensic window = 3h, 2026-02-24)

Evidence (forensics):
- `/tmp/booking_quality/analysis-last3h-run-audit-20260224T124020Z.tsv`
- `/tmp/booking_quality/analysis-last3h-file-audit-clean-20260224T124129Z.tsv`
- `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r2/summary.json`
- `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r2/responses.jsonl`
- `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r3/summary.json`
- `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r3/responses.jsonl`

Факты:
- За 3 часа: `PASS=3`, `FAIL=4`, `NON-CANONICAL=6` (run-level audit).
- В non-canonical окне зафиксированы `invalid_run_economy_preflight`, `invalid_runtime_fingerprint_preflight`, `invalid_scenario_contract_preflight`, `system_exit`, `dry_run_non_evaluable`.
- На сопоставимом `code_fingerprint` + `scenario_fingerprint` один full-run дал `semantic_valid=false` (`r2`), другой `semantic_valid=true` (`r3`) при `seed=null`.
- В full critical зафиксированы timeout/degrade случаи (`policy_error:deadline_exceeded`, `timeout_degrade`) и `pipeline_ms` до `23521.83` при бюджете `18000ms`.
- `dedup_db_fallback_rate=1.0` и `dedup_fallback_reason=redis_error` в обоих full-runs (`r2/r3`), что указывает на infra-contract gap.

## Problem Snapshot Addendum (FACT, runtime provenance + anti-loop, 2026-02-26)

Evidence (forensics):
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r4-forensic/summary.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r4-forensic/problem_turns.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r4-runtime18291/summary.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r4-runtime18291/problem_turns.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r4-runtime18291-postmixfix/summary.json`

Факты:
- Replay на старом runtime (`:18290`) показал `semantic_valid=false` с `post_llm_semantic_rewrite_budget_exceeded` и `judge_fail`; в traces были override c `reason=info_ref_resolution`.
- Replay на свежем runtime (`:18291`) из текущего коммита убрал `judge_fail` и критичный semantic override drift; `strict_pass_rate` вырос с `0.9483` до `0.9828`.
- Остался один fail-turn, классифицированный как ложный `mix_info_booking` для `intent=catalog.service_query` + `tool_decision=missing_slot` (это booking collect, не semantic leak).
- Длинный replay может зависать в хвосте с `stop_reason=in_progress` и неполным артефактом (`brief.md` отсутствует), что делает run non-canonical и расходует ресурсы.
- Запуск replay поверх baseline с `baseline_canonical=false` подтверждает цикл "дорогой прогон без права на acceptance", если preflight не fail-closed.
- В lock run `booking-lock-20260226-envelope-a1-r10` обнаружен security/perf дефект: judge transport через `curl` subprocess включал `Authorization: Bearer ...` в argv процесса (`ps`) и давал дополнительный per-turn overhead.
- Remediation: judge transport переведен на in-process HTTP request (без subprocess и без секрета в argv); lock до фикса классифицирован forensic-only.

## Problem Snapshot Addendum (FACT, master intent semantics, 2026-02-27)

Evidence:
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r38/summary.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r38/responses.jsonl`

Факты:
- В replay (`r38`) зафиксирован semantic-fail `expected_info_section_miss` по `master`.
- Фактический ответ на "Я хочу узнать о ваших услугах." ушёл в `catalog.service_query` (service_choice), `info_sections` пустые.
- Это подтверждает mismatch между ожиданием сценария и желаемой семантикой: master-ответ должен быть только при явном master-запросе.

Решение (binding):
- Master-ответ выдаётся только по явным запросам о мастерах/опыте/кто делает услугу.
- Общие вопросы про услуги остаются service-query и не переводятся в master без явного сигнала.
- Реализация — через semantic resolver + pack data, без core hardcode/regex.

## Problem Snapshot Addendum (FACT, budget reality + process trust, 2026-02-27)

Evidence:
- `/tmp/firebreak_summary_scan.json`
- `/tmp/booking_quality_firebreak/summary.json`
- `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r38/summary.json`
- `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.md`
- `/tmp/booking_quality/analysis-last-3h.md`

Факты:
- По текущему скану `summary.json` (`25` run): `semantic_red=13`, `infra_red=4`, `non_canonical=7`.
- Значимая доля run в окне остается непригодной для baseline/comparison из-за process/integrity (`INVALID`, `run_incomplete`, `early_failure`, interrupted stop-reasons).
- Зафиксирован process trust gap: `manual_audit.json=status:done`, но `summary.manual_audit.status=pending` в большинстве run текущей цепочки firebreak (`25/26` проверенных run со статусом).
- В lock/replay артефактах одновременно наблюдаются:
  - зеленые deterministic/delivery метрики,
  - красные semantic-blockers (`wrong_action`, `handoff_miss`, `post_llm_semantic_rewrite_budget_exceeded`),
  что подтверждает мульти-слойный характер дефекта.
- Экономика прогонов: запуск полного `lock -> replay -> full` как каждодневного debug-цикла приводит к перерасходу токенов/времени до закрытия корневых дефектов в process + semantic + data слоях.

Решение (binding):
- Полная acceptance-цепочка `lock -> replay -> full` сохраняется как release-gate и не используется как основной inner-loop разработки.
- В ежедневном цикле вводится обязательный бюджетный dev-lane (детерминированный + micro LLM + ручной аудит), а full-chain запускается только после прохождения `Go-to-Full` критериев.

## Contradictions Found And Resolved In This TP

1. Противоречие: требование "один semantic owner" было не зафиксировано как жесткий контракт.
- Обновление: введён обязательный invariant single semantic arbiter + запрет post-hoc semantic rewrite вне whitelist reason-code.

2. Противоречие: в mandatory checks присутствовали `judge_mode off` прогонки, что конфликтует с Quality Validity/Baseline Integrity gate.
- Обновление: `judge off` оставлен только как forensic/non-acceptance lane; acceptance-цепочка только с `judge.enabled=true`.

3. Противоречие: timeout/degrade политика не закрепляла защиту factual-path в booking context.
- Обновление: добавлен контракт "booking context не ломает FACT"; при factual intent запрещен generic collect по timeout.

4. Противоречие: acceptance-chain не была зафиксирована как единая цепочка с одинаковыми fingerprint.
- Обновление: добавлен обязательный canonical flow `lock -> replay -> full`, `run_economy=block`, единый `scenario_fingerprint` и `code_fingerprint`.

5. Противоречие: TP не фиксировал control-plane детерминизм как источник semantic drift.
- Обновление: добавлен scope/plan на стабилизацию control-plane stochastic режима через structured contracts и variance control.

6. Противоречие: риск "чистого детерминизма" не был зафиксирован как архитектурный anti-pattern.
- Обновление: закреплен hybrid-контур "probabilistic semantic reasoning + deterministic policy/contracts/tool-boundary"; запрещено принимать byte-identical текст как proxy качества.

7. Противоречие: изоляция tenant tools/facts описана декларативно, но не закреплена протокольно.
- Обновление: добавлен capability-contract (tenant manifest + tool protocol gate), где core не может вызвать инструмент/факт вне allowlist текущего tenant.

8. Противоречие: forensic/debug флаги раннера могли попадать в acceptance-контур.
- Обновление: закреплён fail-closed запрет на acceptance через `--allow-no-code-delta`, `--allow-judge-off`, `--skip-outbox`, `count<10`, либо урезанный coverage без `include_media` и `handoff`.

9. Противоречие: явные info-вопросы в booking-контексте могли деградировать в pricing/service из-за stale service carryover.
- Обновление: закреплён контракт: explicit `hours/location/parking/contact` не может быть переопределён в `price_query/service_match` без явного price/duration сигнала текущего turn.

10. Противоречие: шаги исполнения были размазаны между волнами и не были зафиксированы как обязательная последовательность.
- Обновление: добавлен binding `Execution Contract (1..5)` с stop conditions и evidence для каждого шага.

11. Противоречие: runtime provenance проверялся неполно, из-за чего quality-прогоны могли идти на устаревшем container code.
- Обновление: введён обязательный runtime provenance gate (`base_url -> /admin/version -> git_commit`) с fail-closed при несовпадении ожидаемого fingerprint.

12. Противоречие: lock/replay state мог теряться при раннем останове, что провоцировало повтор неканонических lock-циклов.
- Обновление: checkpoint/failure summary обязаны сохранять `run_economy + runtime_preflight + lock/replay fingerprint state`; повтор lock при прежнем non-canonical fingerprint блокируется.

13. Противоречие: contract oracle ошибочно помечал booking collect как `mix_info_booking` в `service_query + missing_slot`.
- Обновление: зафиксирован guard: `catalog.service_query` с `missing_slot/slot_mismatch` не считается mix-leak; это валидный booking collect path.

14. Противоречие: tooling transport нарушал secret hygiene и добавлял лишний runtime overhead.
- Обновление: введён запрет на передачу API ключей через argv subprocess; judge/tool API вызовы обязаны быть in-process transport с redacted observability.

## Architecture Charter (binding)

1. LLM-first semantic owner
- Единственный владелец смысла turn (`FACT/COLLECT/HANDOFF + intent/slots/fact_refs`) — policy-core LLM.
- Любые fast-path/guards после semantic-owner не переосмысляют intent/action, а только валидируют/блокируют/деградируют контрактно.

2. Deterministic boundaries only
- Детерминизм разрешён только на границах: LAW/safety, schema validation, capability/tool protocol, idempotency/outbox/state.
- Детерминизм в core не может быть primary business router.

3. Business-agnostic core
- Core не содержит нишевых phrase/regex веток для маршрутизации ответов.
- Доменная специфика живёт в packs/resolver/manifests.

4. Graceful degrade budget (5%)
- Допускается ограниченный деградированный путь (LLM timeout/unavailable/schema mismatch), но как исключение.
- Error budget на acceptance: доля degrade-path событий не выше `0.05`; каждое событие обязано иметь `reason_code` и trace/meta evidence.

5. Context continuity
- Контекст диалога, ожидаемые слоты и capability-ограничения не теряются между turn'ами.
- Degrade-path не должен ломать factual intent и не должен сбрасывать клиента в generic collect без контрактного основания.

6. Acceptance oracle
- Приёмка строится по поведенческому контракту (`action/tool/trace/meta/outcome`), не по идентичности текста.

### Charter Precedence (anti-contradiction rule)

- При конфликте между секциями приоритет такой:
  1) `Architecture Charter (binding)` и `Invariant`,
  2) `Plan Addendum (2026-02-24, execution order)`,
  3) `Plan (1..16)`.
- Любой шаг/чек, противоречащий приоритетным секциям, считается невалидным для acceptance.

## Execution Contract (1..5, binding)

1. Governance sync first
- Синхронизировать канон/пороги до кода: charter, thresholds, acceptance envelope.
- Stop condition: обнаружен acceptance-hack или конфликт канона.

2. Semantic core remediation
- Исправлять только семантический корень (single semantic owner + boundary determinism), без phrase-based hotfix.
- Stop condition: любое post-hoc semantic rewrite вне whitelist reason-code.

3. Deterministic contract lock
- Зафиксировать детерминированные контрактные тесты на актуальные fail-turn clusters до дорогих LLM run.
- Stop condition: новый fail-turn не имеет contract test/waiver.

4. Canonical quality chain
- Запускать только `lock -> replay -> full` на сопоставимых fingerprints и валидных preflight.
- Stop condition: INVALID/NON-CANONICAL run, interrupted chain, mixed run_economy/judge mode.

5. Evidence handoff
- Обязательный пакет: `summary.json + brief.md + responses.jsonl + trace_bundle.jsonl + top_failures + exact replay command`.
- Stop condition: отсутствует любой обязательный evidence-артефакт или FACT без evidence в STATE.

## Execution Addendum (2026-02-26, mandatory)

1. TP precedence
- Этот TP является главным контрактом исполнения для текущей ветки до закрытия `P13`.
- Любые локальные решения/фиксы/прогоны, противоречащие TP, считаются `INVALID`.

2. Anti-drift process (all test tooling)
- Для quality-цепочки обязателен один и тот же процесс: `lock -> replay -> full` без смешивания lanes.
- Для replay/full обязателен фиксированный `scenarios.json` из lock и `--baseline-summary` lock.
- Сравнение метрик разрешено только между сопоставимыми fingerprint (`code + scenario + runtime + judge_mode + run_economy`).
- Повторные lock/replay без изменения fingerprint классифицируются как forensic-only и не обновляют baseline.
- Нельзя принимать acceptance по partial/non-canonical run (`run_incomplete`, `INVALID`, `NON-CANONICAL`).

3. Manual artifact analysis (MUST)
- После каждого прогона обязателен ручной аудит всех артефактов:
  - `summary.json`,
  - `responses.jsonl`,
  - `trace_bundle.jsonl`,
  - `brief.md`.
- Judge verdict не заменяет ручной аудит; judge используется как вспомогательный оркестр.
- Если ручной аудит обнаруживает конфликт judge vs contract, это фиксируется как отдельный root-cause и вход в доработку judge/rubric.
- Стандартная команда post-run аудита:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260227-a1 --status done --strict-artifacts`
- Acceptance запрещен, если `manual_audit.status != done` или `artifact_integrity.valid != true`.

4. Stop-the-line for efficiency
- Если run перешел в `run_incomplete`/`stop_reason=in_progress`, цепочка останавливается до root-cause фикса.
- Нельзя компенсировать нестабильный lock множеством новых lock попыток без анализа предыдущих артефактов.
- Любой новый run до post-run manual audit предыдущего run — нарушение процесса.
- Runtime preflight обязан применять `manual_audit_gate=block` (или эквивалентный fail-closed guard) и останавливать новый run при `manual_audit_pending:booking-lock-20260227-a1`.

5. Throughput firebreak (mandatory)
- Если в lock-run наблюдается `bot_response` без текстового payload (boolean reply) и прогон уходит в длительное polling-ожидание, run классифицируется как `forensic-only` до устранения причины.
- Если фактический throughput падает ниже устойчивого минимума (операционно: `dialogs_seen < expected` при длительном wall-time и/или `run_completion_gap`), прерывание run допустимо только после фиксации root-cause в `manual_audit`.
- После принудительного стопа обязателен полный post-run audit (`summary/responses/trace/brief`) с analyst root-causes и next steps; baseline/comparison для такого run запрещены.
- Перед следующим lock-run нужно применить remediation на уровне runner/runtime:
  - минимизировать бессмысленные poll/trace ожидания,
  - исключить ожидание assistant-message там, где webhook уже дал терминальный contract payload,
  - сохранять неизменными acceptance-гейты (`judge=all`, `include_media`, `coverage booking,info,interrupt,handoff`, `count>=10`).
- Любой lock, не завершивший полный dialog-coverage, остаётся non-canonical независимо от частичных pass-метрик.

6. Anti-loop lock gate (mandatory)
- Повторный lock с тем же `lock_fingerprint` после неканонического lock (`semantic_valid=false` или `run_integrity_valid=false` или `stop_reason in_progress/signal`) блокируется fail-closed.
- Разблокировка только двумя путями:
  - есть code/runtime delta (новый fingerprint),
  - либо явный forensic override (не acceptance lane, baseline update запрещен).
- Replay/full запрещены, пока не получен первый канонический lock (`infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`, `manual_audit.done=true`).
- Любая цепочка, где lock неканоничен, автоматически считается `forensic-only`, даже если replay/full локально были запущены вручную.

7. Canonical completion gate (mandatory)
- `P10` и `P13` считаются закрытыми только при завершённой цепочке:
  - lock (canonical) -> replay (canonical) -> full (canonical),
  - у каждого шага полный пакет артефактов и manual audit.
- Любой `INVALID`/`INCOMPLETE` шаг в цепочке обнуляет статус closure и возвращает процесс к root-cause remediation.

8. Runtime provenance gate (mandatory)
- Перед каждым lock/replay/full обязателен preflight runtime identity:
  - проверить `base_url` + `runtime_fingerprint`,
  - зафиксировать `/admin/version` (`git_commit`, `build_time`) в `summary`.
- Несовпадение ожидаемого code/runtime fingerprint -> `INVALID(runtime_commit_mismatch)`, прогон останавливается до исправления runtime.
- Сравнение baseline разрешено только если runtime provenance сопоставим между lock/replay/full.
- Commit parity недостаточен при грязном worktree: для изменённых owner-файлов (`decision.py`, `ops/diagnose.py`, related contracts/tests) обязателен hash-parity check между worktree и runtime container перед quality-run.
- Если hash-parity не соблюдён, run маркируется `forensic-only`; acceptance/baseline/comparison запрещены до rebuild runtime из текущего worktree.

9. Artifact completion gate for interrupted runs (mandatory)
- Даже при `signal/system_exit/in_progress` runner обязан писать минимальный финальный артефакт-пакет:
  - `summary.json` с terminal `status`,
  - `brief.md` c stop_reason,
  - сохранённый lock/replay fingerprint state.
- Если пакет неполный, run автоматически маркируется `forensic-only` и не допускается в comparison/baseline.
- Новый run с тем же lock_fingerprint запрещён до закрытого manual audit предыдущего interrupted run.
- Повторный lock с тем же fingerprint после non-canonical run допускается только через явный forensic override (`--allow-no-code-delta`) и остаётся вне acceptance lane до canonical lock.

10. Artifact index + resume manifest (mandatory)
- Каждый run обязан сохранять `run_manifest.json` c аргументами запуска, статусом, путями артефактов и resume-командой.
- Индекс артефактов ведётся по часам и по типам (`lock/replay/full`) в `/tmp/booking_quality/_index`, чтобы всегда было видно последние прогоны, их аргументы и статус.
- Любой новый run блокируется, если предыдущий в том же режиме имеет `manual_audit!=done` или неполный артефакт‑пакет.

11. Semantic boundary guard for booking/info (mandatory)
- Явный booking collect turn (`catalog.service_query` + `tool_decision in {missing_slot,slot_mismatch}`) не может классифицироваться как `mix_info_booking`.
- Для explicit info-intent запрещено переопределение в `price_query/service_match` без явного price/duration сигнала текущего turn.
- Любое отклонение от этого правила считается semantic contract regression и блокирует acceptance.

12. Secret-safe transport gate (mandatory)
- Запрещено передавать `OPENAI_API_KEY` или другие секреты в argv subprocess (`ps` visibility).
- Judge/tool HTTP вызовы должны выполняться in-process transport (или эквивалент с гарантированной secret redaction).
- Обнаружение секрета в argv/log artifact = `INVALID(secret_exposure_detected)` и stop-the-line до remediation.

## Execution Addendum (2026-02-27, master intent semantics mandatory)

1. Master-intent contract (mandatory)
- Intent `master`/`master_query` разрешён только при явных master-запросах: “какие мастера делают X”, “кто делает X”, “кто лучше/опытнее по X”.
- Общие вопросы “про услуги” остаются `catalog.service_query` без master-ответа.

2. Pack-driven only (mandatory)
- Ответы про мастеров строятся только из pack-данных (masters/services/experience), без домыслов.
- При отсутствии service-слота обязателен уточняющий вопрос.

3. No core hardcode (mandatory)
- Запрещены phrase/regex ветки в core для master-routing.
- Master intent определяется LLM/resolver + pack контрактом.

4. P10/P13 gate
- `P10/P13` нельзя закрывать до внедрения master-intent контракта, pack-данных и контрактных тестов.

## Execution Addendum (2026-02-27, budget-aware operating model, mandatory)

1. Two-lane operating model (mandatory)
- `Dev lane` (дешевый, обязательный): deterministic contract tests + micro LLM replay + post-run manual audit.
- `Acceptance lane` (дорогой, release-only): только canonical `lock -> replay -> full` с полными гейтами.
- Любой вывод о релизной готовности из `Dev lane` недопустим.
- Двухконтурность не является снижением quality bar: acceptance-инварианты/пороговые значения/архитектурные требования остаются неизменными.

2. Go-to-Full gate (mandatory)
- `Acceptance lane` разрешён только если одновременно:
  - `manual_audit.status=done` и синхронен в `summary + manual_audit.json`,
  - `artifact_integrity.valid=true`,
  - `weak_oracle_turn_count=0`,
  - последние dev-run не содержат `INVALID/NON-CANONICAL/INCOMPLETE`,
  - нет активных blocker-классов `wrong_action|handoff_miss|booking_flow_break` на целевых дефект-кластерах,
  - `rewrite_governance.valid=true` и `post_llm_semantic_rewrite_rate <= 0.02`.
- Нарушение любого пункта блокирует full-chain и возвращает процесс в remediation.

3. Full-chain frequency policy (mandatory)
- Full-chain не запускается "после каждого фикса".
- Разрешенный режим: milestone/candidate runs (по готовности gate), либо фиксированное окно (например, 1 раз в 24-48 часов) при выполненном Go-to-Full.
- Любой full-run вне этой политики маркируется forensic-only и не используется для acceptance.
- Запрет: использовать budget/time/token ограничения как аргумент для смягчения acceptance требований или для внедрения workaround в production path.

4. Vertical remediation packets (mandatory)
- Исправления выполняются пакетами "semantics + contracts + data + evidence", а не одиночными hotfix.
- Минимум 3 обязательных пакета:
  - `Packet A`: process trust (`manual_audit sync`, artifact completion, preflight fail-closed),
  - `Packet B`: semantic routing (`master/service`, action ownership, rewrite budget),
  - `Packet C`: pack/data contracts (masters/services/experience + slot requirements).
- Частичное закрытие пакета не считается выполнением этапа.

5. Past -> Present -> Future context contract (mandatory)
- Каждый этап обязан явно фиксировать:
  - `Past`: что уже делали и какой эффект подтвержден evidence,
  - `Present`: какие root-causes активны сейчас,
  - `Future`: какой следующий атомарный пакет закрывает какую бизнес-потерю.
- Запись "сделано" без этой триады считается неполным handoff и не может быть использована как acceptance-evidence.

6. Budget-aware stop-the-line (mandatory)
- При росте `INVALID/NON-CANONICAL` или process-trust gap (audit mismatch) дорогие LLM прогоны останавливаются до фикса runner/process слоя.
- Токены/время считаются ограниченным ресурсом качества; расход без прохождения Go-to-Full трактуется как process regression.
- Если полноценная проверка временно недоступна, статус этапа = `BLOCKED`; "упрощенный pass" по бюджету запрещен.

## Execution Addendum (2026-02-28, runtime reliability root-fix, mandatory)

1. Root-cause scope (mandatory)
- Текущий активный blocker после process-fix: `semantic_valid=false` при `infra_valid=true` из-за `degraded_fallback_rate > 0.05` в timeout-degrade кластере.
- Root-cause считается runtime reliability path (`policy_core_degraded_collect/timeout_degrade`), а не oracle/text mismatch.

2. Quality-constant protection (mandatory)
- Порог `degraded_fallback_rate <= 0.05` не смягчается.
- Запрещено снижать acceptance threshold, отключать judge/coverage или менять quality lane как workaround.

3. Single-degrade-per-context contract (mandatory)
- Для `timeout_degrade` в booking collect допускается только один degrade-turn на conversation context.
- Повторный `timeout_degrade` в том же context обязан приводить в `clarify_limit -> HANDOFF` (или эквивалентный contract escalation), а не к повторному `degraded_collect`.
- Любой второй подряд `policy_core_mode=degraded_fallback` на том же timeout-контексте без escalation = regression.

4. Observability contract (mandatory)
- Повторный timeout-degrade обязан быть наблюдаем через `decision_trace`/`decision_meta`:
  - `reason_code=timeout_degrade`,
  - retry counter/limit,
  - explicit decision (`timeout_booking_limit`/`clarify_limit`/`handoff`).
- Silent fallback without retry metadata запрещён.

5. Deterministic gate before replay (mandatory)
- Обязательный тест: timeout booking-safe fallback first-hit -> collect prompt; second-hit (same context) -> clarify-limit escalation.
- Acceptance replay разрешён только после зелёного deterministic test для этого контракта.

6. Completion criteria for this packet (mandatory)
- Dev-lane replay с `judge-mode all` на фиксированном hotset показывает:
  - `infra_valid=true`,
  - `run_integrity_valid=true`,
  - `degraded_fallback_rate <= 0.05`,
  - без новых `wrong_action|handoff_miss|booking_flow_break` blocker-классов.

## Invariant

- Не менять продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять LAW/policy/safety hard-gates.
- Runtime core остается pack-agnostic.
- Один semantic arbiter владеет итоговым решением turn (`FACT/COLLECT/HANDOFF + intent/slots/fact_refs`); downstream-слои только валидируют/блокируют, но не переосмысляют смысл.
- Core не использует phrase/regex branching как primary бизнес-маршрутизацию.
- `decision_meta`/`decision_trace` обязательны и консистентны на каждом user turn.
- INVALID/INCOMPLETE run не участвует в baseline/comparison.
- Никаких hardcoded phrase-branching в core-path (`decision/booking/tool_registry`) как способа фикса качества.
- Timeout/degrade не должен превращать factual запрос в generic collect; только контрактный degrade-path с reason-code.
- Доля degrade-path событий в acceptance-цепочке не выше `0.05`.
- Acceptance только по канонической цепочке `lock -> replay -> full` при `run_economy=block` и сопоставимых fingerprint.
- В booking-контексте explicit info-intent (`hours/location/parking/contact`) не может переезжать в `price_query/service_match` без явного price/duration сигнала текущего turn.
- Любой fallback/override, меняющий semantic class turn, обязан писать `reason_code` в trace/meta.
- Runtime provenance (`runtime_fingerprint` + `/admin/version.git_commit`) должен совпадать по всей канонической цепочке.
- Interrupted run обязан завершаться terminal summary/brief; "вечный in_progress" для acceptance запрещён.
- Master intent допускается только при явном master-запросе; общие вопросы про услуги остаются service-query.
- Ответы про мастеров строятся только из pack-данных; без фактов — уточнение/эскалация.
- Acceptance lane запускается только после прохождения Go-to-Full; full-chain не используется как постоянный debug-цикл.
- `manual_audit` статус обязан быть консистентен между `summary` и `manual_audit.json`; рассинхрон = process-blocker.
- Бюджетные ограничения не меняют целевую архитектуру и не легализуют обходные решения в core/runtime.

## Scope

- Перевести доменную интерпретацию на resolver-contract и удалить text-coupling из core.
- Ввести fail-closed гейты, которые блокируют добавление хардкода в core на уровне CI.
- Перестроить тестовый oracle на структурные сигналы (`action/intent/slots/outcomes/trace`), а не на ответные фразы.
- Довести run-quality контур до стабильного anti-drift цикла (lock/replay/acceptance).
- Стабилизировать control-plane stochastic поведение (policy-core/multi-intent/answer-interpreter/consult controller) через structured contracts и variance control, без требования byte-identical ответа.
- Зафиксировать boundary-only детерминизм: deterministic code не подменяет semantic-owner решения.
- Закрыть infra-contract gap для dedup/cache budget path (Redis contract + fallback observability gate).
- Ввести business-agnostic capability-contract: каждый tenant/ниша использует только свои tools/packs через capability manifest, без нишевого кода в core.
- Зафиксировать protocol boundary для external tools (MCP-compatible adapter): migration без vendor lock-in и без hardcode provider semantics в core.
- Ввести master-intent семантику через resolver + pack-данные (masters/services/experience), без core hardcode.

## Architectural Position (explicit)

- Семантический арбитр остаётся вероятностным (LLM semantic reasoning), а не "чисто детерминированным".
- Детерминизм применяется только там, где это контракт/безопасность:
  - policy/LAW/safety gates,
  - schema validation,
  - tool capability allowlist,
  - idempotency/outbox/state invariants.
- Acceptance и регрессия проверяются по поведенческим контрактам (`action/tool/trace/meta/outcome`), а не по идентичности текста.

## Technology Mapping (2025 targeted, non-generic)

1. Semantic arbiter contract via structured outputs
- Технология: structured JSON outputs для LLM policy-core (Responses-style schema enforcement).
- Почему: один владелец semantic decision, меньше post-hoc reinterpretation, fail-closed при schema mismatch.
- Где в системе: `decision.py` + policy-core adapter + `decision_meta` schema.

2. Tool boundary via MCP-compatible capability gateway
- Технология: протокол инструментов (MCP-compatible) + tenant capability manifest (`allowed_tools`, `allowed_fact_scopes`, `handoff_policy`).
- Почему: business-agnostic масштабируемость; новая ниша подключает свои инструменты/факты без изменений core.
- Где в системе: `tool_registry_service.py`, `pack_runtime_service.py`, onboarding/control-plane capability provisioning.

3. Pack Query Engine with hybrid retrieval
- Технология: dense+sparse retrieval + strict metadata filters (tenant/branch/pack scope) + margin abstain.
- Почему: уход от phrase-fitting и устойчивость к перефразам/типо/mixed language.
- Где в системе: `pack_runtime_service.py` + pack compiler artifacts + query contract.

4. Contract-first eval stack (agentic, not phrase-based)
- Технология: action/tool/trace graders, multi-seed reproducibility, scenario fingerprint lock.
- Почему: quality-приёмка по поведению, а не по тексту; контроль stochastic drift.
- Где в системе: `ops/diagnose.py` + `test_booking_quality_*` + run-economy gates.

5. Durable workflow boundary for long-running paths
- Технология: durable/background execution only для long tasks (handoff/media/heavy retrieval), без переноса semantic ownership из core.
- Почему: таймауты и `deadline_exceeded` не должны ломать turn outcome.
- Где в системе: async outbox/handoff/media pipeline, без переписывания turn arbiter.

## Out of scope

- DEC-уровневая полная замена оркестрации.
- Изменение бизнес-политик/LAW.
- Глобальная миграция всех исторических паков за один PR.

## Touch-list

- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/consult_pack_service.py`
- `truffles-api/app/services/tool_protocol_gateway.py` (new, if absent)
- `truffles-api/app/services/capability_manifest_service.py` (new, if absent)
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_calendar_slot_response_contract.py`
- `truffles-api/tests/test_master_info_flow.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_tool_capability_manifest.py`
- `truffles-api/tests/test_tool_protocol_gate.py`
- `truffles-api/tests/test_pack_query_engine_contract.py`
- `truffles-api/tests/test_pack_query_engine_abstain.py`
- `truffles-api/tests/test_cross_domain_capability_isolation.py`
- `truffles-api/tests/test_booking_quality_*.py`

## Plan (Atomic LLM-First, binding)

### Analysis Gate (обязателен перед каждым пунктом)
- `AG-1 Evidence`: собрать факты из `summary/responses/trace/meta` по конкретному дефекту.
- `AG-2 Contract Delta`: зафиксировать, какой поведенческий контракт нарушен (`action/tool/slots/reason_code`).
- `AG-3 Design Decision`: явно разделить probabilistic (`LLM/resolver`) и deterministic boundary.
- `AG-4 Risk/Rollback`: описать риск, обратимую миграцию, rollback-команду.
- `AG-5 Test Matrix`: утвердить набор deterministic + LLM checks до начала кода.

### Atomic Work Plan
1. `P0 Governance Lock`
- Синхронизировать charter/TP/runner-гейты без противоречий.
- Зафиксировать dual-lane приемку: semantic vs delivery.
- Stop-the-line: любой acceptance через debug-режимы/неполный coverage.

2. `P1 Semantic Decision Envelope`
- Ввести единый `Semantic Decision Envelope` как source of truth turn:
  - `action_class`, `intent_class`, `tool_action`, `slot_candidates`,
  - `fact_refs/entity_refs`, `confidence`, `abstain_reason`,
  - `override_reason_codes`, `resolver_id/version`.
- Downstream не может менять semantic-class без whitelist reason-code.

3. `P2 Structured Policy-Core Adapter`
- Schema-first structured output для policy-core.
- Любой schema mismatch/timeout -> controlled degrade с обязательным reason-code.
- Запрет silent fallback без trace/meta.

4. `P3 Semantic Firewall`
- Реализовать fail-closed: deterministic слой может только `validate/block/replan`.
- Запрет post-hoc semantic rewrite вне whitelist policy overrides.
- Каждый override/degrade обязан писать `reason_code`.

5. `P4 Expected-Reply Refactor`
- Оставить expected-reply как slot-evidence, а не semantic-owner.
- Исключить захват маршрута `booking -> info` из-за stale expected-reply.
- Выровнять clear/set контур expected-reply и session memory.
- Добавить master-intent контракт: явные master-запросы -> master intent, общие услуги -> service-query.

6. `P5 Pack Query Engine v2`
- Hybrid retrieval: lexical recall + semantic rerank + strict tenant/branch filters.
- Margin-based abstain: низкая уверенность -> `COLLECT/HANDOFF`, без guessing.
- Добавить provenance bundle (`pack_id/entity_id/source_ref/confidence`).

7. `P6 Capability Manifest + Protocol Gate`
- Tenant capability manifest (`allowed_tools`, `allowed_fact_scopes`, `handoff_policy`).
- MCP-compatible protocol gate deny-by-default до фактического вызова инструмента.
- Runtime не может вызвать tool/fact вне allowlist tenant.

8. `P7 Core De-hardcoding Sweep`
- Удалить business phrase/regex routing из core (`decision/booking/info/tool_registry`).
- Оставить в core только boundary validation/safety/idempotency/outbox.
- Нишевая семантика допускается только в packs/resolver/manifests.

9. `P8 Acceptance Engine Split`
- Ввести два независимых статуса:
  - `semantic_acceptance`: качество поведения по контракту,
  - `delivery_acceptance`: транспорт/доставка.
- `CHATFLOW_BILLING_BLOCKED` классифицировать как `delivery_waiver_billing`,
  не блокирующий `semantic_acceptance`.
- Baseline для семантики не должен ломаться из-за billing-blocked в текущем режиме оплаты.

10. `P9 Contract Test Migration`
- Перевести regression oracle на `decision_meta/decision_trace/action/tool/state`.
- Текстовые сравнения ответов исключить как primary oracle.
- Зафиксировать детерминированные тесты на все active fail-turn clusters.

11. `P10 Canonical Quality Chain`
- Acceptance только по `lock -> replay -> full` на сопоставимых fingerprint.
- Multi-seed drift для контрактных метрик (`action/tool/reason-code drift`).
- INVALID/INCOMPLETE run не участвует в baseline/comparison.

12. `P11 Budget-Go-To-Full Control`
- Внедрить fail-closed `Go-to-Full` preflight и lane enforcement в runner.
- Синхронизировать `manual_audit` статус между артефактами и summary агрегатами.
- Блокировать full-chain при process trust gap.

13. `P12 Cross-domain Hardening`
- Проверка pack-agnostic поведения на минимум 2 несалонных capability-pack.
- Запрет domain-specific branching в runtime core.

14. `P13 Canary + Rollback`
- Stage A: deterministic contracts + micro replay.
- Stage B: lock/replay/full acceptance.
- Stage C: canary rollout с stop-the-line при regression.

15. `P14 Evidence + STATE Handoff`
- Обязательный пакет: `summary`, `brief`, `responses`, `trace_bundle`,
  top-failures, replay/full commands, contract drift digest.
- FACT в `STATE.md` только с evidence.

16. `P15 Timeout-Degrade Reliability Remediation`
- Убрать повторный timeout-degrade collect в booking контексте через `single-degrade-per-context`.
- На втором timeout-degrade того же intent/context делать contract escalation (`clarify_limit -> HANDOFF`) вместо второго collect.
- Зафиксировать turn-level evidence и deterministic regression test до следующего judge replay.

## Acceptance Requirements (binding)

### A. Semantic Acceptance
- `semantic_valid=true`
- `strict_pass_rate>=0.95`
- `hard_fail_turns=0`
- `reason_code` покрывает все override/degrade случаи (`rewrite_reason_coverage=1.0`)
- Нет несанкционированного semantic rewrite вне whitelist.
- `judge_fail` блокирует semantic lane только при подтверждённом deterministic semantic contract-fail; standalone judge fail считается advisory и требует manual-audit root-cause.

### B. Delivery Acceptance
- Отдельный verdict, не смешивается с semantic baseline.
- `CHATFLOW_BILLING_BLOCKED` допустим как `delivery_waiver_billing` в текущем режиме
  (оплата не активна) при обязательной фиксации в evidence.
- Другие delivery-инциденты классифицируются и учитываются в отдельном error budget lane.

### C. Canonical Run Integrity
- Acceptance-run только при:
  - `run_economy.mode=block`,
  - `judge.enabled=true`,
  - `count>=10`,
  - `include_media=true`,
  - `scenario_coverage=booking,info,interrupt,handoff`,
  - сопоставимых `code_fingerprint + scenario_fingerprint`.
- INVALID/NON-CANONICAL/INCOMPLETE run исключаются из baseline/comparison.
- Повтор lock с неизменным fingerprint после неканонического lock запрещён (anti-loop gate).
- Replay/full разрешены только после первого канонического lock и завершённого manual audit этого lock.
- Обязательный post-run audit gate:
  - `manual_audit.status=done`,
  - `artifact_integrity.valid=true`,
  - root-cause digest заполнен для всех `critical/high` findings.
- Runtime preflight обязан подтвердить `runtime_commit_match=true` между chain-step и ожидаемым кодом ветки.
- Master intent допустим только для явных мастер-запросов; общие запросы про услуги остаются service-query.
- Master-ответы должны ссылаться на pack-данные; отсутствие данных -> уточнение/эскалация.

## Testing Methods (binding)

1. `Static Contract Gates`
- AST/Semgrep запрет бизнес-phrase/regex routing в core.
- CI fail-closed при новых нарушениях.

2. `Schema + Contract Unit Tests`
- Structured-output schema tests для policy-core.
- Envelope integrity tests (`action/tool/slots/reason_code/provenance`).

3. `Integration Contract Tests`
- Webhook -> policy -> protocol gate -> tool -> trace/meta.
- Проверки на запрет post-hoc semantic rewrite.

4. `Deterministic Regression Suite`
- Turn-level tests по контракту для известных fail-clusters.
- Без byte-identical сравнения ответов.

5. `LLM Quality Suite`
- Canonical `lock -> replay -> full`.
- Multi-seed contract drift report (`seed 7/19/42` минимум).
- Judge graders должны быть узкими и контрактными (да/нет по `action/tool/trace/meta`); free-form judge summary не может быть единственным блокером acceptance.

6. `Budget-aware Lane Suite`
- Dev lane обязателен для каждого fix-пакета: deterministic + micro replay + manual audit.
- Acceptance lane запускается только после Go-to-Full и не заменяется dev lane метриками.
- Проверка консистентности `manual_audit` (`summary` vs `manual_audit.json`) обязательна перед full.

7. `Dual-Lane Validation`
- Semantic lane: contract metrics.
- Delivery lane: transport metrics + waiver taxonomy.

8. `Cross-domain Capability Suite`
- Isolation tests tenant A/B + несалонные packs.

9. `Master Intent Contract Suite`
- Сценарии “какие мастера делают X / кто лучше / опыт по X” -> master intent.
- Сценарии “какие услуги вы оказываете” -> service-query, без master.
- Проверки по `intent/action/tool/trace`, без текст-ораклов.

10. `Timeout-Degrade Reliability Suite`
- Deterministic test на booking timeout-degrade:
  - first-hit -> slot-driven collect,
  - second-hit same context -> clarify-limit escalation/handoff.
- Replay check на фиксированном сценарии подтверждает снижение `degraded_fallback_rate` до контрактного порога без ослабления gates.

## Execution Waves (binding)

1. `Wave 0`: `P0`-`P1` governance + semantic envelope lock.
2. `Wave A`: `P2`-`P4` semantic owner remediation.
3. `Wave B`: `P5`-`P7` retrieval/capability/core de-hardcoding.
4. `Wave C`: `P8`-`P11` acceptance split + quality chain + budget-go-to-full control.
5. `Wave D`: `P12`-`P14` cross-domain + rollout + evidence closure.

Forensic only (not acceptance):
- `judge_mode off/critical` допускается только в diagnostic lane.
- `--allow-no-code-delta`, `--allow-judge-off`, `--skip-outbox` запрещены для acceptance.

## Evidence

- Forensics 11h:
  - `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.json`
  - `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.md`
  - `/tmp/booking_quality/analysis-last-11h-bad-turns-20260223T221713Z.jsonl`
- Forensics 3h addendum (2026-02-24):
  - `/tmp/booking_quality/analysis-last3h-run-audit-20260224T124020Z.tsv`
  - `/tmp/booking_quality/analysis-last3h-file-audit-clean-20260224T124129Z.tsv`
  - `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r2/summary.json`
  - `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r2/responses.jsonl`
  - `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r3/summary.json`
  - `/tmp/booking_quality/firebreak-full-critical-4defects-v2-20260224-a1-r3/responses.jsonl`
- Budget/process trust addendum (2026-02-27):
  - `/tmp/firebreak_summary_scan.json`
  - `/tmp/booking_quality_firebreak/summary.json`
  - `/tmp/booking_quality_firebreak/booking-replay-20260226-envelope-a1-r38/summary.json`
- Quality run artifacts:
  - `/tmp/booking_quality/RUN_ID/summary.json`
  - `/tmp/booking_quality/RUN_ID/brief.md`
  - `/tmp/booking_quality/RUN_ID/responses.jsonl`
  - `/tmp/booking_quality/RUN_ID/trace_bundle.jsonl`
  - `/tmp/booking_quality/RUN_ID/manual_audit.md`
  - `/tmp/booking_quality/RUN_ID/manual_audit.json`
- Contract evidence:
  - `decision_meta` sample rows,
  - `decision_trace` sample rows with resolver/policy/tool stages,
  - acceptance command + output digest.

- External research inputs (2025, primary):
  - OpenAI Responses API updates (background mode, remote MCP, encrypted reasoning items): `https://openai.com/index/new-tools-and-features-in-the-responses-api/`
  - Model Context Protocol specification (2025 revision): `https://modelcontextprotocol.io/specification/2025-06-18`
  - OpenAI Evals design guidance (agentic evals and graders): `https://platform.openai.com/docs/guides/evals`
  - LangGraph v1.0 durable agent orchestration: `https://blog.langchain.com/langgraph-v1/`
  - Qdrant 1.16 hybrid retrieval and multitenancy capabilities: `https://qdrant.tech/blog/qdrant-1.16.x/`

### One web search (mandatory before implementation)

- Query: `site:docs.python.org os.replace atomic write json file`
- Date/time: `2026-03-01T04:48:53Z`
- Opened sources:
  - `https://docs.python.org/3.12/library/os.html#os.replace` (primary)
  - `https://docs.python.org/3/library/fcntl.html`
- Ready solutions found:
  - atomic file replacement (`tmp write -> os.replace`) for process state/registry updates;
  - OS file-lock primitives (`fcntl`) for cross-process coordination when needed.
- Decision: `reuse/integrate`
  - keep existing atomic `os.replace` write path in runner state/registry updates;
  - apply chain-scoped filtering in forensic/oracle gates (no lock-subsystem rewrite in this packet).
- Rejected options:
  - introducing a new lock daemon/DB lock for this remediation wave (out of scope, high migration cost).
- Query: `OWASP fail secure principle fail closed`
- Date/time: `2026-03-01T05:11:47Z`
- Opened sources:
  - `https://owasp.org/www-community/Fail_securely` (primary)
- Ready solutions found:
  - fail-closed gate is preferred for security/reliability-critical transitions;
  - permissive fallback on missing evidence is a control failure.
- Decision: `reuse/integrate`
  - keep acceptance promotion fail-closed;
  - enforce machine-check of L2 evidence artifact before any acceptance lock.
- Rejected options:
  - allowing checklist-only self-declaration of PG3 without artifact validation.
- Query: `pytest junitxml file and classname attributes`
- Date/time: `2026-03-01T05:42:07Z`
- Opened sources:
  - `https://docs.pytest.org/en/stable/reference.html#confval-junit_family` (primary)
- Ready solutions found:
  - pytest JUnit XML carries deterministic testcase attributes (`name`, `classname`, optional `file`) suitable for machine linkage to target tests;
  - JUnit artifact can be used as deterministic L1 evidence instead of self-declared flags.
- Decision: `reuse/integrate`
  - require `l1_evidence.junit_xml_path` in Go-to-Full checklist and match each `defect_mapping.target_test` against passed JUnit testcase;
  - enforce freshness window across L1 (JUnit) and L2 (summary) evidence.
- Rejected options:
  - accepting checklist-only L1 pass declarations without artifact linkage.
- Query: `json schema versioning best practices`
- Date/time: `2026-03-01T06:03:10Z`
- Opened sources:
  - `https://json-schema.org/understanding-json-schema/reference/schema` (primary)
  - `https://www.sourcemeta.com/blog/how-we-built-jsonschema-for-modern-c` (secondary)
- Ready solutions found:
  - registry contracts should carry explicit schema version for controlled evolution;
  - consumers should fail-closed on unsupported schema when strict compatibility is required.
- Decision: `reuse/integrate`
  - add explicit scenario governance `schema_version` and enforce fail-closed in acceptance replay/full;
  - version and persist realism SLA + lifecycle metadata inside registry entries.
- Rejected options:
  - keeping unversioned registry shape with implicit field assumptions.

## Rollback

- Runtime/code rollback: revert commit(s) in this branch and rerun deterministic suite.
- Gate rollback: только через отдельный TP waiver и временный `warn`, с явным сроком удаления waiver.

## No-go

- Нельзя фиксить качество через hardcoded answer text fitting.
- Нельзя добавлять keyword/regex branching в core-path.
- Нельзя сравнивать/обновлять baseline по INVALID/INCOMPLETE run.
- Нельзя запускать full expensive replay до green deterministic + micro replay.
- Нельзя принимать DoD без `decision_meta/decision_trace` contract evidence.
- Нельзя смешивать `run_economy` режимы (`off/warn/block`) в одной acceptance цепочке.
- Нельзя использовать `judge_mode off` как acceptance доказательство canonical quality.
- Нельзя блокировать/разрешать semantic acceptance только по standalone `judge_fail` без contract corroboration.
- Нельзя требовать byte-identical текст ответа как основной acceptance-критерий.
- Нельзя расширять core под нишевые фразы вместо capability/pack contracts.
- Нельзя обходить capability manifest прямым вызовом tool из webhook/router слоя.
- Нельзя делать lexical fallback primary semantic path в Pack Query Engine.
- Нельзя принимать quality по subset-сценариям (`count<10`) или без полного coverage (`include_media`, `handoff`).
- Нельзя использовать debug/forensic runner flags (`--allow-no-code-delta`, `--allow-judge-off`, `--skip-outbox`) как acceptance-доказательство.
- Нельзя маскировать semantic drift ручным приоритетом stale service carryover над explicit текущим info-вопросом.
- Нельзя переводить service-query в master без явного master-сигнала.
- Нельзя реализовывать master-routing через core hardcode/regex.
- Нельзя запускать full-chain как основной дневной debug-цикл до прохождения Go-to-Full.
- Нельзя игнорировать `manual_audit` рассинхрон между `summary` и `manual_audit.json`.
- Нельзя понижать threshold `degraded_fallback_rate` или отключать timeout-degrade контроль как способ пройти semantic gate.

## Риски/блокеры

- На первом этапе возможен рост `INVALID` из-за новых hard gates (ожидаемо и допустимо).
- Возможны ложные срабатывания static hardcode gate; требуется точная allowlist разрешенных зон.
- Переход на contract-only oracle может вскрыть старые тесты, которые держались на тексте.
- Понадобится синхронное обновление resolver + tests + run-gates, иначе churn в CI.

## Execution Addendum (2026-02-28, Chain Controller + Budget Firebreak)

### FACT audit (last 5h, budget loop evidence)

Источники:
- `/tmp/booking_quality/_index/by_hour/2026-02-28/**`
- `/tmp/booking_quality/_run_guard/ledger.tsv`
- `/tmp/booking_quality/booking-lock-20260228-a1-r11/summary.json`
- `/tmp/booking_quality/booking-lock-20260228-a1-r12/summary.json`
- `/tmp/booking_quality/booking-lock-20260228-a1-r13/summary.json`
- `/tmp/booking_quality/booking-replay-20260228-a1-r11-fix{1,2,3,4}/summary.json`

Факты:
- За последние 5 часов: `27` run, из них `canonical=3`, `non-canonical=24`.
- Стоимость non-canonical части существенно выше полезной:
  - `turns`: `407` vs `45` (canonical),
  - `judge judged`: `297` vs `39`,
  - `duration_s`: `7566.3` vs `777.55`.
- По guard ledger есть повторные циклы с одинаковым fingerprint в одном и том же окне:
  - `mode=replay`: один fingerprint запущен `8` раз,
  - `mode=lock`: один fingerprint запущен `2` раза.
- Есть реальный `resume` механизм (`run_manifest.resume_command` + `--resume`), но на практике запускались новые run-id цепочки и быстрые preflight retries.
- Есть путаница идентичности run: `run_id` с префиксом `lock-` может фактически быть `mode=replay` (определение mode идет по `scenarios_file/run_economy`).

Вывод:
- Корень сжигания бюджета в этом окне: не отсутствие quality-gates, а отсутствие обязательного chain-level оркестратора, который технически запрещает divergence-path (new-run вместо resume/step-order).

### Что уже реализовано (и что это закрывает)

- Chain-level state machine реализован в `scripts/quality_chain_controller.sh` с `lock -> replay -> full`, run_id/mode контрактом, resume-only и ROI stop-loss.
- Acceptance token gate реализован в `ops/diagnose.py` и блокирует acceptance без chain-token.
- Guarded wrapper делегирует acceptance в controller и требует `--pg-checklist` для acceptance lock (`scripts/llm_quality_guarded.sh`).
- Bootstrap/import command для legacy run-артефактов добавлен в `scripts/quality_chain_controller.sh` (создает chain state из summary/run_manifest).
- `run_manifest.json` + индекс `_index` + `resume_command` формируются в `ops/diagnose.py`.
- `manual_audit_gate`, `oracle_conflict_gate`, `forensic_sla_gate`, `scenario_governance_gate`, `quality_constant_gate`, `hardcode_core_gate`, `lexicon_regex_delta_gate` реализованы в `ops/diagnose.py`.
- Deterministic тесты для controller/guard/гейтов есть в `truffles-api/tests/test_booking_quality_chain_controller.py`, `truffles-api/tests/test_booking_quality_guarded_wrapper.py`, `truffles-api/tests/test_booking_quality_status_gate.py`.
- Handoff brief enforced для перехода между шагами (`brief_for_next_agent.md`) в `scripts/quality_chain_controller.sh`.

### Что не реализовано (ключевые пробелы)

- Нет новых ключевых пробелов в chain controller после bootstrap; открытые пункты остаются в `P4/P9/P12/P13/P14` по актуальному Execution Status (`P5/P7` закрыты отдельными блоками).

### Что может сломаться даже после текущих gate (failure map)

1. **Bypass risk:** оператор запускает `ops/diagnose.py` напрямую, минуя guarded wrapper.
2. **Identity drift:** `lock-` run-id при фактическом replay уводит аудит и decision trail в неверный контекст.
3. **Chain split risk:** можно параллельно вести разные acceptance-кандидаты, потому что индекс и gate mode-local.
4. **Resume abandonment:** interrupted lock имеет `resume_command`, но ничто не заставляет использовать его вместо нового run-id.
5. **False progress:** dev-lane canonical run воспринимается как закрытие acceptance chain.
6. **Global state collision:** `.run_economy_lock_state.json/.run_economy_replay_state.json` глобальны, не chain-scoped.
7. **Budget runaway:** нет автоматического стопа при повторных non-canonical прогонах без сокращения target failures.

---

## TP: Chain Controller Enforcement (full implementation plan)

- Название/цель:
  - Ввести обязательный chain-controller для acceptance quality, чтобы исключить бюджетный цикл повторных non-canonical запусков и устранить зависимость процесса от "памяти агента".

- Canon refs:
  - `AGENTS.md` (Quality Constant Gate, No Shortcut Gate, Booking anti-drift loop)
  - текущий TP (sections 6, 7, 9, 10, 11)
  - CA_ID: `CA-QUALITY-CHAIN-CONTROLLER-2026-02-28`

- Invariant:
  - Качество и acceptance критерии не ослабляются.
  - `lock -> replay -> full` остается обязательной acceptance-цепочкой.
  - Прямой обход chain-controller для acceptance невозможен технически.

- Scope:
  - Chain-level оркестрация acceptance прогонов.
  - Hard enforcement step-order/resume-only/run-id contract.
  - Budget stop-loss и mandatory context handoff.
  - Обновление runbook/TP evidence flow.

- Out of scope:
  - Изменение semantic логики консультанта.
  - Ослабление существующих quality gates.
  - Изменение deterministic oracle на текстовый.

- Touch-list (files/paths):
  - `ops/diagnose.py`
  - `scripts/llm_quality_guarded.sh`
  - `scripts/quality_chain_controller.sh` (new)
  - `scripts/quality_artifact_report.py` (optional extensions for chain view)
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `truffles-api/tests/test_booking_quality_chain_controller.py` (new)
  - `truffles-api/tests/test_booking_quality_guarded_wrapper.py` (new)

- Plan (implementation steps):
  1. Add chain state model:
     - New store `/tmp/booking_quality/_chain/{chain_id}.json`.
     - Fields: `chain_id`, `lane`, `status`, `current_step`, `steps.lock/replay/full`, `active_run_id`, `target_blockers`, `roi_window`, `context_hash`, `next_command`.
  2. Add single entrypoint script:
     - `scripts/quality_chain_controller.sh` with commands:
       - `start`, `resume`, `advance`, `status`, `close`, `abort`.
     - `advance` chooses exactly one legal next action (`resume current` or next step), no free-form launch.
  3. Add acceptance hard gate inside `ops/diagnose.py llm-quality`:
     - New args: `--chain-id`, `--chain-step`, `--chain-token`.
     - For `quality_lane=acceptance` require valid chain-token and state alignment.
     - Direct acceptance launch without controller token -> `INVALID(chain_controller_required)`.
  4. Add run_id/mode strict contract:
     - `run_id` prefix must match resolved mode:
       - `booking-lock-*` -> lock,
       - `booking-replay-*` -> replay,
       - `booking-full-*` -> full.
     - Mismatch -> `INVALID(run_id_mode_mismatch)`.
  5. Add resume-only enforcement:
     - If latest chain step run is `incomplete` and has `resume_command`, only resume is allowed.
     - Starting new run-id for same step blocked with explicit reason.
  6. Add chain-level anti-loop/ROI stop-loss:
     - Track target blockers (`wrong_action`, `handoff_miss`, `booking_flow_break`, `run_incomplete`).
     - If `N` consecutive expensive runs (`judge_judged` above threshold) without delta on target blockers -> auto `BLOCKED(root_cause_required)`.
  7. Scope run_economy state by chain:
     - Keep lock/replay fingerprint state in chain namespace, not only global singleton files.
  8. Integrate guarded wrapper with controller:
     - `scripts/llm_quality_guarded.sh` delegates acceptance launches to controller.
     - Add strict deny message when user tries acceptance run directly.
  9. Add mandatory handoff context artifact:
     - `brief_for_next_agent.md` generated per chain step with:
       - root causes,
       - exact next command,
       - allowed next transitions only.
     - Missing brief blocks `advance`.
  10. Extend reporting:
      - `quality_artifact_report.py` adds chain view: current state, blocked reason, last canonical step.
  11. Add deterministic tests:
      - step-order enforcement,
      - resume-only enforcement,
      - run_id/mode mismatch fail,
      - direct acceptance bypass fail,
      - stop-loss trigger and unblock rules.
  12. Add rollout + migration:
      - bootstrap command to import existing run artifacts into chain state (for in-flight chains).
      - fallback mode for old data = read-only + explicit migration required.

- DoD:
  - Acceptance run cannot start without chain-controller token.
  - Interrupted acceptance step cannot be replaced by a new run-id; only resume allowed.
  - `run_id/mode` mismatch blocked deterministically.
  - Chain-level status shows exactly one active step and one allowed next action.
  - Stop-loss blocks repeated budget burn without blocker improvement.
  - Docs/runbook include exact operator flow (start/resume/advance/close).
  - Tests green for all new gates.

- Checks:
  - `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py`
  - `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
  - `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
  - `python3 scripts/quality_artifact_report.py --hours 6 --show-commands`
  - One dry acceptance simulation:
    - start chain -> lock interrupt -> resume -> replay -> full.

- Evidence:
  - Chain state file snapshots (`_chain/{chain_id}.json`) for each transition.
  - run manifests linked to chain id/step.
  - blocked examples:
    - direct acceptance call without token,
    - run_id/mode mismatch,
    - new run-id while resume pending,
    - stop-loss trigger.
  - Final canonical chain evidence:
    - lock/replay/full summaries + manual audits + chain close event.

- Rollback:
  - Feature flag `QUALITY_CHAIN_CONTROLLER_MODE=warn` for temporary downgrade from block -> warn.
  - Revert controller integration commit and restore previous guarded wrapper path.
  - Keep artifacts/index untouched.

- No-go:
  - Нельзя добавлять bypass-флаг, который отключает chain-controller в acceptance lane.
  - Нельзя ослаблять existing acceptance gates ради прохождения chain.
  - Нельзя считать dev-lane canonical run закрытием acceptance chain.
  - Нельзя обновлять baseline, если chain не в статусе `canonical_closed`.

- Риски/блокеры:
  - Ложные блокировки на старых run без chain metadata (решается bootstrap migration).
  - Операторские ошибки при переходе на новый entrypoint (решается runbook + explicit errors).
  - Конкурентный запуск нескольких контроллеров (решается file lock на chain_id).
  - Частичный отказ записи chain state (решается atomic write + backup copy).

## Execution Addendum (2026-02-28, Quality Operating Model v2, mandatory)

### Why previous loop fails (root cause, not symptom)

- Acceptance chain (`lock -> replay -> full`) использовался как debug loop вместо release gate.
- Большая часть expensive runs завершалась non-canonical/invalid и не могла обновлять baseline.
- Ошибки обнаруживались слишком поздно, потому что не было обязательного дешевого pre-gate.
- Oracle stack был смещен в сторону judge verdict вместо contract-first (`decision_meta/decision_trace/outcome`).
- Нет процессного SLA на forensic разбор артефактов до запуска следующего expensive run.

### Binding Operating Model (L0-L3)

- `L0 Static/Contract Lane`:
  - Цель: поймать структурные регрессии без токенов.
  - Состав: schema/contract/unit/static gates.
  - Блокер: любой red = STOP.
- `L1 Deterministic Targeted Lane`:
  - Цель: доказать фикс по конкретному root-cause в узком контуре.
  - Состав: targeted deterministic tests + contract assertions.
  - Блокер: нет target test или target test не reproduces defect.
- `L2 Micro Chaos Fail-Fast Lane`:
  - Цель: дешево проверить устойчивость фикса на живом шуме.
  - Состав: llm-quality micro run с fail-fast (`--max-failures`) и ограниченным budget.
  - Блокер: regression по целевому blocker-классу.
- `L3 Acceptance Release Lane`:
  - Цель: финальная приемка only.
  - Состав: canonical `lock -> replay -> full` в acceptance envelope.
  - Ограничение: L3 запрещен без прохождения `Go-to-Full Gate`.

### Go-to-Full Gate (PG0..PG6, required before L3)

- `PG0 Root-Cause Evidence`:
  - Есть формализованный root-cause statement с ссылкой на артефакты.
- `PG1 Target Contract Test`:
  - Есть новый/обновленный тест, который падал до фикса и зелен после фикса.
- `PG2 Deterministic Green`:
  - Обязательный deterministic subset зелен локально.
- `PG3 Micro Chaos Improvement`:
  - L2 показал улучшение в target blocker-class, без новых P0/P1 регрессий.
- `PG4 Forensic Complete`:
  - manual audit выполнен (`manual_audit.status=done`) и сверен с summary.
- `PG5 Provenance/Preflight Valid`:
  - runtime/provenance/preflight валидны; fingerprint согласован.
- `PG6 No Pending Ambiguity`:
  - Нет незакрытого interrupted/pending run в том же chain/fingerprint.

### No-Loop Law (hard stop)

- Запрещен повтор expensive run без нового evidence-сигнала по root-cause.
- Запрещен новый `lock` после non-canonical `lock` с тем же fingerprint без:
  - code/runtime delta, или
  - доказанного process remediation evidence.
- Любой `INVALID/NON-CANONICAL` в L3 автоматически возвращает процесс в `L1/L2`.
- L3 не может быть "основным дневным циклом" разработки.

### Oracle Stack Contract (binding)

- Primary oracle:
  - `decision_meta`, `decision_trace`, tool outcomes, state/outcome contract.
- Secondary oracle:
  - judge verdict/classification как advisory corroboration.
- Tertiary oracle:
  - text-level checks (`must_include`) только как debug hints, не acceptance basis.
- Acceptance decision запрещено принимать по judge-only или text-only сигналу.

### Judge Reliability Protocol (mandatory)

- Judge используется как panel-consistency evaluator, не single authority.
- При конфликте `judge` vs `contract`:
  - фиксируется как отдельный finding в manual audit,
  - приоритет у contract oracle,
  - запускается отдельный remediation backlog для judge/rubric.
- Для acceptance требуется явная пометка:
  - `judge_alignment = corroborated | conflicted`.

### Forensic SOP (mandatory before next expensive run)

- Минимальный пакет ручного разбора:
  - `summary.json`,
  - `responses.jsonl`,
  - `trace_bundle.jsonl`,
  - `brief.md`,
  - `manual_audit.json/md`.
- В handoff обязателен блок:
  - `root_causes`,
  - `top_failures`,
  - `what_changed_since_last_run`,
  - `exact_next_command`,
  - `why L3 is or is not allowed`.
- Новый expensive run до закрытия forensic SOP = `INVALID process`.

### Scenario Asset Governance (quality as product asset)

- Сценарии делятся на пулы:
  - `production-like`,
  - `expert hard cases`,
  - `chaos/noise`.
- Для каждого пула фиксируются quality targets:
  - coverage, drift, blocker rate.
- Сценарии версионируются как baseline asset (`scenario_fingerprint`) и не меняются в середине цепочки.
- Примитивные "идеальные" вопросы не могут быть единственным acceptance corpus.

### Interruption/Resume Contract

- Прерванный run должен:
  - быть резюмирован через `resume`, или
  - быть закрыт forensic-only с явной причиной.
- Старт нового run-id вместо resume без причины = process violation.
- Chain state обязан хранить:
  - `resume_command`,
  - `stop_reason`,
  - `resume_required`.

### Promotion Rules (L0 -> L1 -> L2 -> L3)

- Переход на следующий lane разрешен только при явном green предыдущего lane.
- `L3` разрешается только после `PG0..PG6`.
- `L3 fail` не ведет к новому `L3`; сначала обязательный возврат в `L1/L2`.

### Implementation Program (full rollout)

- `Stage A: Governance Sync`
  - Обновить TP/runbook/AGENTS references под модель L0-L3 + PG0..PG6.
  - Exit criteria: doc gates консистентны и не противоречат charter.
- `Stage B: Oracle Rebalance`
  - Укрепить contract-first acceptance; judge понижен до corroboration role.
  - Exit criteria: decision rule в tooling отражает oracle priority.
- `Stage C: Forensic Automation`
  - Стандартизовать manual audit output и handoff artifact template.
  - Exit criteria: следующий шаг всегда имеет deterministic `next_command + reason`.
- `Stage D: Scenario Governance`
  - Версионировать scenario pools, добавить chaos realism requirements.
  - Exit criteria: acceptance corpus содержит production-like + chaos buckets.
- `Stage E: Fail-Fast Economics`
  - Закрепить L2 micro fail-fast как обязательный pre-gate.
  - Exit criteria: expensive runs происходят только после L2 green signal.
- `Stage F: Chain Integrity`
  - Довести chain controller до строгого enforcement resume/order/identity.
  - Exit criteria: bypass/identity drift/resume abandonment блокируются hard.
- `Stage G: Acceptance Re-enable`
  - Запустить L3 только после прохождения Stage A-F и PG0..PG6.
  - Exit criteria: `lock -> replay -> full` используется как release confirmation, не как debug loop.

### Execution Status Update (2026-03-02, code-fact audit refresh)

- `P0 Governance Lock` partial: L0 static gates are implemented in `ops/diagnose.py` and wired in `.github/workflows/ci.yml` via `llm-quality-gates`; doc sync and runtime evidence are not code-verified.
- `P1 Semantic Decision Envelope` implemented in `truffles-api/app/routers/webhook/decision.py` with coverage in `truffles-api/tests/test_llm_policy_core.py`.
- `P2 Structured Policy-Core Adapter` implemented in `truffles-api/app/services/intent_service.py` + `truffles-api/app/schemas/intent.py` with tests in `truffles-api/tests/test_llm_policy_core.py`.
- `P3 Semantic Firewall` implemented in `truffles-api/app/routers/webhook/decision.py` with reason-code enforcement coverage in `truffles-api/tests/test_message_endpoint.py`.
- `P4 Expected-Reply Refactor` partial: expected-reply contract exists in `truffles-api/app/services/expected_reply_contract.py` and master intent resolver in `truffles-api/app/services/pack_runtime_service.py` + `truffles-api/app/schemas/intent.py`, but expected-reply still participates in routing in `truffles-api/app/routers/webhook/booking.py` and `truffles-api/app/routers/webhook/info.py`.
- `P5 Pack Query Engine v2` implemented via dedicated block `docs/TASK_PACKAGES/TP-2026-03-02-p5-pack-query-engine-v2-a1.md`: `truffles-api/app/services/pack_runtime_service.py` now provides hybrid retrieval (`sparse+semantic`) with rerank and strict tenant/branch scope filtering in runtime path (`semantic_service_match`, `get_pack_service_hint`, retrieval provenance in `ensure_resolver_meta`), with deterministic coverage in `truffles-api/tests/test_pack_query_engine_contract.py`, `truffles-api/tests/test_pack_query_engine_abstain.py`, `truffles-api/tests/test_pack_runtime_service.py`, plus `test_message_endpoint.py -k \"semantic_service_matcher or service_not_found\"`.
- `P6 Capability Manifest + Protocol Gate` implemented in `truffles-api/app/services/capability_manifest_service.py`, `truffles-api/app/services/capabilities_runtime.py`, `truffles-api/app/services/tool_registry_service.py` with tests `truffles-api/tests/test_tool_protocol_gate.py` and `truffles-api/tests/test_cross_domain_capability_isolation.py`; dedicated `tool_protocol_gateway.py` file not found.
- `P7 Core De-hardcoding Sweep` done: phrase/regex routing removed from `truffles-api/app/routers/webhook/info.py`, `truffles-api/app/routers/webhook/booking.py`, `truffles-api/app/services/tool_registry_service.py` by moving matchers to `truffles-api/app/services/info_signal_service.py` and `truffles-api/app/services/booking_signal_service.py`; checks green (`test_booking_appointments.py`, `test_master_info_flow.py`, `test_message_endpoint.py -k "info_intents or booking_info_intents or expected_reply"`).
- `P7` continuity follow-up opened as mandatory program block `SIG-PROGRAM-S0-S4` in `docs/TASK_PACKAGES/TP-2026-03-02-process-integrity-signal-program-a1.md` to prevent context loss and enforce `S1/S2/S3/S4` completion without residual hardcode drift.
- `P8 Acceptance Engine Split` implemented in `ops/diagnose.py` (`semantic_acceptance` and `delivery_acceptance`).
- `P9 Contract Test Migration` partial: master long-hair tests migrated to contract meta asserts (`truffles-api/tests/test_info_master_long_hair.py`, checks green as of 2026-03-02) and demo_salon semantic service tests migrated (message_endpoint `semantic_service_matcher/semantic_question_type`, checks green as of 2026-03-02), but text-based oracles remain elsewhere in `truffles-api/tests/test_message_endpoint.py` and `truffles-api/tests/test_knowledge_service.py`.
- `P10 Canonical Quality Chain` implemented: chain controller + acceptance token gate implemented in `scripts/quality_chain_controller.sh`, `scripts/llm_quality_guarded.sh`, `ops/diagnose.py`, and multi-seed drift enforcement added to PG checklist validation (`multi_seed_evidence` required for acceptance lock).
- `P11 Budget-Go-To-Full Control` implemented in `scripts/quality_chain_controller.sh` (PG checklist + L1/L2 evidence linkage) and enforced via `scripts/llm_quality_guarded.sh` for acceptance lock.
- Chain controller bootstrap/import implemented in `scripts/quality_chain_controller.sh` with deterministic coverage in `truffles-api/tests/test_booking_quality_chain_controller.py`.
- `P12 Cross-domain Hardening` partial: deterministic cross-domain suite now covers two non-salon runtime packs (`truffles-api/tests/test_cross_domain_signal_contract_suite.py`) and quality tooling now has matrix non-salon contract gate in `ops/diagnose.py` (`--cross-domain-contract off|warn|block`); live quality matrix evidence for real non-salon clients is still pending.
- `P13 Canary + Rollback` missing: no canary/rollback automation or tests found in repo.
- `P14 Evidence + STATE Handoff` partial: `ops/diagnose.py` writes `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl`, `run_manifest.json`; `STATE.md` handoff remains a process step, not a coded gate.
- `P15 Timeout-Degrade Reliability Remediation` implemented: timeout degrade retry limit and clarify/handoff escalation logic exist in `truffles-api/app/routers/webhook/decision.py` with deterministic tests in `truffles-api/tests/test_message_endpoint.py` (booking timeout retry exhaust -> handoff).

### Mandatory Continuation for P7 (S0..S4, code-fact status at 2026-03-02)

- `S0 No-Hardcode Gate Scope Fix` done: static hardcode gate in `ops/diagnose.py` now includes signal-layer files (`truffles-api/app/services/booking_signal_service.py`, `truffles-api/app/services/info_signal_service.py`) and explicit technical-format whitelist (`LLM_QUALITY_HARDCODE_TECHNICAL_ALLOW_SNIPPETS`); coverage updated in `truffles-api/tests/test_booking_quality_status_gate.py`.
- `S1 Signal Manifest Externalization` done: domain regex/markers moved out of runtime signal services into declarative manifest + schema:
  - manifest: `truffles-api/app/knowledge/generic/SIGNAL_MANIFEST.yaml`
  - schema: `contracts/packs/signal_manifest.v1.jsonschema`
  - runtime loader: `truffles-api/app/services/signal_manifest_service.py`
  - consumers migrated: `truffles-api/app/services/booking_signal_service.py`, `truffles-api/app/services/info_signal_service.py`
  - deterministic evidence: `pytest -q truffles-api/tests/test_signal_manifest_service.py`, `pytest -q truffles-api/tests/test_booking_appointments.py`, `pytest -q truffles-api/tests/test_master_info_flow.py`, `pytest -q truffles-api/tests/test_message_endpoint.py -k "info_intents or booking_info_intents or expected_reply"`.
- `S2 Signal Runtime Compiler` done: signal loader now builds compiled runtime bundle with explicit version/fingerprint/signature metadata and cache-by-signature contract in `truffles-api/app/services/signal_manifest_service.py` (`CompiledSignalManifest`, `compiled_version`, `manifest_fingerprint`, `manifest_signature`, `get_signal_manifest_runtime_meta`); deterministic proof in `truffles-api/tests/test_signal_manifest_service.py` (`8 passed`).
- `S3 No-Hardcode Gate v2` done for scope enforcement: hardcode gate path policy in `ops/diagnose.py` now fail-checks `runtime/core/signal` scope (`webhook/*.py`, `*_signal_service.py`, `*_runtime_service.py`, `pack_runtime_service.py`, `tool_registry_service.py`) with deterministic scope tests in `truffles-api/tests/test_booking_quality_status_gate.py` (`8 passed` for scope/gate slice).
- `S4 Cross-domain Contract Suite` done (code-fact): dedicated deterministic suite for minimum two non-salon packs added in `truffles-api/tests/test_cross_domain_signal_contract_suite.py` (covers info/booking/tool_registry contract path via runtime truth datasets), and quality matrix now supports fail-closed cross-domain gate (`ops/diagnose.py`, helper `_llm_quality_build_cross_domain_matrix_contract_status`, args `--cross-domain-contract`, `--cross-domain-min-non-salon`, `--cross-domain-excluded-slugs`) with deterministic coverage in `truffles-api/tests/test_booking_quality_status_gate.py` (`cross_domain_matrix_contract*` tests).

### DoD for this Addendum

- TP явно фиксирует L0-L3 operating model.
- `Go-to-Full Gate` и `No-Loop Law` закреплены как обязательные.
- Oracle/judge responsibility разделены contract-first способом.
- Определен полный rollout-план Stage A-G с exit criteria.

### Checks

- Документарная проверка:
  - TP sections не противоречат `Architecture Charter` и текущим No-go.
- Процессная проверка:
  - любой предложенный L3 run должен проходить PG0..PG6 checklist перед запуском.
- Аудиторская проверка:
  - handoff содержит forensic SOP пакет и next-command rationale.

### Evidence

- Обновленный TP с этим addendum.
- Пример заполненного PG0..PG6 чеклиста в session evidence перед следующим L3.
- Пример forensic handoff, где объяснено почему L3 разрешен или заблокирован.

### No-go (additional)

- Нельзя запускать L3 "чтобы проверить, вдруг теперь пройдет", без PG0..PG6.
- Нельзя повышать роль judge до primary acceptance oracle.
- Нельзя заменять root-cause фиксы повтором expensive runs.
- Нельзя принимать успех по "зелёным общим метрикам" при красных target blockers.
