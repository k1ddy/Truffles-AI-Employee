# TP-2026-02-21-consultant-contract-first-remediation-a1

- Название/цель: Contract-first remediation консультанта по форензике прогонов за последние 11 часов. Цель: остановить budget burn, исключить text-fitting/hardcode в core, перевести доменную интерпретацию на `semantic-first + resolver + contracts`, и вернуть устойчивое качество `>=95%` на валидном full critical replay.
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

## Invariant

- Не менять продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять LAW/policy/safety hard-gates.
- Runtime core остается pack-agnostic.
- `decision_meta`/`decision_trace` обязательны и консистентны на каждом user turn.
- INVALID/INCOMPLETE run не участвует в baseline/comparison.
- Никаких hardcoded phrase-branching в core-path (`decision/booking/tool_registry`) как способа фикса качества.

## Scope

- Перевести доменную интерпретацию на resolver-contract и удалить text-coupling из core.
- Ввести fail-closed гейты, которые блокируют добавление хардкода в core на уровне CI.
- Перестроить тестовый oracle на структурные сигналы (`action/intent/slots/outcomes/trace`), а не на ответные фразы.
- Довести run-quality контур до стабильного anti-drift цикла (lock/replay/acceptance).

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
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_calendar_slot_response_contract.py`
- `truffles-api/tests/test_master_info_flow.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_booking_quality_*.py`

## Plan (1..16)

1. Stop-the-line + freeze acceptance spend
- До архитектурного фикса запретить full expensive replay.
- Разрешены только deterministic + micro replay на lock scenarios.

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
- Stage A: deterministic + micro replay.
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

## DoD

- В core-path нет новых raw keyword/regex branching; Hardcode Prevention Gate green.
- Core regression тесты не используют текстовые подстроки как главный oracle для поведения.
- Resolver возвращает canonical contract и provenance (`resolver_id/version/confidence`).
- Low-confidence path всегда fail-safe (`COLLECT`/`HANDOFF`), без guess.
- Replay/acceptance невозможен на non-canonical/unreadable baseline.
- Quarantine для incomplete run artifacts работает и отражается в summary/brief.
- На full critical run: `infra_valid=true`, `semantic_valid=true`, `strict_pass_rate>=0.95`, `judge_fail=0`, `unobserved_turn_count=0`.

## Checks

- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/pack_runtime_service.py`
- `ruff check ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/pack_runtime_service.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking or expected_reply or session_memory or policy_core"`
- `pytest -q truffles-api/tests/test_booking_quality_*.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file <lock_scenarios> --baseline-summary <lock_summary> --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20`

## Evidence

- Forensics 11h:
  - `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.json`
  - `/tmp/booking_quality/analysis-last-11h-20260223T221713Z.md`
  - `/tmp/booking_quality/analysis-last-11h-bad-turns-20260223T221713Z.jsonl`
- Quality run artifacts:
  - `<run_dir>/summary.json`
  - `<run_dir>/brief.md`
  - `<run_dir>/responses.jsonl`
  - `<run_dir>/trace_bundle.jsonl`
- Contract evidence:
  - `decision_meta` sample rows,
  - `decision_trace` sample rows with resolver/policy/tool stages,
  - acceptance command + output digest.

## Rollback

- Runtime/code rollback: revert commit(s) in this branch and rerun deterministic suite.
- Gate rollback: только через отдельный TP waiver и временный `warn`, с явным сроком удаления waiver.

## No-go

- Нельзя фиксить качество через hardcoded answer text fitting.
- Нельзя добавлять keyword/regex branching в core-path.
- Нельзя сравнивать/обновлять baseline по INVALID/INCOMPLETE run.
- Нельзя запускать full expensive replay до green deterministic + micro replay.
- Нельзя принимать DoD без `decision_meta/decision_trace` contract evidence.

## Риски/блокеры

- На первом этапе возможен рост `INVALID` из-за новых hard gates (ожидаемо и допустимо).
- Возможны ложные срабатывания static hardcode gate; требуется точная allowlist разрешенных зон.
- Переход на contract-only oracle может вскрыть старые тесты, которые держались на тексте.
- Понадобится синхронное обновление resolver + tests + run-gates, иначе churn в CI.
