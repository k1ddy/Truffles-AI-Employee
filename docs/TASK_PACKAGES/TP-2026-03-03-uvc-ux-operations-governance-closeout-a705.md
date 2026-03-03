# TP-2026-03-03-uvc-ux-operations-governance-closeout-a705

## Block identity
- `BLOCK_ID`: UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705
- `PARENT_BLOCK_ID`: UVC-UX-STEADY-STATE-OPERATIONS-A705
- `DEPENDS_ON`: merge of PR `#883` on `main` (`27147d14597466e97895c74addce4f2f885beca4`)
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705

## Название/цель
Закрыть governance-дрейф UVC-аудита в существующем Console контуре: убрать дубли/расхождения в canonical audit документах, добавить fail-closed детерминированный guard и встроить его в control-loop + CI, чтобы drift не возвращался.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-steady-state-operations-a705.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/platform_admin_control_loop.sh`
  - `scripts/check_console_audit_governance.py` (new)
  - `.github/workflows/ci.yml`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
  - `truffles-api/tests/test_check_console_audit_governance.py` (new)
- `Baseline commands`:
  - `rg -n "\[partial\]|\| Open \|" docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `rg -n "UX-08|UX-26" docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `scripts/platform_admin_control_loop.sh --help`
  - `rg -n "check:uvc-antidrift|console-contract-predeploy" .github/workflows/ci.yml`
- `FACT findings`:
  - В `UX_BACKLOG` есть повторяющиеся ID (`UX-08`, `UX-26`) и stale `Open` записи без deterministic guard against duplication.
  - В `CANON_VS_IMPLEMENTED` есть повторяемый `partial`-drift по Integrations RBAC и некорректная маркировка manager knowledge как `partial` вместо `match`.
  - Existing anti-drift gate защищает OpenAPI/UI contracts, но не валидирует консистентность audit governance docs.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python re module named groups`
- **Date/time (local):** `2026-03-03 17:41 (+05, Asia/Almaty)`
- **Why this query is precise:** для детерминированного парсинга markdown-строк governance-checker нужен безопасный и читаемый regex подход с именованными группами.
- **Sources opened (from this query):**
  - Python docs `re` module: `https://docs.python.org/3/library/re.html`
- **Existing solutions found:** named groups, explicit match objects, strict validation branch.
- **Decision:** `reuse/integrate` Python stdlib (`re`, `argparse`, `json`) без внешних зависимостей.
- **Rejected options:** markdown parser dependency (избыточно для простого deterministic gate).

## Root cause (mandatory)
- **Symptom:** после закрытия UVC Stage1..5 + steady-state в audit документах остались дубли и stale partial/open записи, что создаёт ложный сигнал о незакрытом UVC UX contract.
- **Minimal reproduction:**
  1. Выполнить `rg -n "\[partial\]|\| Open \|" docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`.
  2. Сравнить повторяющиеся backlog IDs и дубли partial по Integrations RBAC.
- **Evidence to capture:** before/after doc diff, guard output JSON, control-loop summary with governance step, CI gate wiring.
- **Five Whys (or equivalent):**
  1. Почему дубли остались? Потому что после функциональных UX блоков не было отдельного governance closeout шага.
  2. Почему это не ловилось CI? Потому что текущий anti-drift gate покрывает contracts/selectors/OpenAPI, но не canonical backlog hygiene.
  3. Почему это риск? Потому что stale backlog/canon drift портит decision quality следующего planning wave.
  4. Почему риск повторяемый? Потому что нет fail-closed machine-check для audit docs consistency.
  5. Почему нужен отдельный блок? Потому что это cross-doc + control-loop + CI governance concern, не локальный cosmetic fix.
- **Root cause statement:** отсутствует детерминированный governance-checker для консистентности UVC audit canon/backlog, из-за чего после merge возможен устойчивый drift в документах и операционном контуре.
- **Fix mechanism:** добавить machine-check script и встроить его в control-loop/CI, одновременно устранить текущие фактические дубли/ошибочные статусы в audit docs.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `scripts/platform_admin_control_loop.sh` as single entrypoint.
  - existing CI lane `console-contract-predeploy`.
  - existing audit docs (`CANON_VS_IMPLEMENTED`, `UX_BACKLOG`) as source-of-truth for governance pass/fail.
- **External reuse:** Python stdlib regex/argparse/json patterns from official docs.
- **Why not reinvent the wheel:** не нужен новый pipeline; расширяем уже действующие fail-closed gates.

## Invariant
- Не добавлять новые top-level UI tabs/routes.
- Не менять runtime core/LLM semantics.
- Сохранить existing UVC anti-drift gate (`check:uvc-antidrift`) без ослабления.
- Governance closeout должен быть fail-closed и machine-checkable.

