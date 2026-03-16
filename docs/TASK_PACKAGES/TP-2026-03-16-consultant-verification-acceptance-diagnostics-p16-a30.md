# TP-2026-03-16-consultant-verification-acceptance-diagnostics-p16-a30

- Title/Goal: Close the remaining in-scope consultant-verification acceptance gap by making workspace availability deterministic for tenant diagnostics: add stable blocker codes, clean up internal workspace-vs-team-tools naming, and preserve the legacy `feature_enabled` API field only as a compatibility alias.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: preview/live release-model correction is merged, owner workspace gate is separated from team tools, but tenant acceptance is still ambiguous because the consultant-verification overview exposes free-form blockers plus legacy `feature_enabled` naming.
- `docs/CONSOLE_GUIDE.md`
- `truffles-api/app/services/console_consultant_verification.py`
- `console-web/src/app/business/consultant-verification/page.tsx`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic alias field serialization official docs`
- **Date/time (local):** `2026-03-16 13:23 Asia/Almaty`
- Sources opened (from this query):
  - Pydantic docs, alias concepts: `https://docs.pydantic.dev/latest/concepts/alias/`
- High-signal source: official Pydantic docs
- Found solutions:
  - keep legacy wire compatibility by exposing a stable serialized field while using clearer internal names
  - use explicit schema fields/aliases instead of ad-hoc response reshaping
- Decision: `integrate`
- Reason: this block keeps `feature_enabled` as a backward-compatible field while clarifying the actual semantic owner `workspace_enabled` in code/contracts.
- Rejected options:
  - removing `feature_enabled` immediately and breaking existing clients/tests
  - leaving ambiguous free-form blockers as the only diagnostic surface

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing consultant-verification overview builder in `truffles-api/app/services/console_consultant_verification.py`
  - existing public response model `ConsoleConsultantVerificationOverviewResponse`
  - existing frontend gating in `console-web/src/app/business/consultant-verification/page.tsx`
- External reuse:
  - Pydantic alias guidance from the official docs above for compatibility-safe schema evolution
- Why not reinvent the wheel:
  - the runtime semantics are already correct; this block only hardens the contract so tenant diagnosis is deterministic without breaking existing clients.

## Root cause (mandatory)
- Symptom:
  - the core architecture is fixed, but tenant-level acceptance for `Проверка консультанта` is still too manual: the overview contract mixes old `feature_enabled` naming with new workspace semantics and exposes only free-form `blockers[]`, which makes it harder to determine deterministically why the tab is unavailable for a concrete tenant.
- Minimal reproduction:
  - inspect `truffles-api/app/services/console_consultant_verification.py` overview builder and `console-web/src/app/business/consultant-verification/page.tsx`
  - the page derives readiness from `workspace_enabled ?? feature_enabled`, `branch_selection_required`, `can_verify_now`, and `blockers[]`, but the API does not return stable blocker codes.
- Evidence:
  - `truffles-api/app/services/console_consultant_verification.py:591-625`
  - `truffles-api/app/services/console_consultant_verification.py:1197-1268`
  - `console-web/src/app/business/consultant-verification/page.tsx:132-134`
  - `console-web/src/app/business/consultant-verification/page.tsx:346-362`
- Five Whys:
  1. Why is tenant acceptance still ambiguous? Because workspace availability is represented through a mixture of booleans and natural-language blocker strings.
  2. Why does that matter now? Because the original architectural blocker is closed, so the remaining failures are likely tenant/config/branch/source issues that need deterministic diagnosis.
  3. Why is the contract still confusing? Because `feature_enabled` now semantically means `workspace_enabled`, while `team_tools_enabled` is separate.
  4. Why is that risky? Because future operators and UI code can accidentally re-mix workspace access with team tools or rely on brittle string matching in blockers.
  5. Why must this be fixed in the contract? Because the remaining closure step is tenant acceptance, not another backend architecture change.
- Root cause statement:
  - the remaining gap is contract ambiguity: consultant-verification availability is now semantically correct, but the API/UI contract still exposes the old gate naming and lacks stable blocker codes for tenant-specific diagnosis.
- Fix mechanism:
  - introduce structured blocker codes, rename internal overview variables to `workspace_enabled`, preserve `feature_enabled` only as a compatibility alias, and update frontend/tests/docs to use the structured contract.

