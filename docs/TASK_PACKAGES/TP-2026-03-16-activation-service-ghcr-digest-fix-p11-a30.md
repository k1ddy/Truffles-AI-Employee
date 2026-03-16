# TP-2026-03-16-activation-service-ghcr-digest-fix-p11-a30

- Title/Goal: Fix the post-merge deploy failure by making `restart_knowledge_activation_service.sh` accept the same GHCR digest refs that `restart_release.sh` already resolves and passes during main deploy.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: knowledge activation P0-P10 facts
- `TECH.md` deploy / release references
- `SPECS/SYSTEM_REFERENCE.md` release restart references
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.docker.com docker image pull NAME[:TAG|@DIGEST] official docs`
- **Date/time (local):** `2026-03-16 09:05 Asia/Almaty`
- Sources opened (from this query):
  - Docker Docs, `docker image pull`: `https://docs.docker.com/reference/cli/docker/image/pull/`
  - Docker Docs, `docker image ls`: `https://docs.docker.com/reference/cli/docker/image/ls/`
- High-signal source: official Docker documentation
- Found solutions:
  - Docker accepts image refs in `NAME[:TAG|@DIGEST]` form
  - digest refs are valid for `pull`, `run`, and related image operations
- Decision: `integrate`
- Reason: the deploy failure is a false validation reject in our shell gate, not a Docker limitation
- Rejected options:
  - downgrading deploy back to mutable tag-only refs
  - disabling `REQUIRE_GHCR`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `scripts/restart_api.sh` already has digest-aware `is_ghcr_image_ref`
  - `scripts/restart_release.sh` already resolves/passes digest refs
  - `truffles-api/tests/test_restart_release_scripts.py`
- External reuse:
  - Docker official image-ref syntax from the sources above
- Why not reinvent the wheel:
  - the release stack already supports digest refs everywhere except this one script gate

## Root cause (mandatory)
- Symptom:
  - merged `main` run `23127522792` failed in `deploy` / `Deploy to VPS`
- Minimal reproduction:
  - `restart_release.sh` resolves `ghcr.io/k1ddy/truffles-ai-employee@sha256:...`
  - deploy passes that digest ref into `restart_knowledge_activation_service.sh`
  - the script rejects it with `ERROR: REQUIRE_GHCR=1 but IMAGE_NAME='...@sha256:...' is not a GHCR image.`
- Evidence:
  - `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/23127522792`
  - `scripts/restart_release.sh`
  - `scripts/restart_knowledge_activation_service.sh`
- Five Whys:
  1. Why did deploy fail? The activation-service restart script exited non-zero.
  2. Why did that script exit? Its GHCR allowlist rejected the image ref.
  3. Why was the ref rejected? The shell case only allowed `ghcr.io/...:*`, not `ghcr.io/...@sha256:*`.
  4. Why did deploy pass a digest ref? `restart_release.sh` intentionally resolves mutable tags to immutable digests for parity safety.
  5. Why is this a defect? The release flow is internally inconsistent: parent scripts are digest-aware, but the child activation-service gate is tag-only.
- Root cause statement:
  - `restart_knowledge_activation_service.sh` has a stale GHCR validation gate that only accepts tag refs, so main deploy fails when the release path correctly promotes the image to an immutable digest ref
- Fix mechanism:
  - make `restart_knowledge_activation_service.sh` use the same digest-aware GHCR ref validation as the rest of the release stack and add a regression test for digest refs

## Invariant
- Keep `REQUIRE_GHCR=1` enforced.
- Keep digest-based deploy parity unchanged.
- Do not weaken image verification or health verification.

## Scope
- Fix GHCR digest validation in `restart_knowledge_activation_service.sh`
- Add deterministic regression coverage
- Sync session/canon docs for the merge-failure RCA

## Out of scope
- Broader restart-script unification across unrelated services
- Deploy workflow redesign
- Product/runtime behavior changes

## Touch-list
- `scripts/restart_knowledge_activation_service.sh`
- `truffles-api/tests/test_restart_release_scripts.py`
- `docs/TASK_PACKAGES/TP-2026-03-16-activation-service-ghcr-digest-fix-p11-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Patch the activation-service GHCR gate to accept digest refs.
2. Add a targeted regression test for digest refs.
3. Update session/canon evidence with the merge-failure RCA and fix.
4. Push to the same branch and verify the PR rerun.

## DoD
- `restart_knowledge_activation_service.sh` accepts `ghcr.io/k1ddy/truffles-ai-employee@sha256:...` when `REQUIRE_GHCR=1`
- Targeted regression tests are green
- Session/canon docs reflect the merge-failure fix

## Checks
- `pytest -q truffles-api/tests/test_restart_release_scripts.py`
- `ruff check truffles-api/tests/test_restart_release_scripts.py`
- `bash -n scripts/restart_knowledge_activation_service.sh`
- `SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - if the activation-service script accepts GHCR digest refs, the existing main deploy flow will stop failing on the false `REQUIRE_GHCR` reject
- Expected measurable effect:
  - targeted restart-script regression stays green and the next CI rerun clears `deploy`
- Max full runs: `1`
- Max targeted reruns per failure family: `2`
- Stop condition:
  - stop after targeted local proof is green and one CI rerun confirms the deploy job passes

## Evidence
- failed run URL + failing step output
- targeted test output
- updated session/state references

## Rollback
- Revert the digest-gate fix commit

## Release safety (mandatory for non-doc changes)
- Strategy:
  - patch only the failing digest gate and keep the existing deploy path
- Go/no-go signals:
  - targeted test green
  - rerun of the branch PR clears `deploy`
- Rollback:
  - revert the fix if activation-service restart breaks on non-digest refs
- Post-release monitoring window:
  - watch the rerun of this PR and the next `main` deploy for the `deploy` job, especially `Deploy to VPS`

## No-go
- No disabling `REQUIRE_GHCR`
- No switch back to mutable tag-only deploy
- No manual server edits as “evidence”

## Risks/blockers
- Other restart helper scripts still have tag-only GHCR gates; this block fixes only the active failure family.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Other service restart scripts still duplicate GHCR validation instead of sharing one helper.

### Why not in this block
- The immediate blocker is one merge-failing script; wider refactor is not needed to restore deploy.

### Risk if deferred
- Another service-specific restart path could hit the same false reject later.

### Linked follow-up Task Package(s)
- Follow-up block for shared restart-script GHCR validation helper.

### Expiry/trigger to stop deferral
- If any other service restart path fails on digest refs, shared helper extraction becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Unify GHCR image-ref validation across service restart scripts to remove duplicate tag-only gates.

### First deterministic check command
- `rg -n "REQUIRE_GHCR|ghcr.io/k1ddy/truffles-ai-employee:\\*" scripts/restart_*.sh`

### Blocked-by conditions
- This deploy-fix PR must merge and the next `main` deploy run must complete.

### Owner role for closure
- Brain / Top Architect
