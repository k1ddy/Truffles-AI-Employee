# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave6-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE6-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW2-A705`

## Название/цель
Выполнить следующий полный атомарный wave6 блок для `UX-11/UX-12`: ещё один bounded backend/frontend extraction с contract-first проверками и без runtime semantic drift.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## One web search (mandatory before implementation)
- **Status:** pending for wave6 start.
- **Requirement:** perform exactly one query and record source/reuse decision before code changes.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave5 closure-review.
- **Root cause statement:** monolith residual still above closure threshold.
- **Fix mechanism:** one more bounded extraction with deterministic contract checks.

## Invariant
- No runtime behavior changes.
- No new top-level tabs/routes.
- Platform-admin contract tests remain green.

## Scope
- Backend wave6 extraction from `console.py` into service module.
- Frontend wave6 extraction from `ProvisioningWizard.tsx` into dedicated component/hook module.
- Deterministic tests/checks and canon evidence sync.

## Out of scope
- Big-bang router/component rewrite.
- Any policy-core or booking semantic change.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/*`
- `truffles-api/tests/*`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/*`
- `docs/CONSOLE_AUDIT/artifacts/*wave6*`
- `STATE.md`, `STRUCTURE.md`, session docs

## Plan (1..N)
1. FACT pre-check + one mandatory web-search.
2. Backend bounded extraction + deterministic tests.
3. Frontend bounded extraction + deterministic lint/build checks.
4. Revalidate targeted acceptance lane.
5. Canon sync and PR.

## DoD
- measurable LOC reduction in both monoliths.
- new extraction modules covered by deterministic tests.
- targeted acceptance checks green.
- closure-review2 contract prepared.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile ...`
- `pytest -q ...`
- `cd console-web && npm run lint -- --file ...`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- diff for extracted modules and rewiring.
- deterministic check outputs.
- updated canon status for `UX-11/UX-12`.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` (`build + one targeted e2e lane`).
- Stop condition: two consecutive failures without new RCA evidence.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded behavior-preserving extraction.
- **Go/no-go signals:** py_compile/pytest/lint/build/e2e/session-gate all green.
- **Rollback:** `git revert COMMIT_SHA` + rerun checks.
- **Post-release monitoring window:** required PR CI lanes green before merge.

## Rollback
- `git revert COMMIT_SHA` and rerun deterministic checks.

## No-go
- hidden runtime behavior changes.
- disconnected/duplicated actions across tabs.
- skipping mandatory gates.

## Risks/блокеры
- hidden coupling may expand scope.
- e2e flakes may hide real regressions if not triaged.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: expected residual until closure-review2.
- `Why not in this block`: bounded extraction strategy to keep risk controlled.
- `Risk if deferred`: continued high blast-radius.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review2-a705.md`.
- `Expiry/trigger to stop deferral`: if wave6 fails to reduce both monoliths, escalate to architecture decision.

## Next-block contract (mandatory)
- `Next block objective`: closure-review2 decision (`Fixed` vs `Open`) after wave6 evidence.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave6 checks red or evidence incomplete.
- `Owner role for closure`: Brain + Top Architect.