## Invariant
- Do not reintroduce sync/live activation as gates for preview workspace.
- Do not merge workspace access and team tools back into one flag.
- Do not expose operational internals to owner primary copy beyond the existing product-safe blockers.

## Scope
- Consultant-verification overview schema/service/frontend contract only.
- Deterministic tests for blocker codes and workspace/team-tools separation.
- Session/state docs for this closure block.

## Out of scope
- `livecheck-auto` / CA03-CA06 families
- webhook semantic-runtime fixes in `decision.py` / `trace.py`
- new activation architecture work
- new compare/findings functionality

## Touch-list
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Add structured consultant-verification blocker codes and compatibility-safe schema fields.
2. Rename internal overview/service variables from `feature_enabled` to `workspace_enabled` while keeping the legacy response field.
3. Update frontend gating/tests to consume structured diagnostics without changing owner-safe copy.
4. Run targeted backend/frontend checks and record closure/residual debt in canon.

## DoD
- Overview response returns stable blocker codes for workspace gating.
- Internal backend/frontend logic no longer depends on ambiguous `feature_enabled` semantics.
- Legacy `feature_enabled` response field remains serialized for compatibility.
- Owner-safe UI still shows the same product copy, while deterministic tests can assert the precise blocker reason.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && pytest -q truffles-api/tests/test_console_consultant_verification_api.py truffles-api/tests/test_console_owner_business.py -k 'consultant_verification'`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && python3 truffles-api/scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && npm --prefix console-web run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && npm --prefix console-web run lint -- --file src/app/business/consultant-verification/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - stable blocker codes plus clearer workspace naming will improve tenant acceptance diagnosis without changing owner behavior.
- Expected measurable effect:
  - backend overview tests stay green, frontend mocked owner-access tests stay green, and no compatibility regressions appear in generated API/types.
- Max full runs: `1 targeted pytest batch + 1 generate:api + 1 frontend lint + 1 targeted Playwright batch`
- Max targeted reruns per failure family: `1`
- Stop condition:
  - stop once the consultant-verification contract checks are green, or isolate any remaining failure into a narrower follow-up block.

## Evidence
- updated consultant-verification contract files
- targeted pytest output
- OpenAPI/types regeneration evidence
- frontend lint evidence
- updated session/state docs

## Rollback
- Revert the narrow consultant-verification contract commit(s); no data rollback required.

## Release safety (mandatory for non-doc changes)
- Strategy:
  - compatibility-safe contract hardening only; preserve legacy response field while shifting internal logic/tests to the new structured contract.
- Go/no-go signals:
  - targeted consultant-verification backend tests green
  - OpenAPI/types regeneration clean
  - frontend lint clean
- Rollback:
  - revert the contract-hardening commit if owner workspace rendering regresses
- Post-release monitoring window:
  - first owner-session create/read flow after deploy on the target tenant

## No-go
- No new livecheck/CI family work in this block
- No removal of `feature_enabled` from the public response yet
- No new owner-facing ops jargon

## Risks/blockers
- Existing local P15 runtime-semantic edits remain out-of-scope and must not be merged as part of this block.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `feature_enabled` remains in the public response as a compatibility alias.
- Team tools stay on a separate gate; this block does not change findings/compare policy.

### Why not in this block
- Removing the alias is a later API cleanup.
- Team-tools policy is a product decision, not a tenant-acceptance blocker.

### Risk if deferred
- Future code can still misread `feature_enabled` if the alias remains too long.

### Linked follow-up Task Package(s)
- follow-up API cleanup block to deprecate/remove `feature_enabled`
- separate policy block if the product decides to open team tools fully

### Expiry/trigger to stop deferral
- if another implementation branch reuses `feature_enabled` as a semantic gate, the alias cleanup becomes immediate.

## Next-block contract (mandatory)
### Next block objective
- After this contract hardening, run tenant-specific owner acceptance using the overview payload and session create flow only.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && pytest -q truffles-api/tests/test_console_consultant_verification_api.py truffles-api/tests/test_console_owner_business.py -k 'consultant_verification'`

### Blocked-by conditions
- none; this is the direct remaining closure block for consultant-verification acceptance.

### Owner role for closure
- Brain / Top Architect
