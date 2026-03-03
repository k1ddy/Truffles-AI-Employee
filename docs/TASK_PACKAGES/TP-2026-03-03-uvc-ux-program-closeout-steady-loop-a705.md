# TP-2026-03-03-uvc-ux-program-closeout-steady-loop-a705

## Block identity
- `BLOCK_ID`: UVC-UX-PROGRAM-CLOSEOUT-A705
- `PARENT_BLOCK_ID`: UVC-UX-STAGE5-A705
- `DEPENDS_ON`: merge of PR `#881` into `main` (`c21ccf60`)
- `UNLOCKS`: UVC-UX-STEADY-STATE-OPERATIONS-A705

## Название/цель
Закрыть handoff после UVC UX Stage 1-5 в steady-state режим: автоматизировать регулярный Platform Admin control loop (anti-drift + KPI guard + optional e2e lane) как повторяемый deterministic контур без добавления новых вкладок и без изменения runtime ownership по вкладкам.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage5-rollout-efficiency-a705.md`
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: automation validates existing ownership contract through `check:uvc-antidrift`.
  - proof: fail-closed script/workflow step.
- `REQ-2` intuitive business loop and stable operations:
  - solution: weekly deterministic control loop with clear run summary and thresholds.
  - proof: generated run artifacts + guard exit status.
- `REQ-3` no shortcuts/costyl in default path:
  - solution: reuse existing checks/tools; no runtime semantic hardcode.
  - proof: touch-list excludes runtime business logic files.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/platform_admin_control_loop.sh` (new)
  - `.github/workflows/platform-admin-control-loop.yml` (new)
  - `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "partial|manual|control loop" docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/uvc_stage5_kpi_main_postmerge_c21_a705.json`
  - `npm --prefix console-web run check:uvc-antidrift`
- `FACT findings`:
  - Stage 1-5 already closed and merged to `main`; post-merge checks are green.
  - Control-loop runbook exists, but automation is still partly manual (`[partial]` in canon audit).

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.github.com actions schedule workflow cron workflow_dispatch`
- **Date/time (local):** `2026-03-03 16:20 +05`
- **Why this query is precise:** нужен первоисточник по безопасной автоматизации регулярного workflow запуска (schedule + manual dispatch) для steady-state control loop.
- **Sources opened (from this query):**
  - GitHub Docs: `https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule`
- **Existing solutions found:** scheduled workflow via POSIX cron + optional `workflow_dispatch`, with guidance on schedule delay/high-load and default-branch behavior.
- **Decision:** `integrate` — добавить отдельный workflow для control-loop по расписанию и ручному запуску.
- **Rejected options:** ad-hoc manual execution only.

## Root cause (mandatory)
- **Symptom:** контрольный контур Platform Admin формально описан, но регулярное исполнение зависит от ручного запуска и человеческой дисциплины.
- **Minimal reproduction:**
  1. Открыть `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`.
  2. Проверить `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.
  3. Увидеть `Runbook ... [partial]`, потому что remediation/control jobs не автоматизированы.
- **Evidence to capture:** script output artifact, workflow definition, updated canon/status entries.
- **Five Whys (or equivalent):**
  1. Почему статус `partial`? Нет автоматизированного повторяемого запуска.
  2. Почему это риск? Ручной режим пропускает окна контроля.
  3. Почему это влияет на UX/операции? Дрейф и регрессии могут замечаться поздно.
  4. Почему не использовать существующий CI напрямую? Нужен отдельный, узко сфокусированный control-loop контур.
  5. Почему сейчас? Stage 1-5 закрыты, следующий контрактный шаг — steady-state handoff.
- **Root cause statement:** отсутствует автоматизированный execution-контур для уже определённого Platform Admin control loop, из-за чего устойчивость процесса зависит от ручных действий.
- **Fix mechanism:** добавить deterministic wrapper-script + scheduled/dispatch workflow + evidence contract в docs/STATE.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `ops/console_platform_admin_kpi_snapshot.py`
  - `console-web/scripts/check-uvc-antidrift.mjs` (`npm run check:uvc-antidrift`)
  - existing `platform-admin` e2e suite (optional run mode)
  - existing runbook structure (`docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`)
- **External reuse:** official GitHub Actions schedule semantics from docs.github.com.
- **Why not reinvent the wheel:** базовые проверки уже реализованы; нужна интеграция в единый repeatable job, а не новые проверки.

