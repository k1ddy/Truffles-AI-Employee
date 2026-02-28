# TP-2026-02-27-research-gates-rollout-a900

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-RESEARCH-2026Q1`
- `PARENT_BLOCK_ID`: `PROCESS-GOVERNANCE`
- `DEPENDS_ON`: `none`
- `UNLOCKS`: `PROCESS-GATES-ENFORCEMENT-ADOPTION`

## Название/цель
Внедрить research-driven контракт в канон, шаблоны и локальные session gates, чтобы агент не мог начать нетривиальную реализацию без внешнего исследования, RCA и reuse-решения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/session_start.sh`
- `scripts/session_check.sh`
- `scripts/zero_context_gate.sh`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: `AGENTS.md`, zero-context templates, session/gate scripts, session log artifacts.
- `Baseline commands`:
  - `git status -sb`
  - `sed -n '1,320p' AGENTS.md`
  - `sed -n '1,320p' docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
  - `sed -n '1,320p' docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
  - `sed -n '1,340p' scripts/session_check.sh`
  - `sed -n '1,280p' scripts/zero_context_gate.sh`
- `FACT findings`:
  - В `AGENTS.md` нет жёсткого обязательного external research gate.
  - В шаблоне TP нет обязательных секций `One web search`, `Root cause`, `Reuse-first`, `Release safety`, `Token/run budget`.
  - `session_check.sh` не проверяет research-driven секции Task Package.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `SRE error budget release freeze canary deployment best practices`
- **Date/time (local):** `2026-02-27 13:35, Asia/Almaty`
- **Why this query is precise:** проверяет именно policy связи релизов с надежностью, а не общие советы по CI/CD.
- **Sources opened (from this query):**
  - `Google SRE Workbook: Error Budgets` - `https://sre.google/workbook/error-budget-policy/`
  - `Google SRE Workbook: Canarying Releases` - `https://sre.google/workbook/canarying-releases/`
  - `AWS Well-Architected: perform safe deployment` - `https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prepare_safe_deployment.html`
- **Existing solutions found:** error-budget policy gates, staged rollout/canary, explicit rollback as mandatory release contract.
- **Decision:** `reuse` документированных SRE/Well-Architected практик и встроить их в процессные гейты Truffles.
- **Rejected options:** ad-hoc “инженер решает по ситуации” отклонено как невалидируемое и дрейфующее.
- **Open questions:** нужен ли отдельный CI gate для research sections или достаточно локального `session_check`.

## Root cause (mandatory)
- **Symptom:** агенты иногда начинают реализацию до внешней валидации подхода и принимают ранние решения по частичным сигналам.
- **Minimal reproduction:** создать новый TP без внешнего поиска/RCA/reuse и выполнить сессию; текущие гейты это пропускают.
- **Evidence to capture:** текущие TP/Report templates, `session_check`/`zero_context_gate` поведение до изменений.
- **Five Whys (or equivalent):**
  1. Why? Нет обязательного research section в TP.
  2. Why? Шаблон и гейты не требуют этот раздел.
  3. Why? Исторически фокус был на evidence после кода, а не на pre-implementation decision quality.
  4. Why? Нет формализованной связи между RCA/reuse и приёмкой блока.
  5. Why? Процессный канон не был расширен до research-driven release discipline.
- **Root cause statement:** процессный контракт неполный: отсутствуют обязательные pre-code гейты для research/RCA/reuse/release safety.
- **Fix mechanism:** обновить канон + шаблоны + локальные гейты, чтобы отсутствие этих секций блокировало session check.

## Reuse-first plan (mandatory)
- **Internal reuse:** использовать существующие `session_start.sh`, `session_check.sh`, `zero_context_gate.sh`, шаблоны TP/Report.
- **External reuse:** применить уже известные SRE/Well-Architected паттерны как процессные правила без написания нового фреймворка.
- **Why not reinvent the wheel:** текущие скрипты уже являются точкой контроля; нужно расширение проверок, а не новый pipeline.

## Invariant
- Не ломать существующую логику session governance.
- Не ослаблять текущие quality/stop-the-line правила.
- Не вводить broad refactor вне process/gate scope.

