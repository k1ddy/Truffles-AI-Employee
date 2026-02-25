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

## Plan (1..16)

1. Stop-the-line + freeze acceptance spend
- До архитектурного фикса запретить full expensive replay.
- Разрешены только contract-bound deterministic checks + micro replay на lock scenarios с `judge.enabled=true`.

2. Explicit architecture contract for domain resolution
- Зафиксировать единый интерфейс resolver output:
  - `intent_class`,
  - `action_class` (`FACT/COLLECT/HANDOFF`),
  - `entity_refs` (id-based),
  - `slot_candidates`,
  - `confidence`,
  - `abstain_reason`,
  - `resolver_id/ruleset_version`.
- Core-path принимает только этот контракт и не ветвится по пользовательскому тексту.

3. Remove text-coupling from core (deletions)
- Удалить/перенести все phrase-dependent ветки из:
  - `decision.py`,
  - `booking.py`,
  - `tool_registry_service.py`,
  - `info.py`.
- Вместо них использовать contract flags (`tool_decision`, `expected_reply_type`, `resolver_result`, `policy outcome`).

4. Introduce bounded resolver layer (semantic-first)
- Semantic retrieval из pack/БД:
  - lexical recall (fuzzy/BM25/trigram),
  - semantic rerank (embedding score),
  - disambiguation by margin/threshold.
- Правило: low confidence -> `COLLECT`/`HANDOFF`, не угадывать.

5. Lexicon governance (bounded fallback, not primary)
- Лексикон только fallback для:
  - safety/legal triggers,
  - brand aliases/orthography,
  - rare domain entities.
- Ввести `lexicon_budget_per_release` и отчет `why semantic failed`.
- Любой lexicon delta без resolver delta + contract tests -> CI FAIL.

6. Hardcode Prevention Gate (CI fail-closed)
- AST/Semgrep rule-set:
  - запрет string-list/regex branching по raw text в core-файлах;
  - разрешенные зоны: resolver/data packs only.
- Дифф-гейт: новые phrase-matcher конструкции в core = BLOCK.

6.1 Quality threshold alignment with charter
- Синхронизировать thresholds инструмента и ТЗ: `strict_pass_rate >= 0.95`.
- Для acceptance закрепить деградационный бюджет: `degraded_fallback_rate <= 0.05`.
- Acceptance-run при `count < 10` или без `include_media`/`handoff` coverage = INVALID.

7. Contract-only tests migration
- Убрать text-based assertions из core regression tests как primary oracle.
- Перевести на:
  - `decision_meta` fields,
  - `decision_trace` stages/reasons,
  - tool outcomes/state transitions.

8. Domain pack grounding tests (auto-generated)
- Из пака генерировать test-cases:
  - exact forms,
  - translit,
  - typo variants,
  - RU/KZ/mixed paraphrases.
- Проверять `entity_id` grounding и `no_guess` policy.

9. Safety/legal deterministic gate hardening
- Safety/legal triggers должны быть deterministic-first.
- Проверки: `reason_code`, `policy_section`, `trace stage`.

10. Resolver observability contract
- Добавить в `decision_meta`:
  - `resolver_id`, `resolver_version`, `resolver_confidence`, `resolver_candidates`, `abstain_reason`.
- Добавить в trace stage `resolver` с decision path.

11. Anti-drift replay contract v2
- Lock/replay только сопоставимыми параметрами.
- Replay невозможен без:
  - canonical baseline,
  - `reset_before_dialog=true`,
  - `jid_mode=unique`,
  - runtime commit match.

12. Run-economy anti-burn hardening
- Блокировать replay при:
  - non-canonical baseline,
  - unreadable baseline,
  - unchanged replay fingerprint без code delta.
- Отдельно помечать incomplete artifact runs в quarantine.

13. Runtime behavior stabilization (booking/session memory)
- Убрать raw datetime carryover.
- Контрактно выровнять `expected_reply` clear/set paths.
- На conflict/mismatch отвечать через intent-contract, не через phrase-fitting.

14. Canary rollout strategy
- Stage A: contract-bound deterministic checks + micro replay.
- Stage B: full critical replay.
- Stage C: production canary percentage.
- Stop-the-line при regression/semantic drift.

15. Documentation + governance update
- Зафиксировать в TP/STATE/REPORT:
  - удаленные hardcode места,
  - новые CI gates,
  - новые contract tests,
  - replay chain evidence.

16. Acceptance + merge wave
- PR-A: core/runtime contract refactor + deletion of text-coupling.
- PR-B: resolver/lexicon governance + CI gates.
- PR-C: tests/evidence/docs.
- Каждый PR с отдельным evidence block и reproducible commands.

## Plan Addendum (2026-02-24, execution order)

1. P0 Firebreak stabilization (immediate)
- Зафиксировать single semantic owner на уровне contract tests.
- Убрать semantic reinterpretation в post-plan ветках (кроме whitelist deterministic overrides).
- Зафиксировать mandatory reason-code на каждом override/degrade event.