## Invariant
- Не добавлять новые top-level вкладки/разделы UI.
- Не менять ownership контракт вкладок (`Tenants` orchestration, `Integrations` fact-only, `Workspace` execute, `Ops` verify/incidents).
- Не ослаблять `anti-drift`/quality gates.

## Scope
- Добавить единый shell entrypoint для Platform Admin control loop.
- Добавить scheduled + workflow_dispatch CI workflow для control-loop.
- Обновить runbook и canon/status документы до `match` на automation coverage.

## Out of scope
- Любые изменения runtime бизнес-логики API/LLM policy-core.
- Новый UX функционал вкладок.
- Изменение контрактов `/admin/control-tower/*`.

## Touch-list
- `scripts/platform_admin_control_loop.sh` (new)
- `.github/workflows/platform-admin-control-loop.yml` (new)
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
- `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Зафиксировать post-merge baseline (`main@c21`) и evidence paths.
2. Реализовать wrapper-script, который fail-closed гоняет `KPI guard + anti-drift` и опционально e2e lane.
3. Добавить отдельный workflow (`schedule + workflow_dispatch`) для регулярного запуска wrapper-script.
4. Обновить runbook/canon/master/state/session артефакты по результату automation handoff.
5. Прогнать local checks, собрать evidence и закрыть блок.

## DoD
- `scripts/platform_admin_control_loop.sh` выполняется локально и пишет run artifact.
- Workflow file добавлен и валиден по синтаксису/ссылкам шагов.
- `CANON_VS_IMPLEMENTED` больше не содержит partial-gap по control-loop automation.
- `STATE.md` содержит FACT с command/evidence по steady-state handoff.

## Checks
- `bash -n scripts/platform_admin_control_loop.sh`
- `scripts/platform_admin_control_loop.sh --run-id local-a705 --run-e2e 0`
- `npm --prefix console-web run check:uvc-antidrift`
- `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/uvc_stage5_kpi_main_postmerge_c21_a705.json`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- `/tmp/platform_admin_control_loop/local-a705/summary.json`
- `/tmp/platform_admin_control_loop/local-a705/kpi_snapshot.json`
- Updated docs paths from touch-list.

## Token / run budget (mandatory for expensive suites)
Max full runs: `1` full e2e lane (optional mode only when explicitly enabled).
Fail-fast / scenario lock: default `run-e2e=0`; scheduled loop runs only `kpi + anti-drift`.
Stop condition: any fail in KPI guard or anti-drift blocks completion.
Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive automation only; no runtime-path mutations.
- **Go/no-go signals:** wrapper-script green, session checks green, no contract regressions.
- **Rollback:** `git revert` new script/workflow commit; return to manual runbook path.
- **Post-release monitoring window:** `7d` weekly schedule observation with artifact review.

## Rollback
- Revert commit with automation files, keep previous manual runbook procedure.

## No-go
- Включать silent-ignore для failed checks.
- Подменять бизнес-сигналы из KPI snapshot “красивыми” текстами без фактов.
- Делать workflow, который не сохраняет run artifacts.

## Risks/Blockers
- Scheduled workflow может стартовать с задержкой в high-load windows (GitHub Actions limitation).
- Для optional e2e режима нужен корректный `PLAYWRIGHT_BASE_URL` и доступность target среды.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remediation actions по инцидентам остаются operator-driven, не fully auto-remediated.
- `Why not in this block`: цель блока — deterministic observability/control loop automation, не auto-repair.
- `Risk if deferred`: задержка реакции на инциденты при отсутствии дежурного оператора.
- `Linked follow-up Task Package(s)`: `UVC-UX-STEADY-STATE-OPERATIONS-A705`.
- `Expiry/trigger to stop deferral`: при повторяющихся P0/P1 инцидентах без SLA-resolve в 2 подряд weekly loops.

## Next-block contract (mandatory)
- `Next block objective`: UVC-UX-STEADY-STATE-OPERATIONS-A705 (operator-assist remediation automation on top of control-loop evidence).
- `First deterministic check command`: `rg -n "platform_admin_control_loop|platform-admin-control-loop" scripts .github/workflows docs/runbooks`
- `Blocked-by conditions`: control-loop automation block not fully green/evidenced.
- `Owner role for closure`: Brain + Top Architect.
