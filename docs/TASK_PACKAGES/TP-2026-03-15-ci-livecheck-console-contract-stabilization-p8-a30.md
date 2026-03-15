# TP-2026-03-15-ci-livecheck-console-contract-stabilization-p8-a30

- Title/Goal: Restore the post-merge `main` pipeline after deploy auth was fixed by eliminating the remaining red families: prod livecheck gate drift (`TEST_MODE=0`) and live console contract drift caused by underconstrained GET parameter schemas / missing deterministic Schemathesis seeds.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: deploy SSH auth unification P7, knowledge activation P0-P6 facts
- `TECH.md` CI / livecheck / deploy workflow references
- `SPECS/SYSTEM_REFERENCE.md` release + ops references
- CA_ID: none

## One web search (mandatory before implementation)
- Query: `Schemathesis TOML parameter generation examples override official docs`
- Date/time: `2026-03-15 22:xx Asia/Almaty`
- Sources opened:
  - Schemathesis configuration docs: `https://schemathesis.readthedocs.io/en/stable/configuration/`
  - Schemathesis configuration reference: `https://schemathesis.readthedocs.io/en/stable/reference/configuration/`
- High-signal source: official Schemathesis documentation
- Found solutions:
  - operation-specific `[[operations]]` config supports per-operation `parameters = { ... }`
  - global / operation-specific parameter overrides are the intended way to inject realistic path/query seeds without weakening checks
- Decision: `integrate`
- Reason: contract-live failures are from schema-compliant but operationally unrealistic random values; official per-operation overrides let us keep live Schemathesis enabled while forcing deterministic live-safe seeds where the spec currently underconstrains runtime expectations
- Rejected variants:
  - disabling failing endpoints in live contract lane
  - lowering Schemathesis phases/checks
  - replacing contract-live with ad-hoc curl smoke

## Root cause (mandatory)
- Symptom:
  - merged `main` run `23113240314` stays red after deploy auth fix
  - `deploy` is green on rerun, but `console-contract-live` and all `ci-livecheck` pools are red
- Minimal reproduction:
  - `gh run view 23113240314 --log-failed`
  - livecheck artifact shows `TEST_MODE_NOT_ENABLED`
  - prod `/home/zhan/truffles-main/truffles-api/.env` contains `TEST_MODE=0`
  - `console-contract-live` reproduces 400s on schema-compliant negative limits / invalid dates / literal `null` cursors in GET endpoints, plus possible case-stream 500
- Evidence:
  - GitHub Actions run `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/23113240314`
  - prod `docker exec truffles-api env | rg '^TEST_MODE='` -> `TEST_MODE=0`
  - failed Schemathesis repros in job `67135697210`
- Five Whys:
  1. Why is `main` red after merge? Because livecheck gate exits early and contract-live generates requests that runtime rejects.
  2. Why does livecheck gate exit? Because prod runtime drifted to `TEST_MODE=0` even though CI expects guarded livecheck mode.
  3. Why did runtime drift matter only now? Because deploy transport was previously failing earlier; once deploy recovered, downstream live gates ran again.
  4. Why does contract-live fail? Because several GET endpoints document overly broad string/integer/null inputs while runtime enforces tighter bounds or expects real tenant data.
  5. Why are those mismatches red in CI? Because live Schemathesis fuzzing treats those inputs as valid positive-space examples; runtime then returns undocumented 400 / 500.
- Root cause statement:
  - There are two separate drifts after the deploy fix: prod livecheck runtime env drift (`TEST_MODE=0`) and live console contract drift where OpenAPI / Schemathesis inputs are underconstrained relative to runtime validation and tenant data requirements.
- Fix mechanism:
  - Restore prod livecheck invariants by setting `TEST_MODE=1` and restarting the API.
  - Tighten live contract inputs at the spec / Schemathesis config boundary with deterministic per-operation parameter overrides and schema constraints, then fix any remaining real runtime bug (if `cases/{case_id}/stream` still 500s under valid inputs).