2. P0.1 Stochastic robustness hardening
- Не фиксировать semantic слой в "temperature=0 everywhere"; оставить вероятностный reasoning там, где это улучшает обобщение.
- Обязать structured output + confidence/abstain для policy-core и interpretation tasks.
- Добавить reproducibility check по контрактам (`action/tool/trace`) на multi-seed (а не по текстовой идентичности).

3. P0.2 Honest timeout path
- Ввести bounded retry policy для timeout.
- Для factual intent в booking context сначала FACT, затем controlled next-step (без generic collect leak).

4. P1 Pack Query Engine normalization
- Вынести factual extraction в pack query contract (`intent + query facets -> fact bundle`).
- Удалить ad-hoc phrase fitting из webhook routing.

5. P1.1 Infra contract hardening
- Закрыть Redis topology mismatch для llm-quality/local runtime.
- Включить gate на `dedup_db_fallback_rate` и явный waiver-only процесс при infra инциденте.

6. P2 Acceptance governance lock
- Единственная acceptance цепочка: `lock -> replay -> full`.
- Единый `scenario_fingerprint`, `code_fingerprint`, `run_economy=block`.
- Mixed evidence (`off/warn/block` в одном acceptance окне) запрещён.

7. P2.1 Cross-domain scalability hardening
- Ввести `tool capability manifest` на tenant/pack уровне (`allowed_tools`, `allowed_fact_scopes`, `handoff_policy`).
- Core router выбирает только из capability-allowlist текущего tenant; любые "чужие" tools/answers блокируются контрактом.
- Pack Query Engine формирует fact bundle строго из tenant-pack artifacts (compiled), без нишевых fallback в core code.

8. P2.2 Structured-output semantic arbiter rollout
- Ввести schema-first contract для результата policy-core (`action/intent/slots/fact_refs/confidence/abstain_reason`).
- Любой невалидный JSON/schema mismatch переводить в controlled degrade-path с trace reason-code.
- Удалить оставшиеся post-override semantic rewrites вне whitelist policy overrides.

9. P2.3 MCP-compatible tool protocol rollout
- Вынести вызов tool-ов через protocol adapter и capability check до фактического вызова.
- Зафиксировать deny-by-default: неизвестный tool -> blocked + trace reason.
- Добавить integration tests на "tenant A не может вызвать tool tenant B".

10. P2.4 Hybrid retrieval hardening for Pack Query Engine
- Реализовать strict tenant/branch filters + hybrid recall/rerank + abstain by margin.
- Добавить provenance в fact bundle (`pack_id`, `entity_id`, `source_ref`, `confidence`).
- Закрыть legacy lexical-only fallback как primary path.

11. P2.5 Eval modernization (2025 contract lane)
- Добавить multi-seed contract stability отчёт (`action/tool/reason-code drift`).
- Отдельно мерить semantic consistency vs timeout/degrade rates.
- Зафиксировать acceptance threshold по контрактным метрикам, не по text similarity.

12. P2.6 Timeout budget governance
- Для long tasks: bounded background/deferred path с прозрачным статусом.
- Для turn response: hard SLA budget + deterministic degrade contract.
- Запретить generic collect как default timeout response для factual intent.

## Execution Process (wave discipline)

1. Wave 0 (Governance lock)
- Цель: убрать противоречия канона/инструмента.
- Артефакты: синхронизированный `AGENTS.md`, TP charter, acceptance envelope в раннере.
- Stop condition: любые acceptance-прогоны с мягкими параметрами (`judge off`, `count<10`, no handoff/media).

2. Wave A (Semantic owner remediation, PR-A)
- Цель: убрать semantic overrides и phrase-branching из core, оставить один semantic owner.
- Артефакты: code deletions в core + D2 deterministic contract tests + evidence lock/replay.
- Stop condition: любой новый hardcode/fast-path semantic takeover.

3. Wave B (Capability/protocol hardening, PR-B)
- Цель: fail-closed tool/fact boundaries для multi-tenant.
- Артефакты: capability manifest enforcement + protocol gate + cross-domain isolation tests.
- Stop condition: tool/action вне allowlist проходит в runtime.

4. Wave C (Pack query engine + provenance, PR-C)
- Цель: hybrid retrieval + abstain-by-margin без lexical-only primary fallback.
- Артефакты: resolver contract + provenance + abstain tests.
- Stop condition: core снова зависит от нишевых фраз.

5. Wave D (Acceptance and release)
- Цель: lock -> replay -> full на одинаковых fingerprint с quality gates.
- Артефакты: `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl` + top-failures.
- Stop condition: regression, INVALID run, non-canonical baseline, interrupted chain.

## DoD