## Scope
- Add deterministic audit-governance checker script and tests.
- Wire checker into `platform_admin_control_loop.sh` and CI `console-contract-predeploy`.
- Clean duplicated/stale entries in `CANON_VS_IMPLEMENTED` and `UX_BACKLOG`.
- Sync runbook/master/session/state evidence for the new block.

## Out of scope
- Feature delivery in new UI surfaces.
- Large architectural refactor of `console.py` or `ProvisioningWizard.tsx`.
- RBAC behavior changes in runtime endpoints.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-operations-governance-closeout-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `scripts/check_console_audit_governance.py` (new)
- `truffles-api/tests/test_check_console_audit_governance.py` (new)
- `scripts/platform_admin_control_loop.sh`
- `.github/workflows/ci.yml`
- `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-operations-governance-closeout-a705.md` (new)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Create new TP + switch active session metadata to this block.
2. Implement `check_console_audit_governance.py` with fail-closed checks (duplicate UX IDs, missing/duplicate gap tags, malformed table rows).
3. Add deterministic tests for checker with pass/fail fixtures.
4. Integrate checker into `platform_admin_control_loop.sh` summary/artifacts and CI `console-contract-predeploy`.
5. Clean current canonical drift entries in `CANON_VS_IMPLEMENTED.md` and `UX_BACKLOG.md`.
6. Update runbook/index/master/state/session docs and capture evidence artifact.
7. Run checks, commit, push, open PR.

## DoD
- Checker exists and fails on duplicated backlog IDs/canon gap issues.
- Control-loop summary contains governance step status + governance artifact path.
- CI `console-contract-predeploy` runs governance checker in addition to anti-drift.
- Current duplicates/stale mismatches in audit docs are removed.
- Deterministic tests for checker are green.
- Session/state/report docs reflect this block with evidence.

## Checks
- `python3 -m py_compile scripts/check_console_audit_governance.py`
- `pytest -q truffles-api/tests/test_check_console_audit_governance.py`
- `bash -n scripts/platform_admin_control_loop.sh`
- `scripts/platform_admin_control_loop.sh --run-id governance-closeout-a705 --run-e2e 0 --output-root /tmp/platform_admin_control_loop`
- `cd console-web && npm run check:uvc-antidrift`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Code diff for checker + integration.
- Checker test output.
- Control-loop summary/artifact paths including governance audit JSON.
- Updated canonical docs diff showing resolved duplicates/stale entries.
- Session/STATE/master updates with exact evidence paths.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` control-loop runs for this block.
- **Fail-fast / scenario lock:** no full e2e lane; `--run-e2e 0` for deterministic governance closeout.
- **Stop condition:** two consecutive failures without new RCA evidence -> stop-the-line.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** canary via CI predeploy lane first, then control-loop adoption in regular scheduled run.
- **Go/no-go signals:** checker tests green + control-loop governance step pass + CI predeploy pass.
- **Rollback:** revert checker integration commits and rerun existing anti-drift baseline.
- **Post-release monitoring window:** next scheduled `platform-admin-control-loop` run.

## Rollback
- Revert touched commits for checker/integration/docs and rerun:
  - `cd console-web && npm run check:uvc-antidrift`
  - `scripts/platform_admin_control_loop.sh --run-id rollback-a705 --run-e2e 0`

## No-go
- Добавлять новый governance pipeline вне существующего control-loop.
- Ослаблять existing anti-drift or CI gates.
- Оставлять duplicate UX IDs/partial drift как "known issue" без machine-check.

## Risks/Blockers
- Existing historical docs may include legacy duplicate patterns; fail-closed gate must focus only on canonical audit files.
- Markdown table parsing can be brittle if schema drifts without checker updates.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `UX-11` (`console.py` size) и `UX-12` (`ProvisioningWizard.tsx` size) остаются открытыми как structural debt.
- `Why not in this block`: текущий блок закрывает governance drift и anti-drift enforcement, не code decomposition.
- `Risk if deferred`: slowing future iteration speed and increasing blast radius on large-file changes.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705` (to create after this block).
- `Expiry/trigger to stop deferral`: если следующий UX/API change требует >2 unrelated edits inside `console.py` or `ProvisioningWizard.tsx`.

## Next-block contract (mandatory)
- `Next block objective`: start `UVC-UX-TECH-DEBT-DECOMPOSITION-A705` with bounded decomposition plan for `console.py` and `ProvisioningWizard.tsx` under contract tests.
- `First deterministic check command`: `rg -n "\| UX-11 \||\| UX-12 \|" docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: governance checker not enforced in CI/control-loop.
- `Owner role for closure`: Brain + Top Architect.