## Scope
- Обновление канона `AGENTS.md`.
- Обновление zero-context шаблонов TP/Report.
- Усиление `scripts/zero_context_gate.sh`.
- Усиление `scripts/session_start.sh` и `scripts/session_check.sh` под новый контракт.
- Усиление `scripts/session_gate.sh` для серверного enforcement `research_gate`/`zero_context_gate` в CI.
- Добавление reliability gate в `ci-livecheck` на базе `ops/console_owner_admin_kpi_snapshot.py --fail-on-breach`.

## Out of scope
- Изменения runtime business logic консультанта.
- Миграция старых закрытых Task Packages.

## Touch-list
- `AGENTS.md`
- `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
- `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
- `scripts/zero_context_gate.sh`
- `scripts/session_start.sh`
- `scripts/session_check.sh`
- `scripts/session_gate.sh`
- `.github/workflows/ci.yml`
- `docs/SESSIONS/SESSION-2026-02-27-research-gates-rollout-a900.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Добавить research-driven policy clauses в `AGENTS.md`.
2. Расширить TP/Report templates обязательными секциями.
3. Обновить `zero_context_gate.sh` под новые секции/токены.
4. Обновить `session_start.sh` и `session_check.sh` для enforced adoption в новых сессиях.
5. Обновить `session_gate.sh`, чтобы CI проверял session-scoped research/zero-context gates по изменённым session log.
6. Добавить в `ci-livecheck` reliability gate с fail-on-breach и artifact evidence.
7. Прогнать локальные проверки (`bash -n`, `session_check`, `zero_context_gate`, YAML parse).
8. Зафиксировать evidence и handoff.

## DoD
- В `AGENTS.md` есть явные mandatory gates: `External Research`, `Root Cause`, `Reuse-First`, `Release Safety`, `Iteration Discipline`.
- TP/Report template содержат все новые обязательные секции.
- `session_start.sh` проставляет gate-маркеры в новой session log.
- `session_check.sh` блокирует сессию при `research_gate=required` и отсутствии обязательных TP section/token.
- `zero_context_gate.sh` проверяет новые секции и запрещает placeholder content.
- `session_gate.sh` валидирует `research_gate`/`zero_context_gate` для изменённых `docs/SESSIONS/SESSION-*.md` в CI.
- `ci-livecheck` блокируется при reliability breach (`console_owner_admin_kpi_snapshot --fail-on-breach`) и сохраняет reliability artifacts.

## Checks
- `bash -n scripts/session_start.sh scripts/session_check.sh scripts/zero_context_gate.sh`
- `bash -n scripts/session_gate.sh`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-27-research-gates-rollout-a900.md --report docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md` (ожидаемо fail для template с placeholders; sanity check)
- `scripts/session_check.sh`
- `python3 - <<'PY' ... yaml.safe_load(open('.github/workflows/ci.yml')) ... PY`

## Evidence
- `git diff --stat`
- `git diff -- AGENTS.md docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md scripts/zero_context_gate.sh scripts/session_start.sh scripts/session_check.sh`
- вывод проверок shell/session.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** после первого fail исправлять только один причинный фактор за итерацию.
- **Stop condition:** 2 подряд прогона без новой evidence -> возврат к RCA.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased adoption через session metadata (`research_gate=required` для новых сессий).
- **Go/no-go signals:** новые сессии проходят `session_check`; старые сессии не ломаются без metadata.
- **Rollback:** откат коммита с process changes.
- **Post-release monitoring window:** первые 3 рабочих дня после merge смотреть ошибки `session_check`/`session_start`.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `AGENTS.md`
  - `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
  - `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
- `Drift closeout rule`:
  - update docs and gates in one block; residual mismatch is recorded as explicit GAP.

## Rollback
- `git revert SHA` в ветке процесса.
- Для локального отката без merge: восстановить изменённые process files до предыдущего commit.

## No-go
- Нельзя добавлять новые обходные “optional” пути для research/RCA секций.
- Нельзя снижать текущие acceptance-гейты ради прохождения checks.
- Нельзя менять runtime/product behavior в этой задаче.

## Risks/Blockers
- Старые активные сессии могут быть несовместимы с новым strict enforcement.
- Риск ложных блокировок снижается metadata-driven режимом (`research_gate=required` только для новых session logs).

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `scripts/session_check.sh` then `AGENTS.md`
- `Do not touch`: runtime business logic files outside touch-list
- `Open risks`: backward compatibility with legacy sessions
- `First command to verify`: `bash -n scripts/session_start.sh scripts/session_check.sh scripts/zero_context_gate.sh`