- В core-path нет новых raw keyword/regex branching; Hardcode Prevention Gate green.
- Core regression тесты не используют текстовые подстроки как главный oracle для поведения.
- Resolver возвращает canonical contract и provenance (`resolver_id/version/confidence`).
- Low-confidence path всегда fail-safe (`COLLECT`/`HANDOFF`), без guess.
- Replay/acceptance невозможен на non-canonical/unreadable baseline.
- Quarantine для incomplete run artifacts работает и отражается в summary/brief.
- На full critical run: `infra_valid=true`, `semantic_valid=true`, `strict_pass_rate>=0.95`, `judge_fail=0`, `unobserved_turn_count=0`.
- На full critical run: `degraded_fallback_rate<=0.05` и `rewrite_reason_coverage=1.0`.
- На acceptance run зафиксирован единый `scenario_fingerprint` и `code_fingerprint` для `lock/replay/full`.
- `run_economy.mode=block` на всех acceptance звеньях.
- `judge.enabled=true` для lock/replay/full acceptance run.
- Для booking coverage fast-path не перехватывает `info/check_booking/media/reschedule` turns в обход semantic-owner.
- Timeout/degrade path не даёт `generic collect` для factual intent; trace/meta содержит reason-code.
- `dedup_db_fallback_rate` либо в пределах целевого порога, либо run помечен infra-waiver и исключён из baseline/comparison.
- Multi-seed acceptance показывает стабильность контрактов (без требования идентичного текста ответа):
  - стабильность `action/tool/trace reason-code`,
  - отсутствие роста critical misroute/hard-fail по порогам.
- Tenant не может выполнить tool/action вне собственного capability manifest.
- Semantic arbiter output всегда schema-valid; schema violation уходит в controlled degrade с reason-code.
- В trace зафиксированы `capability_check` и `tool_protocol_decision` до вызова tool.
- Для factual path есть provenance bundle (`pack_id/entity_id/source_ref/confidence`) и margin-based abstain.
- Cross-domain regression suite проходит минимум на 2 несалонных capability-pack (smoke-contract уровень).

## Checks

- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/pack_runtime_service.py`
- `ruff check ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/pack_runtime_service.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_policy_core_fast_collect_guard.py`
- `pytest -q truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking or expected_reply or session_memory or policy_core"`
- `pytest -q truffles-api/tests/test_booking_quality_*.py`
- `TEST_MODE=1 scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-<id> --owner-file ops/diagnose.py --owner-file truffles-api/app/routers/webhook/decision.py --quick-check "pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_response_guard.py" -- --base-url <local_api> --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --seed 42 --reset-before-dialog --jid-mode unique --judge-mode all --fail-on-thresholds --run-economy-gate block`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --seed 42 --reset-before-dialog --jid-mode unique --judge-mode all --fail-on-thresholds --run-economy-gate block --run-id booking-lock-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --run-id booking-replay-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --run-id booking-full-<id>`
- `jq '.run_economy.mode, .quality_status.infra_valid, .quality_status.semantic_valid, .judge.enabled, .run_economy.code_fingerprint, .run_economy.scenario_fingerprint' <run_dir>/summary.json`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --seed 7 --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --run-id booking-replay-s7-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --seed 19 --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --run-id booking-replay-s19-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --seed 42 --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --run-id booking-replay-s42-<id>`
- `pytest -q truffles-api/tests/test_tool_capability_manifest.py truffles-api/tests/test_tool_protocol_gate.py`
- `pytest -q truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_query_engine_abstain.py`
- `pytest -q truffles-api/tests/test_cross_domain_capability_isolation.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --seed 7 --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --emit-contract-drift --run-id booking-contract-s7-<id>`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --seed 19 --fail-on-thresholds --fail-on-regression --run-economy-gate block --max-failures 20 --emit-contract-drift --run-id booking-contract-s19-<id>`

Forensic only (not acceptance):
- `judge_mode off/critical` сценарии допустимы только как дополнительная диагностика, но не как основание baseline/update acceptance.

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
- Quality run artifacts:
  - `<run_dir>/summary.json`
  - `<run_dir>/brief.md`
  - `<run_dir>/responses.jsonl`
  - `<run_dir>/trace_bundle.jsonl`
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
- Нельзя требовать byte-identical текст ответа как основной acceptance-критерий.
- Нельзя расширять core под нишевые фразы вместо capability/pack contracts.
- Нельзя обходить capability manifest прямым вызовом tool из webhook/router слоя.
- Нельзя делать lexical fallback primary semantic path в Pack Query Engine.

## Риски/блокеры

- На первом этапе возможен рост `INVALID` из-за новых hard gates (ожидаемо и допустимо).
- Возможны ложные срабатывания static hardcode gate; требуется точная allowlist разрешенных зон.
- Переход на contract-only oracle может вскрыть старые тесты, которые держались на тексте.
- Понадобится синхронное обновление resolver + tests + run-gates, иначе churn в CI.
