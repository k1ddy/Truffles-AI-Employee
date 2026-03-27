# TP-2026-03-16-consultant-verification-owner-access-closure-p12-a30

- Title/Goal: Close the remaining user-facing gap in `Business -> Проверка консультанта` by removing the hidden rollout gate from the owner preview/workspace path while keeping publish/compare governance as a separate contract.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: knowledge release model P0-P11 facts + consultant verification owner gap
- `SPECS/CONSULTANT.md`
- `TECH.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:launchdarkly.com docs feature flags release flags kill switch permissions best practices`
- **Date/time (local):** `2026-03-16 15:05 Asia/Almaty`
- Sources opened (from this query):
  - LaunchDarkly Docs, Creating flags: `https://launchdarkly.com/docs/guides/flags/creating-flags`
  - LaunchDarkly Docs, Flag conventions: `https://launchdarkly.com/docs/guides/flags/flag-conventions`
- High-signal source: official LaunchDarkly documentation
- Found solutions:
  - release flags and operational/kill-switch flags are different flag classes with different lifetimes and responsibilities
  - flag hygiene requires explicit separation of temporary release toggles from longer-lived operational controls
- Decision: `integrate`
- Reason: the current bug comes from one rollout flag doing two jobs at once: gating the owner-facing preview product and gating compare/publish governance. The fix should split those responsibilities instead of deleting all gates blindly.
- Rejected options:
  - keeping the hidden pilot flag as the owner workspace gate
  - deleting all consultant-verification gates in one step and accidentally making compare-before-publish mandatory for every branch
  - solving the symptom with UI copy only

## Reuse-first plan (mandatory)
- Internal reuse:
  - `truffles-api/app/services/console_consultant_verification.py`
  - existing session APIs / compare readiness APIs / overview response
  - `console-web/src/app/business/consultant-verification/*`
  - existing targeted backend tests + owner Playwright lane
- External reuse:
  - LaunchDarkly docs above for release-vs-operational flag separation
- Why not reinvent the wheel:
  - the preview/live architecture is already fixed; the remaining defect is gate semantics and frontend query wiring, not missing infrastructure

## Execution profile (mandatory for non-doc blocks)
- TP mode: `implementation`
- Doc touch budget (files): `10`
- Code dominance: `backend contract split + owner workspace closure`
- Override token: `none`
- Why this profile fits:
  - this block is backend/frontend contract work with targeted docs/session updates, not a new subsystem

## Root cause (mandatory)
- Symptom:
  - owner still cannot actually use `Проверка консультанта`, even though preview/live release-model work is already green underneath
- Minimal reproduction:
  - `python3 ops/knowledge_activation_closeout.py --client-slug demo_salon --branch-slug main --guard-json <(printf '{"decision":"go"}\n') --pretty` returns `preview_available=true`, `release_preview_ready=true`, `owner_surface_enabled=false`, `can_verify_now=false`
  - open `truffles-api/app/services/console_consultant_verification.py`: `_require_verification_rollout()` still blocks session/message/findings/compare endpoints on `resolve_consultant_verification_enabled(context)`
  - open `console-web/src/app/business/consultant-verification/page.tsx`: `workspaceReady` still depends on `data.feature_enabled`
