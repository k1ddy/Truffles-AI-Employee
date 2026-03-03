# TP-2026-03-03-uvc-ux-steady-state-operations-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STEADY-STATE-OPERATIONS-A705
- `PARENT_BLOCK_ID`: UVC-UX-PROGRAM-CLOSEOUT-A705
- `DEPENDS_ON`: merged PR `#882` (`366d2687`) with control-loop automation handoff
- `UNLOCKS`: UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705

## Название/цель
Закрыть residual после UVC Stage 1-5 + program closeout: перевести Platform Admin remediation из полностью ручного режима в operator-assist deterministic loop на базе уже собранных control-loop артефактов, без добавления новых вкладок и без изменения ownership контрактов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-program-closeout-steady-loop-a705.md`
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`

## Requirement traceability (mandatory)
- `REQ-1` нет disconnected/duplicate функций и кнопок:
  - решение: remediation automation работает поверх существующего `Ops Jobs` контракта и текущего control-loop, без новых UI-поверхностей.
  - proof: touch-list не включает новые top-level routes/pages.
- `REQ-2` интуитивная бизнес-логика и подсказки:
  - решение: единый remediation brief с plain-language шагами и explicit next actions.
  - proof: markdown brief + deterministic plan JSON в artifacts.
- `REQ-3` reuse-first, без костылей:
  - решение: reuse существующих `ops/console_platform_admin_kpi_snapshot.py`, `scripts/platform_admin_control_loop.sh`, `/console/v1/ops/jobs/run` payload contract.
  - proof: нет runtime-core изменений в API policy/LLM слоях.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/platform_admin_control_loop.sh`
  - `ops/console_platform_admin_kpi_snapshot.py`
  - `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
  - `contracts/console_api/openapi.v1.yaml` (`ConsoleOpsJobRunRequest`)
- `Baseline commands`:
  - `scripts/platform_admin_control_loop.sh --run-id baseline-a705 --run-e2e 0 --output-root /tmp/platform_admin_control_loop`
  - `rg -n "outbox_process|ops/jobs/run|archive_pending_older_than_hours" docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md contracts/console_api/openapi.v1.yaml`
- `FACT findings`:
  - control-loop automation уже есть и стабилен, но remediation шаги остаются операторскими и не собраны в единый deterministic assist-контур.

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google/sre-book incident response`
- **Date/time (local):** `2026-03-03 17:13 +0500`
- **Sources opened (from this query):**
  - `https://sre.google/sre-book/emergency-response/`
- **Found reusable solution:** incident loop с чётким циклом `mitigate -> restore service -> preserve evidence -> postmortem`.
- **Decision:** `integrate` — оформить remediation assist как artifact-first cycle с явным decision + evidence + next actions.
- **Rejected options:** ad-hoc manual-only runbook sequence без machine-readable plan.

## Root cause (mandatory)
- **Symptom:** после closeout weekly control-loop фиксирует состояние, но remediation по инцидентам исполняется вручную и не стандартизирована между операторами.
- **Minimal reproduction:**
  1. Запустить `scripts/platform_admin_control_loop.sh --run-e2e 0`.
  2. Получить `kpi_snapshot.json`/`summary.json`.
  3. Увидеть, что дальнейшие remediation шаги определяются вручную по runbook, без единого plan artifact.
- **Evidence:**
  - `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-program-closeout-steady-loop-a705.md` residual debt section.
  - `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md` (manual sequence sections).
- **Five Whys:**
  1. Почему remediation неоднороден? Нет machine-readable assist слоя.
  2. Почему это важно? Операторы принимают разные решения при одинаковом guard status.
  3. Почему риск бизнесовый? Время реакции и качество rollback/go-no-go нестабильны.
  4. Почему не решено в closeout? Closeout закрыл observability+automation запуска, но не слой remediation decisions.
  5. Почему сейчас? Это прямой `Next-block contract` после закрытого closeout.
- **Root cause statement:** отсутствует детерминированный operator-assist remediation artifact между KPI guard и фактическим ops action execution.
- **Fix mechanism:** добавить remediation-assist script + интеграцию в control-loop + runbook contract + deterministic test.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `ops/console_platform_admin_kpi_snapshot.py`
  - `scripts/platform_admin_control_loop.sh`
  - existing Ops Jobs contract (`outbox_process` with `dry_run/execute`).
- **External reuse:**
  - SRE emergency-response loop (incident cycle discipline).
- **Why not build new UI/API:** текущие вкладки/контракты уже покрывают execution; нужен orchestration-assist слой, не новая продуктовая поверхность.

