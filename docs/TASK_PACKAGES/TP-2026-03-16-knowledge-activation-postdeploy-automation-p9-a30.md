# TP-2026-03-16-knowledge-activation-postdeploy-automation-p9-a30

- Title/Goal: Automate post-deploy knowledge activation proof on `main` by turning the existing manual `release_guard` + optional tenant closeout into a CI-managed artifact flow that runs on the VPS immediately after deploy and uploads evidence back to GitHub Actions.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: knowledge activation P0-P6 facts, deploy SSH auth unification P7, livecheck/contract stabilization P8
- `TECH.md` CI / deploy / livecheck workflow references
- `SPECS/SYSTEM_REFERENCE.md` release + ops references
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.github.com GitHub Actions upload artifact job summary official docs`
- **Date/time (local):** `2026-03-16 08:00 Asia/Almaty`
- **Sources opened (from this query):**
  - GitHub Docs, storing and sharing data from a workflow: `https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow`
  - GitHub Docs, workflow commands / adding a job summary: `https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary`
- High-signal source: official GitHub documentation
- Found solutions:
  - workflow artifacts are the canonical way to persist machine-readable deploy evidence from a job
  - `GITHUB_STEP_SUMMARY` is the canonical way to surface a short operator-readable verdict in the workflow UI
- Decision: `integrate`
- Reason: P9 needs machine-readable release evidence, not just log lines; official artifact upload plus job summary fit the existing CI model without inventing a second evidence transport
- Rejected options:
  - leaving guard/closeout as manual SSH-only steps in the runbook
  - printing JSON only to deploy logs without artifact upload
  - adding a separate external storage sink before CI artifacts exist

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing `scripts/restart_release.sh` activation canary hook
  - existing `truffles-api/scripts/knowledge_activation_release_guard.py`
  - existing `ops/knowledge_activation_closeout.py`
  - existing SSH bootstrap and artifact-upload patterns in `.github/workflows/ci.yml`
- External reuse:
  - official GitHub Actions artifact + job-summary primitives from the sources above
- Why not reinvent the wheel:
  - the missing piece is orchestration, not a new proof engine; reuse the existing guard/closeout contracts and wrap them in the current deploy workflow

## Execution profile (mandatory for non-doc blocks)
- TP mode: `implementation`
- Doc touch budget (files): `8`
- Code dominance: `CI workflow + release orchestration script`
- Override token: `none`
- Why this profile fits:
  - the block is a narrow post-deploy automation slice on top of already implemented P5/P6 logic, but it also has canonical release-doc fallout (`STATE/STRUCTURE/TECH/runbook/session`) that must move in the same commit as the workflow/script change

## Root cause (mandatory)
- Symptom:
  - P5/P6 release proof exists in code and runbook, but deploy on `main` still stops at parity checks; machine-readable activation proof is not automatically captured by CI
- Minimal reproduction:
  - inspect `.github/workflows/ci.yml` `deploy` job: it runs `scripts/restart_release.sh` without `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1` / `RUN_KNOWLEDGE_ACTIVATION_CANARY=1`
  - inspect `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`: guard and closeout are still manual SSH commands after deploy
  - inspect current prod DB: there is no configured consultant-verification canary tenant yet, so a hard-required tenant closeout would redline every deploy today
- Evidence:
  - `.github/workflows/ci.yml`
  - `scripts/restart_release.sh`
  - `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atc "SELECT c.name, b.slug, b.is_active FROM branches b JOIN clients c ON c.id=b.client_id WHERE b.is_active = true ORDER BY c.name, b.slug;"`
- Five Whys:
  1. Why is there no post-deploy activation proof artifact in CI? Because deploy never invokes the guard/closeout scripts.
  2. Why does deploy not invoke them? Because the deploy workflow stops after restart/parity checks.
  3. Why was that acceptable initially? Because P5/P6 first delivered the proof scripts and runbook, not CI automation.
  4. Why can't we just hard-require tenant closeout now? Because the current runtime has no explicit configured canary tenant with consultant-verification enabled.
  5. Why is that risky? Because release safety remains partly manual and future operators can miss the proof step even though the code exists.
- Root cause statement:
  - knowledge activation release proof is implemented only as manual runbook commands; the CI deploy path does not run the guard, does not capture artifacts, and does not yet have an explicit canary-tenant configuration contract for tenant closeout
- Fix mechanism:
  - add one post-deploy orchestration path that always runs release guard on the VPS, uploads machine-readable artifacts to GitHub, optionally runs tenant closeout when explicit client/branch config is present, and leaves a truthful skip artifact when closeout is not yet configured

## Invariant
- Do not weaken deploy, livecheck, or contract gates.
- Keep release proof fail-closed for `release_guard`; no silent pass on guard failure.
- Do not fake tenant closeout success when a closeout target is not configured.

## Scope
- Add a post-deploy orchestration entrypoint for activation release proof
- Wire deploy CI to run the proof on the VPS and upload artifacts
- Add a short workflow summary for operator readability
- Update canon/session/runbook docs for the new automation contract

## Out of scope
- Provisioning a new consultant-verification canary tenant in prod
- Reworking `ci-livecheck` or `console-contract-live`
- New product/UI behavior

## Touch-list
- `.github/workflows/ci.yml`
- `scripts/restart_release.sh`
- `scripts/knowledge_activation_postdeploy.sh`
- `truffles-api/tests/test_restart_release_scripts.py`
- `truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-knowledge-activation-postdeploy-automation-p9-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Add a reusable post-deploy wrapper that runs release guard and optional tenant closeout, emits a manifest, and preserves truthful skip semantics when no closeout target is configured.
2. Extend `restart_release.sh` call sites / CI deploy flow so activation service restart + guard artifact run as part of post-deploy proof.
3. Update `.github/workflows/ci.yml` to fetch the proof artifacts back from the VPS, upload them, and expose a short step summary.
4. Add targeted regression tests for the new wrapper and any `restart_release.sh` contract changes.
5. Update runbook + session/canon docs with the new automation path and the residual gap around tenant-target configuration.

