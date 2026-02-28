# TP-2026-02-28-process-gates-enforcement-adoption-a911

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-ENFORCEMENT-ADOPTION-2026Q1`
- `PARENT_BLOCK_ID`: `PROCESS-GOVERNANCE`
- `DEPENDS_ON`: `PROCESS-GATES-RESEARCH-2026Q1`
- `UNLOCKS`: `PROCESS-GATES-ADOPTION-AUDIT-2026Q2`

## Название/цель
Довести внедрённые research-driven gates до операционного adoption-режима: зафиксировать политику применения к новым/текущим сессиям, исключить ложные блокировки и добавить прозрачный audit-контур.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/session_start.sh`
- `scripts/session_check.sh`
- `scripts/session_gate.sh`
- `scripts/session_audit.sh`

## Invariant
- Не ослаблять текущие mandatory gates (`research/root_cause/reuse/release_safety/iteration`).
- Не ломать doc-only fast path и текущую session governance механику.
- Не менять runtime business logic.

## Scope
- Зафиксировать adoption-policy для research-driven gates в каноне/процессе.
- Добавить диагностический контур для выявления сессий/TP без нужных секций.
- Подготовить безопасный rollout для legacy-сессий (без ложных стопов).

## Out of scope
- Изменения продуктовой логики консультанта и provider runtime.
- Долгие quality/eval прогоны.
- Массовая миграция всех исторических TP в рамках одного блока.

## One web search (mandatory before implementation)
- **Query (exact):** `change management policy enforcement gradual rollout backward compatibility`
- **Date/time (local):** `2026-02-28 15:42 (Asia/Almaty)`
- **Why this query is precise:** нужен практический шаблон постепенного включения обязательных process-gates без деградации действующего delivery-потока.
- **Sources opened (from this query):**
  - `Google SRE Workbook: Error Budget Policy` - `https://sre.google/workbook/error-budget-policy/`
  - `Google SRE Workbook: Canarying Releases` - `https://sre.google/workbook/canarying-releases/`
  - `AWS Well-Architected: Perform safe deployment through automation` - `https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prepare_safe_deployment.html`
- **Existing solutions found:** phased rollout with explicit gates, blast-radius control, reversible rollout path, evidence-first go/no-go.
- **Decision:** `reuse` phased enforcement pattern и применить его к session/process gates Truffles.
- **Rejected options:** одномоментный strict enforcement для всех legacy-сессий отклонён из-за высокого риска ложных блокировок.
- **Open questions:** где провести границу между `optional` и `required` для активных legacy-сессий.

## Root cause (mandatory)
- **Symptom:** после внедрения research-driven gates часть контуров остаётся неравномерной: новые сессии покрыты, но adoption по legacy и audit-прозрачность неполные.
- **Minimal reproduction:** выбрать активную legacy-сессию без явных research секций и проверить `session_check`/`session_gate` поведение по current policy.
- **Evidence to capture:** session logs, TASK_PACKAGE coverage, gate output (`session_check`, `session_gate`, `session_audit`).
- **Five Whys (or equivalent):**
  1. Why? Initial rollout закрыл contract, но не полностью формализовал adoption для legacy.
  2. Why? Фокус был на stop-the-line enforcement для новых блоков.
  3. Why? Не было отдельного блока на policy rollout cadence и audit.
  4. Why? Не определены чёткие критерии перевода legacy-сессий в `required`.
  5. Why? Отсутствует явный adoption-audit loop в process runbooks.
- **Root cause statement:** отсутствует отдельный операционный слой adoption/policy-audit поверх уже внедрённых research gates.
- **Fix mechanism:** добавить policy+audit контур с phased enforcement, фиксированными критериями и evidence-отчётностью.

## Reuse-first plan (mandatory)
- **Internal reuse:** использовать `session_start`, `session_check`, `session_gate`, `session_audit`, текущие TP/session templates.
- **External reuse:** применить SRE/Well-Architected rollout principles как process-policy.
- **Why not reinvent the wheel:** база gate-механик уже есть; нужен controlled adoption и audit, а не новый фреймворк.

## Touch-list
- `AGENTS.md`
- `STATE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
- `scripts/session_check.sh`
- `scripts/session_gate.sh`
- `scripts/session_audit.sh`
- `docs/SESSIONS/SESSION-2026-02-28-process-gates-enforcement-adoption-a911.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Зафиксировать текущий adoption GAP по active sessions (без правок runtime).
2. Уточнить policy матрицу `required|optional|off` для research-driven gates.
3. Добавить/уточнить диагностические проверки и отчётность по adoption coverage.
4. Прогнать быстрые локальные проверки process gates.
5. Подготовить evidence и handoff для следующего adoption-audit блока.

## DoD
- Есть явный и проверяемый adoption policy для research-driven gates.
- Есть диагностический output/отчёт, показывающий coverage и остаточные GAP.
- Нет регресса по текущим `session_check`/`session_gate` для новых required-сессий.
- Все изменения ограничены process/docs scope.

## Checks
- `bash -n scripts/session_check.sh scripts/session_gate.sh scripts/session_audit.sh`
- `SESSION_AGENT=a911 scripts/session_check.sh`
- `scripts/session_audit.sh`

## Evidence
- `git diff --stat`
- `session_check` output
- `session_audit` output
- обновлённые `docs/SESSIONS/*` + `docs/SESSION_INDEX.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** одна причинная гипотеза на итерацию.
- **Stop condition:** 2 итерации без новой evidence => возврат к RCA/research.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased policy rollout (new sessions first, legacy by explicit adoption criteria).
- **Go/no-go signals:** `session_check` pass-rate, false-positive incidents, audit coverage.
- **Rollback:** revert policy-script commit и возврат к previous mode.
- **Post-release monitoring window:** минимум 3 рабочих дня по session gate telemetry.

## Rollback
- `git revert COMMIT_SHA` для process/doc изменений.
- Для локального непринятого блока: откат рабочего дерева до base ref.

## No-go
- Нельзя отключать mandatory gates ради прохождения CI.
- Нельзя вводить silent fallback, который маскирует policy нарушения.
- Нельзя расширять scope в runtime core.

## Risks/Blockers
- Риск ложных блокировок на legacy-сессиях без staged policy.
- Риск неполного evidence, если audit-выводы не стандартизированы.

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `scripts/session_audit.sh` и active sessions coverage.
- `Do not touch`: runtime routes/services вне process scope.
- `Open risks`: false-positive blocks on legacy sessions.
- `First command to verify`: `bash -n scripts/session_check.sh scripts/session_gate.sh scripts/session_audit.sh`