## Invariant
- Не добавлять новые top-level вкладки/маршруты.
- Не менять ownership контракт вкладок (`Tenants` orchestration, `Integrations` fact-only, `Workspace` execute, `Ops` verify/incidents).
- Не ослаблять anti-drift, session-gate и fail-closed guard логику.

## Scope
- Добавить deterministic remediation-assist script на базе `kpi_snapshot.json`.
- Интегрировать assist шаг в `platform_admin_control_loop.sh` как artifact stage.
- Обновить runbook и audit/status docs под steady-state operations closure.
- Добавить минимум один deterministic test для assist contract.

## Out of scope
- Изменения runtime policy-core/LLM semantics.
- Новые UI разделы и IA перестройка.
- Изменение backend контрактов `/admin/control-tower/*` и бизнес-ролей.

## Touch-list
- `ops/platform_admin_remediation_assist.py` (new)
- `scripts/platform_admin_control_loop.sh`
- `truffles-api/tests/test_platform_admin_remediation_assist.py` (new)
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
- `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-steady-state-operations-a705.md` (new)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Реализовать `ops/platform_admin_remediation_assist.py` (plan + brief + command template artifacts).
2. Интегрировать assist stage в `scripts/platform_admin_control_loop.sh` и summary contract.
3. Добавить deterministic pytest на assist contract (status mapping + plan outputs).
4. Обновить runbook/audit/master/state/session docs и зафиксировать evidence.
5. Прогнать checks, session gate, подготовить PR.

## DoD
- После control-loop запуска появляется remediation plan artifact (JSON + brief).
- Plan детерминированно отражает `guard.status`/`incident_class` и рекомендуемые ops actions.
- Есть минимум один automated test на assist contract.
- Документы синхронизированы: runbook + canon + master report + state.

## Checks
- `python3 -m py_compile ops/platform_admin_remediation_assist.py`
- `pytest -q truffles-api/tests/test_platform_admin_remediation_assist.py`
- `scripts/platform_admin_control_loop.sh --run-id steady-ops-a705 --run-e2e 0 --output-root /tmp/platform_admin_control_loop`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- `/tmp/platform_admin_control_loop/steady-ops-a705/summary.json`
- `/tmp/platform_admin_control_loop/steady-ops-a705/remediation_plan.json`
- `/tmp/platform_admin_control_loop/steady-ops-a705/remediation_brief.md`
- Updated docs from touch-list + PR URL + CI run URL.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1` deterministic lane (`--run-e2e 0`) for acceptance evidence in this block.
- Fail-fast / scenario lock: e2e disabled by default, rely on control-loop guard + targeted pytest.
- Stop condition: any failed guard/test/session gate blocks completion.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive operator-assist automation only; no runtime mutation of decision pipeline.
- **Go/no-go signals:** remediation artifacts produced + tests green + session gate green.
- **Rollback:** revert commit with new assist script/control-loop integration.
- **Rollback procedure and verification:** revert commit with new assist script/control-loop integration, then rerun `scripts/platform_admin_control_loop.sh --run-id rollback-check-a705 --run-e2e 0`.
- **Post-release monitoring window:** 7d weekly schedule review of remediation artifacts.

## Rollback
- `git revert COMMIT_SHA` and keep previous manual remediation runbook path.

## No-go
- Делать auto-execute destructive remediation без dry-run plan.
- Маскировать critical guard как warning через форматирование.
- Добавлять новые UI вкладки вместо оптимизации существующего Ops loop.

## Risks/Blockers
- KPI snapshot может быть неполным при сетевых ограничениях (guard=`unknown`).
- False-positive action recommendations при неполной причине отказа (mitigated by class-based mapping + manual confirm).

## Branch / Worktree / Merge
- Branch: `feat/2026-03-02-uvc-ux-stage1-pr-a705`
- Worktree: `/home/zhan/worktrees/2026-03-02-uvc-ux-stage1-pr-a705`
- Base ref: `origin/main`
- Merge policy: PR -> required checks green -> merge commit
- Cleanup: Brain/Top Architect after merge

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: auto-remediation execute path remains human-confirmed (assist-only, no autonomous changes).
- `Why not in this block`: нужно сохранить fail-safe ownership и избежать silent destructive actions.
- `Risk if deferred`: часть MTTR зависит от оператора, но решение уже стандартизировано assist-artifact.
- `Linked follow-up Task Package(s)`: `UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705`.
- `Expiry/trigger to stop deferral`: если 2 подряд weekly loops требуют одинаковые manual steps без упрощения.

## Next-block contract (mandatory)
- `Next block objective`: UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705 (close canonical gaps and stale open backlog alignment for UVC surface).
- `First deterministic check command`: `rg -n "\[partial\]|\| Open \|" docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: steady-state operations block not merged with evidence.
- `Owner role for closure`: Brain + Top Architect.
