# TP-2026-03-16-knowledge-activation-closeout-hardening-p10-a30

- Title/Goal: Make knowledge activation tenant closeout mandatory on `main` by promoting a canonical canary target and removing the incorrect dependency between release closeout and owner-surface rollout flags.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: knowledge activation P0-P9 facts
- `TECH.md` CI / deploy / release references
- `SPECS/SYSTEM_REFERENCE.md` release + ops references
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.github.com GitHub Actions configuration variables repository environment variables official docs`
- **Date/time (local):** `2026-03-16 08:45 Asia/Almaty`
- **Sources opened (from this query):**
  - GitHub Docs, Variables: `https://docs.github.com/en/actions/concepts/workflows-and-actions/variables`
  - GitHub Docs, Store information in variables: `https://docs.github.com/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables`
- High-signal source: official GitHub documentation
- Found solutions:
  - repository/environment variables are the canonical way to store non-sensitive workflow configuration
  - unset `vars.*` resolve to empty string, so workflows can safely layer explicit overrides over canonical defaults
- Decision: `integrate`
- Reason: P10 needs an explicit closeout-target contract in CI; official workflow variables support deterministic overrides without hiding behavior in secrets
- Rejected options:
  - keeping closeout target implicit in manual runbook commands only
  - requiring operators to pass the target on every manual workflow_dispatch
  - inventing a second config file outside the existing CI/repo canon

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing `ops/knowledge_activation_closeout.py`
  - existing `scripts/knowledge_activation_postdeploy.sh`
  - existing P9 workflow hooks in `.github/workflows/ci.yml`
- External reuse:
  - official GitHub Actions configuration-variable model from the sources above
- Why not reinvent the wheel:
  - the gap is contract wiring, not a missing proof engine; reuse the current closeout and post-deploy wrappers, then tighten the target and decision semantics

## Execution profile (mandatory for non-doc blocks)
- TP mode: `implementation`
- Doc touch budget (files): `8`
- Code dominance: `release proof semantics + CI target contract`
- Override token: `none`
- Why this profile fits:
  - the block is a narrow hardening slice on top of P9, but canon/runbook/session docs must move in the same commit as the CI/script contract change

## Root cause (mandatory)
- Symptom:
  - P9 automation still allows `closeout.status=skipped`, so `main` deploy proof is not yet a hard-required tenant closeout
- Minimal reproduction:
  - run `python3 ops/knowledge_activation_closeout.py --client-slug demo_salon --branch-slug main --guard-json /tmp/knowledge_activation_guard_go.json` against current runtime: all preview/live invariants are green, but the script returns `no_go` solely because `consultant_verification_enabled` is not set in client config
  - inspect `.github/workflows/ci.yml`: P9 still treats missing closeout target as acceptable skip
- Evidence:
  - `python3 ops/knowledge_activation_closeout.py --client-slug demo_salon --branch-slug main --guard-json /tmp/knowledge_activation_guard_go.json --pretty`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atc "SELECT c.name, b.slug, b.is_active FROM branches b JOIN clients c ON c.id=b.client_id WHERE c.name='demo_salon' ORDER BY b.slug;"`
  - `truffles-api/app/services/console_consultant_verification.py`
- Five Whys:
  1. Why is closeout still optional? Because P9 preserved `skipped` semantics when no target or rollout-enabled tenant existed.
  2. Why did no rollout-enabled tenant exist? Because the only stable canary branch (`demo_salon/main`) does not have the owner-surface rollout flag enabled.
  3. Why does that block closeout today? Because `knowledge_activation_closeout.py` treats owner-surface rollout gating as a release-closeout blocker.
  4. Why is that the wrong contract? Because release closeout is supposed to validate artifact/preview/live activation invariants, not whether the owner UI rollout flag is enabled for that tenant.
  5. Why does this matter now? Because making closeout mandatory requires a truthful canary target, and the current script couples release proof to an unrelated product rollout gate.
- Root cause statement:
  - knowledge activation closeout is incorrectly coupled to owner-surface rollout enablement, so the existing stable canary tenant (`demo_salon/main`) cannot be used as a hard-required release target even though its preview/live invariants are already healthy
- Fix mechanism:
  - decouple release closeout decision from owner-surface rollout flag, keep that flag as informational evidence, and promote `demo_salon/main` as the canonical closeout target in CI with hard-required closeout on `main`

## Invariant
- Do not fake release closeout success.
- Keep owner-surface rollout state visible as evidence; do not silently discard it.
- Keep `release_guard` fail-closed and keep `main` deploy proof deterministic.

## Scope
- Adjust closeout decision semantics to validate release invariants independent of owner-surface rollout flag
- Promote a canonical default closeout target for `main`
- Make closeout required in CI deploy proof
- Update canon/runbook/session docs

## Out of scope
- New owner-surface rollout work
- Manual prod DB mutations
- New canary tenant provisioning outside the existing `demo_salon` canary contract

## Touch-list
- `ops/knowledge_activation_closeout.py`
- `truffles-api/tests/test_knowledge_activation_closeout.py`
- `scripts/knowledge_activation_postdeploy.sh`
- `truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `.github/workflows/ci.yml`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-knowledge-activation-closeout-hardening-p10-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Plan
1. Prove the current false blocker on `demo_salon/main` and codify the corrected release-closeout semantics.
2. Update `knowledge_activation_closeout.py` to separate owner rollout evidence from release-closeout readiness.
3. Promote `demo_salon/main` as the default closeout target in post-deploy proof and require closeout on `main`.
4. Extend targeted tests for the new closeout semantics and required-closeout contract.
5. Update canon/runbook/session docs with the new hard-required target contract.