- Evidence:
  - `ops/knowledge_activation_closeout.py`
  - `truffles-api/app/services/console_consultant_verification.py`
  - `truffles-api/app/routers/console.py`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts`
- Five Whys:
  1. Why can the owner not use the tab? Because the page still hides the workspace when `feature_enabled=false`.
  2. Why is `feature_enabled` false? Because it is still derived from the old consultant-verification pilot flag.
  3. Why does that still block the user after P0/P1? Because the old flag still guards interactive session/message endpoints and overview status, even though preview readiness no longer depends on activation.
  4. Why is the old flag still there? Because the same resolver is also used for compare/publish governance, so we preserved it during release-model correction.
  5. Why is that wrong now? Because one flag is carrying two unrelated meanings: owner product access and compare/publish governance.
- Root cause statement:
  - consultant verification still overloads one rollout flag for two different responsibilities, so the owner preview/workspace path remains blocked even when preview-ready invariants are healthy and only advanced compare/governance tools are supposed to stay gated
- Fix mechanism:
  - split the current flag semantics into owner preview/workspace access vs team-tools/compare governance, unblock the owner preview/session path, and keep compare/publish gating on its own explicit boolean

## Invariant
- Do not reintroduce `sync/live activation` as a blocker for preview verification.
- Do not silently make compare-before-publish globally mandatory for all branches.
- Keep verification sessions pinned to immutable truth snapshots.

## Scope
- Split consultant verification gate semantics in backend overview/runtime
- Unblock owner preview/session/message path when preview is ready
- Keep compare/findings/publish governance behind a separate gate if still configured
- Update frontend workspace readiness/query wiring so the tab is usable without team-tools rollout
- Add targeted backend/frontend regression tests and sync canon/session docs

## Out of scope
- New activation/deploy/CI work
- New product features beyond owner access closure
- Manual client-config DB edits to enable rollout
- Full removal of compare governance policy if product still wants it separate

## Touch-list
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationReviewLane.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationTeamToolsPanel.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-verification-owner-access-closure-p12-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Capture the current false blocker and split backend gate semantics into workspace access vs compare/team-tools governance.
2. Update overview/status/actions/readiness to expose separate booleans for owner workspace and advanced team tools.
3. Unblock session/message endpoints for owner preview while keeping compare/finding/publish governance on the separate gate.
4. Update frontend workspace gating and conditional queries/panels so the page works when preview is ready even if team tools stay off.
5. Add targeted backend + Playwright regressions, regenerate contract/types, and sync canon/session docs.

## DoD
- Owner can open `Проверка консультанта`, create a session, and send preview messages whenever preview is ready, even if the old rollout flag is disabled.
- Overview/API expose separate semantics for owner workspace access vs compare/team-tools governance.
- Publish compare requirement still uses the governance gate, not the owner workspace gate.
- Team-tools queries/panels no longer break the page when advanced tools are disabled.
- Targeted backend/frontend checks are green and canon/session docs reflect the closure.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py -k 'consultant_verification or knowledge_publish'`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/services/console_consultant_verification.py app/routers/console.py app/schemas/console.py tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationReviewLane.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationTeamToolsPanel.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'consultant verification owner access|consultant verification readiness'`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - if we split the rollout gate correctly, owner preview access will become usable without making compare/publish governance universally required
- Expected measurable effect:
  - overview returns `can_verify_now=true` on preview-ready branches even when the old pilot flag is false, session/message endpoints succeed, and publish compare remains optional unless the separate governance gate is enabled
- Max full runs: `1`
- Max targeted reruns per failure family: `2`
- Stop condition:
  - stop after targeted backend/frontend proof is green and one PR CI run confirms no new contract drift

## Evidence
- closeout / overview before-vs-after truth on `demo_salon/main`
- targeted pytest/ruff/openapi/generate/lint/build/playwright outputs
- updated session/canon docs
- `STATE.md` NOW update by Brain / Top Architect after validation

## Rollback
- Revert the owner-access closure commit(s)
- Restore old preview/workspace gating if the split unexpectedly weakens compare governance

## Release safety (mandatory for non-doc changes)
- Strategy:
  - narrow contract fix on an existing owner route; no new rollout lane or DB mutations
- Go/no-go signals:
  - owner preview workspace opens on preview-ready overview
  - session/message endpoints succeed with rollout flag off
  - compare/publish gate still behaves according to the separate governance flag
- Rollback:
  - revert the split if publish compare or findings governance leaks unintentionally
- Post-release monitoring window:
  - watch the PR CI run and the first merged owner-path smoke / user canary on `Проверка консультанта`

## No-go
- No UI-only copy fix that leaves the backend gate in place
- No manual tenant-config edits as acceptance proof
- No change that re-couples preview access to activation status
- No blanket removal of compare/publish governance without an explicit product decision

## Risks/blockers
- Existing frontend review lane assumes findings/compare are always mounted, so query wiring must be split carefully to avoid regressions.
- API contract changes require type regeneration and E2E fixture updates in the same block.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Compare/finding/team-tools still remain a second-stage surface inside the same route instead of a separately permissioned workspace.
- The deploy path-filter omission for `scripts/restart_knowledge_activation_service.sh` is still unresolved infra debt outside this product block.

### Why not in this block
- The immediate business gap is owner access closure for consultant verification. Infra path-filter cleanup and broader team-tools productization are separate blocks.

### Risk if deferred
- Advanced tools remain partially coupled to the owner workspace structure, and deploy-impacting script changes may still skip deploy proof until the workflow filter is fixed.

### Linked follow-up Task Package(s)
- Follow-up block for deploy/livecheck path-filter hardening.
- Follow-up block for making compare/findings/team tools a fully explicit product/permission contract.

### Expiry/trigger to stop deferral
- If a merged change to activation-service restart script skips deploy proof again, CI path-filter hardening becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Harden CI path filters so deploy-impacting knowledge-activation script changes always trigger deploy/livecheck proof.

### First deterministic check command
- `rg -n "restart_knowledge_activation_service\.sh|deploy_required|livecheck_required" .github/workflows/ci.yml`

### Blocked-by conditions
- Owner access closure must merge and one user-facing canary must confirm the tab is usable.

### Owner role for closure
- Brain / Top Architect
