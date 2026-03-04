# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave5-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE5-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW-A705`

## Название/цель
Выполнить следующий полноценный bounded decomposition шаг по `UX-11/UX-12` для дальнейшего снижения blast-radius `console.py` и `ProvisioningWizard.tsx` без изменения runtime-семантики.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-close-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## One web search (mandatory before implementation)
- **Status:** pending for execution in wave5 start.
- **Requirement:** run exactly one query and record source/reuse decision before code changes.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave4 final-close.
- **Root cause statement:** residual multi-concern concentration remains in router/component monoliths.
- **Fix mechanism:** one more bounded backend + frontend slice extraction with deterministic contract checks.

## Invariant
- No runtime behavior changes.
- No new top-level tabs/routes.
- Platform-admin contract lane remains green.

## Scope
- Backend wave5 extraction from `console.py` into dedicated service module.
- Frontend wave5 extraction from `ProvisioningWizard.tsx` into dedicated component/hook module.
- Deterministic tests for newly extracted slices.

## Out of scope
- Big-bang rewrite of router/wizard.
- Any policy-core or booking pipeline changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/*`
- `truffles-api/tests/*`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/*`
- `console-web/e2e/platform-admin.spec.ts` (only if selector contract requires update)

## Plan (1..N)
1. FACT pre-check + mandatory one-web-search.
2. Backend bounded extraction + deterministic tests.
3. Frontend bounded extraction + deterministic lint/build checks.
4. Revalidate targeted platform-admin contract lane.
5. Canon sync + evidence artifact.

## DoD
- Additional measurable LOC reduction in both monoliths.
- New extracted modules covered by deterministic tests.
- Targeted contract checks green.
- Residual status re-evaluated with closure criteria.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile ...`
- `pytest -q ...`
- `cd console-web && npm run lint -- --file ...`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff of extracted modules and rewiring.
- Deterministic checks output.
- Updated canon status for `UX-11/UX-12`.

## Rollback
- `git revert COMMIT_SHA` and rerun deterministic checks.

## No-go
- Runtime behavior changes masked as refactor.
- Disconnected UX controls or duplicated execute actions.
- Skipping mandatory gates (`research/root-cause/reuse/release/context`).

## Risks/блокеры
- Hidden coupling can expand extraction scope.
- E2E flake can mask regression if not triaged deterministically.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: expected residual until closure review.
- `Why not in this block`: bounded extraction strategy to keep risk controlled.
- `Risk if deferred`: high blast-radius persists.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705.md`.
- `Expiry/trigger to stop deferral`: if post-wave5 reduction is below expected threshold, escalate to architecture decision.

## Next-block contract (mandatory)
- `Next block objective`: run closure review with objective threshold decision (`Fixed` vs `Open`).
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave5 checks red or evidence incomplete.
- `Owner role for closure`: Brain + Top Architect.
