# TP-2026-02-28-process-gates-legacy-migration-a913

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-LEGACY-MIGRATION-2026Q2`
- `PARENT_BLOCK_ID`: `PROCESS-GOVERNANCE`
- `DEPENDS_ON`: `PROCESS-GATES-ADOPTION-AUDIT-2026Q2`
- `UNLOCKS`: `PROCESS-GATES-LEGACY-MIGRATION-WAVE2-2026Q2`

## Название/цель
Выполнить первую контролируемую миграцию legacy cohort: перевести часть active `legacy_missing` сессий на явный режим `optional` для research-driven gate полей, без включения strict enforcement.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/session_audit.sh`
- `docs/REPORTS/2026-02-28-process-gates-adoption-audit-a912.md`

## Invariant
- Не ослаблять `required` enforcement для новых сессий.
- Не менять runtime/business logic.
- Миграция только metadata/session-governance уровня.

## Scope
- Выбрать ограниченную когорту stale active `legacy_missing` сессий.
- Добавить явные поля:
  - `research_gate: optional`
  - `root_cause_gate: optional`
  - `reuse_gate: optional`
  - `release_safety_gate: optional`
- Подтвердить снижение `missing` в `session_audit` отчёте.

## Out of scope
- Перевод legacy сразу в `required`.
- Массовая миграция всего backlog за один блок.
- Правки runtime/CI/deploy.

## One web search (mandatory before implementation)
- **Query (exact):** `incremental migration strategy legacy metadata rollout in batches with audit evidence`
- **Date/time (local):** `2026-02-28 17:10 (Asia/Almaty)`
- **Why this query is precise:** нужен паттерн batch-модернизации legacy конфигурации с измеримым прогрессом и безопасным rollback.
- **Sources opened (from this query):**
  - `Google SRE Workbook — Canarying Releases` — `https://sre.google/workbook/canarying-releases/`
  - `Google SRE Workbook — Error Budget Policy` — `https://sre.google/workbook/error-budget-policy/`
  - `AWS Well-Architected — Perform safe deployment through automation` — `https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prepare_safe_deployment.html`
- **Existing solutions found:** staged cohort rollout + explicit telemetry before next wave.
- **Decision:** `reuse` существующий `session_audit` JSON + controlled doc-only metadata migration batch.
- **Rejected options:** full backlog rewrite in one pass (high operational risk, hard review, noisy rollback).
- **Open questions:** оптимальный wave size для следующего блока после валидации wave-1.

## Root cause (mandatory)
- **Symptom:** в adoption report большая доля `legacy_missing` (108), из-за чего migration governance не может перейти к фазе cohort-based strictness.
- **Minimal reproduction:** `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a912.json` -> `legacy_missing=108`.
- **Evidence to capture:** before/after counts (`missing`, `optional`), список мигрированных session IDs, `session_check` output.
- **Five Whys (or equivalent):**
  1. Why? Legacy session files не содержат gate mode полей.
  2. Why? Enforcement rollout начинался с новых сессий.
  3. Why? Нужен phased migration для старых сессий.
  4. Why? Без metadata migration audit не отражает зрелость adoption.
  5. Why? Нет baseline wave execution для legacy cohort.
- **Root cause statement:** отсутствие поэтапной metadata миграции legacy сессий к новой gate matrix.
- **Fix mechanism:** выполнить wave-1 batch migration `missing -> optional` по stale active cohort и зафиксировать delta метрик.

## Reuse-first plan (mandatory)
- **Internal reuse:** `scripts/session_audit.sh` structured JSON, existing `docs/SESSIONS/*` metadata format.
- **External reuse:** phased rollout practices (SRE/AWS).
- **Why not reinvent the wheel:** требуется только controlled metadata update + existing audit tooling.

## Touch-list
- `docs/SESSIONS/SESSION-*.md` (только выбранная cohort)
- `docs/REPORTS/2026-02-28-process-gates-legacy-migration-a913.md`
- `docs/TASK_PACKAGES/TP-2026-02-28-process-gates-legacy-migration-a913.md`
- `docs/SESSIONS/SESSION-2026-02-28-process-gates-legacy-migration-a913.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Снять baseline adoption metrics (`missing/optional`) перед миграцией.
2. Выбрать wave-1 cohort (20 stale active `legacy_missing`).
3. Проставить gate mode `optional` в выбранных session files.
4. Повторить audit и подтвердить измеримый delta.
5. Выпустить report + handoff для wave-2.

## DoD
- Wave-1 cohort мигрирована без ошибок формата.
- `legacy_missing` уменьшен минимум на размер wave-1.
- `session_check` и `session_audit` проходят.
- Есть canonical report с before/after evidence.

## Checks
- `bash -n scripts/session_audit.sh scripts/session_check.sh scripts/session_gate.sh`
- `SESSION_AGENT=a913 scripts/session_check.sh`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a913_before.json`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a913_after.json`
- `jq` compare of before/after counts

## Evidence
- `/tmp/session_adoption_a913_before.json`
- `/tmp/session_adoption_a913_after.json`
- migrated session list (in report)
- `docs/REPORTS/2026-02-28-process-gates-legacy-migration-a913.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** один migration batch, один after-audit.
- **Stop condition:** после wave-1 без ожидаемого delta -> stop и RCA.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased migration by cohort (`optional` first, `required` later by owner decision).
- **Go/no-go signals:** expected delta in `missing`, no invalid modes, no session_check regressions.
- **Rollback:** `git revert COMMIT_SHA` for wave patch.
- **Post-release monitoring window:** до следующей migration wave.

## Rollback
- `git revert COMMIT_SHA`
- удалить только wave-1 metadata edits.

## No-go
- Не включать `required` для legacy без отдельного решения.
- Не менять сессии вне выбранной когорты.
- Не трогать runtime код.

## Risks/Blockers
- Некоторые legacy файлы могут иметь нестандартный формат.
- Часть stale sessions может требовать закрытия вместо миграции.

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: baseline/after JSON compare.
- `Do not touch`: runtime services.
- `Open risks`: noisy stale backlog.
- `First command to verify`: `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a913_before.json`
