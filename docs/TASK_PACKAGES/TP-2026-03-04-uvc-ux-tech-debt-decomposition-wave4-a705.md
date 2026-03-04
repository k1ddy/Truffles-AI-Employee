# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave4-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE4-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of closeout PR for `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSEOUT-A705`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705

## Название/цель
Выполнить следующий полноценный этап decomposition после closeout: дополнительно снизить blast-radius `console.py` и `ProvisioningWizard.tsx` через feature-slice extraction без изменения runtime-семантики.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closeout-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Invariant
- No runtime behavior changes.
- No new top-level tabs/routes.
- Existing platform-admin contract tests stay green.

## Scope
- Backend: extract next bounded control-tower/onboarding feature-slice from `console.py` into dedicated module(s).
- Frontend: extract next bounded `ProvisioningWizard` view/action slice into dedicated component/hook module(s).
- Add deterministic tests for newly extracted units.

## Out of scope
- Full router rewrite.
- Full provisioning wizard rewrite.
- Any policy-core/booking semantic changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/*` (new extracted modules)
- `truffles-api/tests/*` (targeted deterministic tests)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/*` (new extracted modules)
- `console-web/e2e/platform-admin.spec.ts` (only if selector contract needs update)

## Plan (1..N)
1. FACT pre-check and one mandatory web-search for wave4 extraction strategy.
2. Backend wave4 extraction + deterministic tests.
3. Frontend wave4 extraction + deterministic tests/lint.
4. Re-run targeted platform-admin lane.
5. Canon sync and PR.

## DoD
- `console.py` and `ProvisioningWizard.tsx` are further reduced by bounded extraction.
- New extraction modules are covered by deterministic tests.
- Targeted e2e lane remains green.
- Canon docs synced with updated residual/final-close contract.

## Checks
- `python3 -m py_compile ...`
- `pytest -q ...`
- `cd console-web && npm run lint -- --file ...`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff of extracted modules and rewiring.
- Test/lint/e2e outputs.
- Updated closeout progression in `STATE/master/backlog`.

## Rollback
- `git revert COMMIT_SHA` and rerun deterministic checks.

## No-go
- Big-bang rewrites.
- New runtime fallback branches.
- Contract changes hidden as refactor.

## Risks/блокеры
- Hidden coupling in monolith files can expand extraction scope.
- E2E flakes can mask true regressions if not triaged deterministically.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: residual remains until final-close criteria are met.
- `Why not in this block`: wave4 is bounded; final closure may require one more bounded block.
- `Risk if deferred`: medium.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705`.
- `Expiry/trigger to stop deferral`: if two consecutive blocks do not reduce blast-radius metrics.

## Next-block contract (mandatory)
- `Next block objective`: final-close decision for `UX-11/UX-12` with closure criteria.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave4 checks red or PR not merged.
- `Owner role for closure`: Brain + Top Architect.
