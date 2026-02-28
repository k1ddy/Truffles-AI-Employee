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