## DoD
- `main`/manual deploy path automatically runs knowledge activation release guard after deploy and uploads JSON artifacts to GitHub Actions.
- If a closeout target is explicitly configured, tenant closeout also runs automatically and its verdict is uploaded.
- If no closeout target is configured, the artifact truthfully records `skipped` instead of pretending success.
- Guard failure still fails the release-proof path; no silent downgrade.
- Targeted tests and session gates are green.

## Checks
- `pytest -q truffles-api/tests/test_restart_release_scripts.py truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `ruff check truffles-api/tests/test_restart_release_scripts.py truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `bash -n scripts/restart_release.sh scripts/knowledge_activation_postdeploy.sh`
- `SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - if deploy always runs the existing guard and uploads the resulting artifacts, release proof stops being a manual runbook-only step while preserving truthful closeout skip behavior until a target tenant is configured
- Expected measurable effect:
  - targeted script tests pass locally, workflow syntax stays valid, and the next deploy-capable CI run exposes uploaded knowledge activation proof artifacts
- Max full runs: `1`
- Max targeted reruns per failure family: `2`
- Stop condition:
  - stop after local script/workflow/session checks are green and one CI run confirms artifact upload behavior

## Evidence
- GitHub Actions run URL(s) with uploaded proof artifacts
- targeted test commands + outputs
- workflow syntax output
- session doc update
- `STATE.md` NOW update by Brain / Top Architect after validation

## Rollback
- Revert the CI + script commit(s)
- Remove the new post-deploy wrapper from the deploy flow
- Fall back to the manual runbook commands in `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`

## Release safety (mandatory for non-doc changes)
- Strategy:
  - keep deploy behavior unchanged up to parity checks, then append automated proof capture using the already-defined guard/closeout contracts
- Go/no-go signals:
  - release guard artifact `decision=go`
  - if closeout target configured: closeout artifact `decision=go`
  - if closeout target missing: manifest records `closeout_status=skipped`
- Rollback:
  - revert the CI/script change if deploy starts failing before or during proof capture for reasons unrelated to the actual release
- Post-release monitoring window:
  - watch the first `main` deploy run through deploy, proof artifact upload, `console-contract-live`, and `ci-livecheck`

## No-go
- No weakening of `release_guard` thresholds
- No hardcoding fake closeout `go`
- No dependency on stale `/home/zhan/truffles-main` source code for new proof logic; use the deployed temp clone or checked-out workflow code
- No manual DB mutations to manufacture a canary tenant

## Risks/blockers
- There is currently no configured consultant-verification canary tenant in prod, so full P6 tenant closeout cannot be hard-required yet.
- Remote artifact download can be flaky if the runner loses SSH connectivity mid-transfer.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Tenant closeout remains conditional on explicit `client_slug/branch_slug` configuration because prod does not yet expose a ready consultant-verification canary target.
- Deploy/livecheck still duplicate SSH bootstrap logic in the workflow.

### Why not in this block
- The immediate value is to remove the manual proof gap without turning `main` red on missing canary configuration; SSH dedup and tenant-fixture provisioning are follow-up blocks.

### Risk if deferred
- Without a configured closeout target, CI proves only release guard automatically and still needs one explicit tenant configuration step before full P6 can become hard-required.

### Linked follow-up Task Package(s)
- Follow-up block to provision an explicit knowledge-activation canary tenant or dedicated closeout fixture env and then switch tenant closeout from optional to required.
- Follow-up block to deduplicate SSH bootstrap across deploy/livecheck/proof jobs in `.github/workflows/ci.yml`.

### Expiry/trigger to stop deferral
- If another release requires tenant-level proof or operators start relying on manual tenant closeout again, the canary-target follow-up becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Make tenant closeout hard-required by introducing explicit versioned canary tenant/env configuration instead of skip semantics.

### First deterministic check command
- `gh run list --workflow CI --branch main --limit 1 --json databaseId,conclusion,url`

### Blocked-by conditions
- P9 artifact automation must be merged and one deploy-capable run must complete successfully first.

### Owner role for closure
- Brain / Top Architect
