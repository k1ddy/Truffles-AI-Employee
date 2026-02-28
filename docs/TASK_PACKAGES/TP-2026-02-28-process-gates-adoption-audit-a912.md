# TP-2026-02-28-process-gates-adoption-audit-a912

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-ADOPTION-AUDIT-2026Q2`
- `PARENT_BLOCK_ID`: `PROCESS-GOVERNANCE`
- `DEPENDS_ON`: `PROCESS-GATES-ENFORCEMENT-ADOPTION-2026Q1`
- `UNLOCKS`: `PROCESS-GATES-LEGACY-MIGRATION-2026Q2`

## Название/цель
Закрыть следующий операционный шаг после enforcement: дать repeatable adoption-audit контур для legacy-сессий с машинно-читаемым evidence и критериями phased migration.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/session_audit.sh`
- `scripts/session_check.sh`
- `scripts/session_gate.sh`

## Invariant
- Не ослаблять блокирующие проверки для новых сессий (`required` режим).
- Не менять runtime/core поведение продукта.
- Не превращать adoption-аудит в hard-stop для legacy без явного rollout decision.

## Scope
- Расширить `session_audit` до machine-readable adoption отчёта.
- Зафиксировать baseline coverage по gate mode (`required|optional|off|missing|invalid`) и backlog legacy-сессий для миграции.
- Добавить канонический report артефакт с критериями миграции по когортам.

## Out of scope
- Массовая правка исторических session-файлов.
- Любые изменения LLM runtime / booking / webhook pipeline.
- Долгие quality-прогоны (`llm-quality`, stress).

## One web search (mandatory before implementation)
- **Query (exact):** `SRE gradual rollout policy adoption legacy systems backward compatibility checklist`
- **Date/time (local):** `2026-02-28 16:52 (Asia/Almaty)`
- **Why this query is precise:** нужен operational шаблон phased migration policy: как внедрять stricter gates для новых сущностей без ложной блокировки legacy.
- **Sources opened (from this query):**
  - `Google SRE Workbook — Error Budget Policy` — `https://sre.google/workbook/error-budget-policy/`
  - `Google SRE Workbook — Canarying Releases` — `https://sre.google/workbook/canarying-releases/`
  - `AWS Well-Architected — Perform safe deployment through automation` — `https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prepare_safe_deployment.html`
- **Existing solutions found:** phased enforcement by cohorts, explicit go/no-go signals, rollback-ready rollout, evidence-first adoption tracking.
- **Decision:** `reuse` текущие `session_*` скрипты + добавить adoption-report output и migration checklist в docs.
- **Rejected options:** instant strict enable for all legacy sessions (слишком высокий риск false-positive блокировок и операционного шума).
- **Open questions:** где выставить threshold для перехода legacy cohort из `optional` в `required`.

## Root cause (mandatory)
- **Symptom:** policy enforcement включён, но operational adoption for legacy не формализован в machine-readable отчёт, поэтому migration backlog управляется вручную.
- **Minimal reproduction:** выполнить `scripts/session_audit.sh` и убедиться, что есть только текстовый summary без структурированного списка кандидатов для migration cohort.
- **Evidence to capture:** output `session_audit`, JSON/markdown adoption report, session coverage counts.
- **Five Whys (or equivalent):**
  1. Why? Enforcement реализован, но контур сопровождения legacy не автоматизирован.
  2. Why? В первой волне фокус был на mandatory gates для новых блоков.
  3. Why? Нужен отдельный adoption-аудит слой, который не был частью первой волны.
  4. Why? Без него migration criteria не машиночитаемы и трудно проверяемы.
  5. Why? Нет стандартного артефакта, который можно сравнивать между сессиями.
- **Root cause statement:** отсутствует структурированный adoption report контракт для legacy rollout decisions.
- **Fix mechanism:** добавить structured output в `session_audit` + канонический report с migration cohorts и threshold.

## Reuse-first plan (mandatory)
- **Internal reuse:** `scripts/session_audit.sh`, `scripts/session_check.sh`, `docs/SESSIONS/*`, `docs/SESSION_INDEX.md`.
- **External reuse:** SRE phased rollout / canary / error-budget policy patterns.
- **Why not reinvent the wheel:** ядро governance уже есть; требуется добавить слой отчётности и migration orchestration, а не новый framework.

## Touch-list
- `scripts/session_audit.sh`
- `docs/REPORTS/2026-02-28-process-gates-adoption-audit-a912.md`
- `docs/SESSIONS/SESSION-2026-02-28-process-gates-adoption-audit-a912.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Добавить в `session_audit` machine-readable режим (`--adoption-report-json`) с coverage и candidate lists.
2. Прогнать audit, зафиксировать baseline adoption evidence и migration backlog.
3. Оформить canonical report с cohort criteria (`new/active-legacy/stale-legacy/done-cleanup`).
4. Провалидировать `bash -n` + `session_check` + `session_audit` и подготовить PR handoff.

## DoD
- `session_audit` выдаёт structured adoption report (JSON) без регресса текущего поведения.
- Есть актуальный report с gate coverage и migration backlog.
- Проверки process-gates проходят локально.

## Checks
- `bash -n scripts/session_audit.sh scripts/session_check.sh scripts/session_gate.sh`
- `SESSION_AGENT=a912 scripts/session_check.sh`
- `scripts/session_audit.sh`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a912.json`

## Evidence
- `git diff --stat`
- output `session_check`
- output `session_audit`
- `/tmp/session_adoption_a912.json`
- `docs/REPORTS/2026-02-28-process-gates-adoption-audit-a912.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** одна гипотеза на итерацию, без запуска долгих quality suites.
- **Stop condition:** 2 итерации без новой evidence => остановка и обновление RCA.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased adoption rollout (new sessions required, legacy cohorts by audit score).
- **Go/no-go signals:** доля `missing` в active sessions, false-positive gate incidents, manual overrides.
- **Rollback:** `git revert COMMIT_SHA` и возврат к предыдущему `session_audit` output mode.
- **Post-release monitoring window:** 3 рабочих дня по `session_audit` coverage trend.

## Rollback
- `git revert COMMIT_SHA`
- удалить только новые audit artifacts (`/tmp/session_adoption_a912.json`) без влияния на runtime.

## No-go
- Нельзя переводить legacy сразу в `required` без criteria/evidence.
- Нельзя ослаблять mandatory gates для новых сессий.
- Нельзя выходить за process/docs scope.

## Risks/Blockers
- Большой historical backlog может дать шум в first adoption report.
- Неполные/устаревшие session metadata могут искажать cohort categorization.

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a912.json`
- `Do not touch`: runtime services/routes.
- `Open risks`: noisy legacy dataset.
- `First command to verify`: `bash -n scripts/session_audit.sh scripts/session_check.sh scripts/session_gate.sh`