## Invariant
- Do not weaken deploy/livecheck/contract gates.
- Do not disable failing live endpoints as a shortcut unless runtime explicitly cannot support contract testing and the exclusion is canon-approved.
- Keep production runtime safety and knowledge release behavior unchanged except for required livecheck env restoration.

## Scope
- Prod env correction for livecheck gate (`TEST_MODE` only if needed for current contract)
- Workflow / contract config / OpenAPI fixes needed to make live contract deterministic and truthful
- Any minimal runtime fix strictly required by remaining documented live failures
- Canon/session/task docs for this block

## Out of scope
- New product features
- Reworking unrelated CI jobs
- Broad refactors of console API unrelated to failing live contract paths

## Touch-list
- `.github/workflows/ci.yml`
- `contracts/console_api/schemathesis.toml`
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/*` targeted tests only
- `docs/TASK_PACKAGES/TP-2026-03-15-ci-livecheck-console-contract-stabilization-p8-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Confirm current red family with run logs and prod runtime evidence.
2. Restore prod `TEST_MODE=1`, restart API, verify `/admin/health` gate locally on prod.
3. Reproduce live contract drift locally against prod with deterministic auth/headers.
4. Add truthful schema constraints and official Schemathesis per-operation parameter overrides for real tenant-safe seeds.
5. Fix any remaining real runtime bug exposed by valid seeded requests.
6. Run targeted contract/livecheck validations and rerun the affected workflow/jobs.
7. Record evidence in session/state docs.

## DoD
- `ci-livecheck` no longer fails on `TEST_MODE_NOT_ENABLED`.
- `console-contract-live` passes on the same merged SHA or a successor SHA without reducing phases/checks.
- Any OpenAPI/schema change is backed by deterministic tests or reproducible validation.
- Session/state docs capture the new root cause and evidence.

## Checks
- `docker exec truffles-api env | rg '^TEST_MODE='`
- `curl -s http://localhost:8000/admin/health | jq '.safety.test_mode_enabled'`
- targeted pytest for touched router/schema behavior
- `python3 scripts/generate_openapi.py --check`
- `ruff check ...` on touched Python tests/files
- targeted local/live Schemathesis run or equivalent reproducible smoke
- `gh run rerun 23113240314` or rerun affected failed jobs / new workflow run
- `SESSION_AGENT=a30 bash scripts/session_check.sh`

## Evidence
- GitHub Actions run URL(s)
- prod env/health command outputs
- targeted test commands + outputs
- session doc update
- `STATE.md` NOW update by Brain/Top Architect after validation

## Rollback
- Revert repo commit(s)
- Restore previous prod `.env` if livecheck restoration causes an unexpected regression
- Re-run canonical restart script to return to last good image/env

## No-go
- No disabling `console-contract-live` or `ci-livecheck`
- No secret rotation unless evidence proves a secret issue
- No manual DB mutations for test-data cosmetics
- No broad spec edits without matching runtime truth

## Risks/blockers
- Some contract failures may still be real runtime bugs after seeding fixes.
- GitHub Actions reruns can be noisy if concurrent main runs overlap.
- Prod env change must remain narrowly scoped to livecheck requirement.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Live contract still depends on tenant-specific seeded IDs and Keycloak-backed header resolution.
- Livecheck remains coupled to prod env flags rather than a dedicated validation environment.

### Why not in this block
- The blocker is current main redness; larger decoupling of live gates would slow recovery.

### Risk if deferred
- Future prod data/env drift can still break live lanes even when code is correct.

### Linked follow-up Task Package(s)
- TBD follow-up for tenant-safe live contract fixture strategy / dedicated livecheck env

### Expiry/trigger to stop deferral
- If live contract/livecheck red recur from tenant/env drift after this fix, the follow-up becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Convert remaining live tenant/env assumptions into explicit, versioned CI fixtures or dedicated env controls so green main does not rely on hidden prod drift.

### First deterministic check command
- `gh run view <next-main-run-id> --json jobs,conclusion,url`

### Blocked-by conditions
- Current red `main` workflow must be green first.

### Owner role for closure
- Brain / Top Architect