## DoD
- `knowledge_activation_closeout.py` returns `go` for a tenant whose release invariants are healthy even if owner rollout is disabled, while still exposing rollout state as evidence.
- Deploy CI on `main` now requires tenant closeout and no longer permits `skipped`.
- `demo_salon/main` is the canonical default closeout target unless explicit overrides are provided.
- Targeted tests, workflow syntax checks, and session gates are green.

## Checks
- `pytest -q truffles-api/tests/test_knowledge_activation_closeout.py truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `ruff check truffles-api/tests/test_knowledge_activation_closeout.py truffles-api/tests/test_knowledge_activation_postdeploy_script.py`
- `python3 - <<'PY'\nimport json, tempfile, pathlib, subprocess, sys\nfrom pathlib import Path\nroot = Path('.')\nfd, path = tempfile.mkstemp(suffix='.json')\nPath(path).write_text('{\"decision\":\"go\"}\\n', encoding='utf-8')\ncompleted = subprocess.run([sys.executable, 'ops/knowledge_activation_closeout.py', '--client-slug', 'demo_salon', '--branch-slug', 'main', '--guard-json', path, '--pretty'], cwd=root, capture_output=True, text=True)\nprint(completed.returncode)\nprint(completed.stdout)\nPY`
- `bash -n scripts/knowledge_activation_postdeploy.sh`
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - if release closeout stops treating owner rollout gating as a blocker and `demo_salon/main` becomes the canonical target, `main` deploy proof can require tenant closeout without resorting to fake success or runtime DB mutations
- Expected measurable effect:
  - local closeout against `demo_salon/main` with a `go` guard artifact returns `decision=go`, and post-deploy proof no longer emits `closeout.status=skipped`
- Max full runs: `1`
- Max targeted reruns per failure family: `2`
- Stop condition:
  - stop after local closeout/script/workflow/session checks are green and one CI run confirms hard-required closeout artifacts

## Evidence
- local closeout command output against `demo_salon/main`
- targeted test commands + outputs
- workflow syntax output
- session doc update
- `STATE.md` NOW update by Brain / Top Architect after validation

## Rollback
- Revert the closeout semantics + CI target commit(s)
- Return post-deploy proof to P9 optional-closeout behavior

## Release safety (mandatory for non-doc changes)
- Strategy:
  - tighten the existing P9 proof path rather than introducing a new deploy lane; `main` keeps one deploy flow with one canonical closeout target
- Go/no-go signals:
  - `release_guard=go`
  - `closeout=go`
  - no `closeout.status=skipped` on `main`
- Rollback:
  - revert the P10 commit if the first CI run shows false-negative closeout failure unrelated to release invariants
- Post-release monitoring window:
  - watch the next PR run and the first resulting `main` run through deploy proof, `console-contract-live`, and `ci-livecheck`

## No-go
- No manual DB writes to force-enable consultant verification on the canary tenant
- No hidden default target outside repo canon
- No weakening of closeout invariants or release_guard thresholds

## Risks/blockers
- If `demo_salon/main` loses active knowledge or branch health, hard-required closeout will redline `main` until the canary tenant is repaired.
- The closeout contract change must be carefully scoped so owner rollout evidence is still visible to operators.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- The hard-required target is still one demo canary tenant, not a dedicated synthetic release environment.
- Deploy/livecheck/proof still share duplicated SSH bootstrap code in `.github/workflows/ci.yml`.

### Why not in this block
- The immediate closure is to remove `skipped` from `main` proof without spinning up a new environment or reworking SSH plumbing.

### Risk if deferred
- Canary-target outages will affect release proof until a dedicated env exists.

### Linked follow-up Task Package(s)
- Follow-up block for dedicated synthetic closeout environment / persisted rollout evidence beyond one demo canary.
- Follow-up block for SSH bootstrap dedup across deploy/livecheck/proof jobs.

### Expiry/trigger to stop deferral
- If `demo_salon/main` becomes unstable as a release canary, a dedicated closeout environment becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Persist release-proof history beyond workflow artifacts so operators can query rollout guard/closeout verdicts without opening old CI runs.

### First deterministic check command
- `gh run list --workflow CI --branch main --limit 1 --json databaseId,conclusion,url`

### Blocked-by conditions
- P10 hard-required closeout must be merged and one `main` deploy run must complete successfully.

### Owner role for closure
- Brain / Top Architect
