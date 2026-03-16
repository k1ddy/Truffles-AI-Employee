# TP-2026-03-16-ci-path-filter-hardening-p13-a30

- Title/Goal: Close the remaining CI governance gap where knowledge-activation deploy-path changes can merge without a real deploy/livecheck proof because `.github/workflows/ci.yml` path filters omit activation-specific scripts used by the main rollout path.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: knowledge release model P0-P12 facts + residual CI path-filter gap for activation deploy proof
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.github.com GitHub Actions workflow path filters paths official docs`
- **Date/time (local):** `2026-03-16 11:06 Asia/Almaty`
- Sources opened (from this query):
  - GitHub Docs, Workflow syntax for GitHub Actions — `paths` / `paths-ignore`: `https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore`
- High-signal source: official GitHub Docs
- Found solutions:
  - workflow path filters are purely file-pattern gates, so every deploy-critical file must be listed explicitly or covered by an included glob
  - skipped jobs are expected behavior when a changed file does not match the configured filter set
- Decision: `integrate`
- Reason: the current defect is not in deploy logic itself; it is in the file-pattern gate that decides whether deploy/livecheck jobs run at all.
- Rejected options:
  - assuming `scripts/restart_release.sh` coverage is enough for child restart scripts
  - relying on manual `workflow_dispatch` to compensate for incomplete automatic filters
  - broadening `deploy_required` to every `ops/**` path without isolating activation proof files

## Reuse-first plan (mandatory)
- Internal reuse:
  - `.github/workflows/ci.yml`
  - existing `changes` job with `dorny/paths-filter@v3`
  - existing workflow YAML parse checks
  - existing shell parse checks used for deploy steps
- External reuse:
  - GitHub Docs above for path-filter semantics
- Why not reinvent the wheel:
  - the workflow already has a proper change-detection layer; the gap is incomplete coverage of activation-specific files, not missing CI infrastructure

## Execution profile (mandatory for non-doc blocks)
- TP mode: `implementation`
- Doc touch budget (files): `6`
- Code dominance: `workflow filter hardening + deterministic guard test`
- Override token: `none`
- Why this profile fits:
  - this block is a small but production-impacting CI governance correction with one workflow change, one deterministic regression test, and minimal canon/session updates

## Root cause (mandatory)
- Symptom:
  - merge/main runs can skip real deploy/livecheck proof even when the change modifies the activation-service restart path that production deploy actually executes
- Minimal reproduction:
  - inspect `.github/workflows/ci.yml`: `deploy_required` and `livecheck_required` do not include `scripts/restart_knowledge_activation_service.sh`
  - merged P11 fixed `scripts/restart_knowledge_activation_service.sh`, but the subsequent main run skipped deploy/livecheck because the changed file did not match those filters
- Evidence:
  - `.github/workflows/ci.yml`
  - merged main run where deploy/livecheck were skipped after the activation-service restart-script fix
  - `gh pr view 980` / merged workflow status showing skipped proof lanes after the product block
- Five Whys:
  1. Why did deploy/livecheck skip for an activation-service restart fix? Because the changed file was not in the workflow path filters.
  2. Why was it not in the filters? Because the initial deploy gating covered parent release scripts but omitted the dedicated activation-service restart script.
  3. Why is that important now? Because the deploy path now explicitly restarts `truffles-knowledge-activation-service` as part of the knowledge release model rollout.
  4. Why did the gap survive previous fixes? Because earlier work focused on deploy auth, digest handling, and runtime proofs, not on the change-detection gate that decides whether those proofs execute.
  5. Why is manual dispatch not enough? Because merge safety cannot depend on an operator remembering to force a run for a file that the workflow should classify automatically.
- Root cause statement:
  - CI change detection for deploy/livecheck is incomplete: activation-specific deploy-proof files are outside the automatic path filters, so deploy-safety jobs can be skipped for real production-impacting changes
- Fix mechanism:
  - add the missing activation deploy/proof files to the relevant `deploy_required` and `livecheck_required` filter sets, and add a deterministic regression test that asserts these filter memberships directly from `.github/workflows/ci.yml`

## Invariant
- Do not weaken deploy gating by expanding it to unrelated broad globs without reason.
- Do not remove the existing distinction between `deploy_required` and `livecheck_required`.
- Keep main deploy fail-closed: production-impacting activation changes must trigger the same proof lanes automatically.

## Scope
- Harden workflow path filters for knowledge-activation deploy/proof files
- Add deterministic regression coverage for the workflow filter contract
- Update canon/session docs for the residual infra closure

## Out of scope
- New deploy logic, rollout logic, or live runtime changes
- Reworking unrelated CI filters
- Changing console-contract gating
- Manual deploys or workflow_dispatch as acceptance proof

## Touch-list
- `.github/workflows/ci.yml`
- `truffles-api/tests/test_ci_workflow_path_filters.py`
- `docs/TASK_PACKAGES/TP-2026-03-16-ci-path-filter-hardening-p13-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Update the active TP/session context for the CI hardening block and record the path-filter RCA.
2. Patch `.github/workflows/ci.yml` so activation restart/proof files are classified as deploy/livecheck impacting.
3. Add a deterministic regression test that parses the workflow and asserts the required filter membership.
4. Run targeted tests and workflow parse checks, then sync canon/session docs and prepare the PR.

## DoD
- `scripts/restart_knowledge_activation_service.sh` is included in both `deploy_required` and `livecheck_required`.
- Activation post-deploy proof files that must execute on `main` are included in the appropriate filters, so the automatic proof path no longer skips them.
- A deterministic regression test fails if the required workflow filter membership drifts again.
- Targeted checks are green and session/canon docs reflect the closure and remaining residuals honestly.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_ci_workflow_path_filters.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check tests/test_ci_workflow_path_filters.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && python3 - <<'PY'
import yaml
from pathlib import Path
workflow = Path('.github/workflows/ci.yml')
yaml.safe_load(workflow.read_text(encoding='utf-8'))
print('YAML_PARSE_OK')
PY`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - if the missing activation files are added to the right filters, future merge/main runs will automatically execute deploy/livecheck proof for these changes instead of silently skipping them
- Expected measurable effect:
  - the workflow filter contract test passes and the changed files now appear in both required filter sets
- Max full runs: `0`
- Max targeted reruns per failure family: `2`
- Stop condition:
  - stop after the workflow filter test, YAML parse, and session check are green

## Evidence
- diff in `.github/workflows/ci.yml`
- deterministic workflow filter regression test output
- YAML parse output
- `SESSION_AGENT=a30 bash scripts/session_check.sh`
- updated session/canon docs

## Rollback
- Revert the workflow filter/test commit if it triggers deploy/livecheck too broadly or breaks CI parsing.

## Release safety (mandatory for non-doc changes)
- Strategy:
  - narrow CI-governance correction only; no runtime code changes
- Go/no-go signals:
  - workflow parses
  - deterministic test confirms required filter membership
  - session check stays green
- Rollback:
  - revert the workflow filter change if it causes unrelated deploy churn
- Post-release monitoring window:
  - watch the first merged main run touching one of the protected files and confirm deploy/livecheck no longer skip

## No-go
- No manual dispatch as substitute for fixing the automatic filter
- No blanket `ops/**` in `deploy_required` unless the file is part of the deploy proof path
- No changes to unrelated CI jobs to “make green”

## Risks/blockers
- Over-broad filter additions can cause unnecessary deploy runs; the file list must stay precise.
- Under-broad additions will leave the governance gap open, so the regression test must assert exact required files.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `console-contract-live` remains intentionally independent from activation restart-script changes; only deploy/livecheck proof is hardened here.
- Release evidence still lives primarily in workflow artifacts, not in a first-class persisted rollout record.

### Why not in this block
- This block is only about restoring automatic deploy/livecheck proof for activation path changes. Console-contract policy and persisted rollout history are separate concerns.

### Risk if deferred
- Without persisted rollout records, audit still depends on GitHub artifacts/history. Without console-contract policy review, some non-contract infra changes may continue to skip Schemathesis by design.

### Linked follow-up Task Package(s)
- Follow-up block for persisted rollout evidence / release history.
- Follow-up block for reviewing whether post-deploy proof files should also influence console-contract lanes.

### Expiry/trigger to stop deferral
- If a future production incident requires historical rollout evidence beyond GitHub retention, persisted rollout records become blocking.

## Next-block contract (mandatory)
### Next block objective
- Confirm the first merged main run touching an activation deploy/proof file actually executes deploy/livecheck, then decide whether the same file family should also trigger console-contract-live.

### First deterministic check command
- `rg -n "restart_knowledge_activation_service\.sh|knowledge_activation_postdeploy\.sh|knowledge_activation_closeout\.py" .github/workflows/ci.yml`

### Blocked-by conditions
- This workflow hardening block must merge first.

### Owner role for closure
- Brain / Top Architect
