# TP-2026-03-15-ci-deploy-ssh-auth-unification-p7-a30

## Block identity
- `BLOCK_ID`: `CI-DEPLOY-SSH-AUTH-UNIFICATION-P7-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-CLOSEOUT-P6-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-ACTIVATION-DONE-A30`
- `UNLOCKS`: `CI-DEPLOY-POSTMERGE-CLOSEOUT-P8-A30`

## Название/цель
Устранить post-merge падение `deploy` на `main` из-за SSH authentication drift: deploy должен использовать тот же нормализованный и проверенный SSH bootstrap, что уже используется в livecheck, чтобы deploy/auth path перестал зависеть от отдельной интерпретации секрета в `appleboy/ssh-action`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `.github/workflows/ci.yml`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `CA_ID`: `N/A`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `.github/workflows/ci.yml`
  - `docs/TASK_PACKAGES/TP-2026-03-15-ci-deploy-ssh-auth-unification-p7-a30.md`
  - `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `FACT findings`:
  - Merge run `23112703782` on `main` failed only in `deploy` while `lint`, `unit-tests`, `console-contract-predeploy`, `console-e2e`, and `build-push` were green.
  - Failed job/step: `deploy` / `Deploy to VPS`.
  - Failed log line: `ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain`.
  - The same workflow already contains a working SSH normalization + validation path for livecheck (`ssh-keygen -yf`, newline/base64 normalization, `ssh-keyscan`).
  - Deploy currently bypasses that path and hands the raw secret directly to `appleboy/ssh-action`.

## One web search (mandatory before implementation)
- **Query (exact):** `GitHub Actions encrypted secrets multiline SSH private key formatting docs`
- **Date/time (local):** `2026-03-15 20:00 +05`
- **Sources opened (from this query):** `https://docs.github.com/actions/security-guides/encrypted-secrets`
- **Found options:** GitHub secrets commonly need explicit newline-preserving handling for multiline values; environment materialization and validation on-runner is a stable pattern when a downstream action interprets raw secret formatting differently.
- **Decision:** `reuse/integrate` — reuse the existing runner-side SSH bootstrap already present in this repo and route deploy through the validated `~/.ssh/id_rsa` path instead of depending on `appleboy/ssh-action` raw key parsing.
- **Rejected options:** rotate secrets first without fixing workflow asymmetry; keep `appleboy/ssh-action` and hope formatting stays stable; add `continue-on-error` around deploy.
- **Source quality:** high-signal primary source = official GitHub documentation.

## Root cause (mandatory)
- **Symptom:** merged code is green, but the `main` deploy run fails immediately on SSH auth before any runtime deploy logic executes.
- **Minimal reproduction:** run `CI` on `main` with current workflow; `deploy` reaches `Deploy to VPS` and fails with SSH authentication while the same secret can still be normalized and used by the livecheck SSH bootstrap.
- **Evidence:** `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/23112703782`, job `67133128703`, `.github/workflows/ci.yml:957`, `.github/workflows/ci.yml:1482`.
- **Five Whys (or equivalent):**
  1. Why did deploy fail? Because SSH authentication failed before the remote script ran.
  2. Why did auth fail in deploy but not in livecheck? Because deploy and livecheck use different SSH key handling paths.
  3. Why are the paths different? Deploy passes the raw secret to `appleboy/ssh-action`, livecheck normalizes/validates the secret on-runner first.
  4. Why is that unsafe? Because multiline/base64/escaped secret formats can be accepted by one path and rejected by another.
  5. Why is this a workflow design issue, not an infra-only incident? Because the workflow duplicates SSH handling with inconsistent semantics for the same secret.
- **Root cause statement:** deploy and livecheck use divergent SSH key parsing semantics; the deploy path trusts `appleboy/ssh-action` raw secret handling instead of reusing the repository’s validated SSH bootstrap, so secret-format drift causes deploy-only auth failures.
- **Fix mechanism:** move deploy onto the same runner-side SSH bootstrap model as livecheck: normalize + validate the key, populate `known_hosts`, perform explicit SSH preflight, then execute the deploy script over standard `ssh`.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `Configure SSH` logic in `.github/workflows/ci.yml` and sibling workflows (`livecheck-only`, `onboarding-fleet-guard`).
- **External reuse:** GitHub encrypted secrets handling guidance.
- **Why not reinvent the wheel:** the repo already has a working SSH normalization routine; the gap is that deploy does not use it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `CI workflow / deploy transport`
- **Override token:** `none`
- **Why this profile fits:** one workflow slice with a narrow operational fix and targeted validation.

## Invariant
- Deploy on `main` remains mandatory when `deploy_required=true`.
- Deploy source remains `origin/main`.
- Deploy parity checks (`EXPECTED_GIT_COMMIT`, console build SHA) remain fail-closed.
- No product/runtime behavior changes.

## Scope
- Replace deploy SSH auth path with the same normalized runner-side SSH bootstrap already used by livecheck.
- Add explicit deploy SSH preflight and clearer auth failure diagnostics.

## Out of scope
- Secret rotation on GitHub/VPS.
- Release guard / closeout automation changes.
- Runtime restart script semantics.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-03-15-ci-deploy-ssh-auth-unification-p7-a30.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Repoint the deploy job to runner-side SSH bootstrap reuse instead of raw `appleboy/ssh-action` key parsing.
2. Add deploy SSH preflight and fail with explicit auth diagnostics before the remote deploy script.
3. Validate workflow syntax and session gates locally.
4. Push the fix and use the next `main`/PR run as evidence.

## DoD
- Deploy no longer depends on `appleboy/ssh-action` raw key parsing.
- The workflow validates/normalizes the SSH key before deploy.
- Auth failures become explicit preflight failures instead of opaque action-level handshake errors.
- Local workflow syntax/session checks are green.

## Checks
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `git diff -- .github/workflows/ci.yml`
- `SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** if deploy uses the same normalized SSH bootstrap as livecheck, the current post-merge failure class will disappear and auth problems will fail earlier with clearer diagnostics.
- **Expected measurable effect:** `deploy` will stop failing inside `appleboy/ssh-action` with raw handshake errors and will instead either pass SSH preflight or fail at explicit runner-side preflight.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after green local workflow syntax/session checks and one confirming CI run.

## Evidence
- Red run URL: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/23112703782`
- Failed job/step: `deploy` / `Deploy to VPS`
- Error line: `ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain`
- Next green run after workflow fix

## Rollback
- Revert the workflow commit; deploy returns to the previous `appleboy/ssh-action` path.

## Release safety (mandatory for non-doc changes)
- **Strategy:** deploy transport hardening only; no runtime contract changes.
- **Go/no-go signals:** workflow syntax parse green, session gate green, next CI deploy reaches remote script/preflight using normalized SSH path.
- **Post-release monitoring window:** monitor the first green `main` deploy plus the immediate post-deploy livecheck/deploy parity steps in the same CI run.
- **Rollback:** revert workflow change if deploy regression appears.

## No-go
- Do not disable deploy on `main`.
- Do not add `continue-on-error`.
- Do not weaken deploy parity or post-deploy checks.
- Do not mutate runtime secrets inside the repo as a “fix”.

## Risks/Blockers
- If the secret or VPS `authorized_keys` are truly invalid, workflow hardening will only surface the problem earlier and more clearly; it will not magically repair infra.
- GitHub-hosted runner IP/network issues remain a separate class of deploy risk.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- SSH bootstrap code remains duplicated across workflow sections and sibling workflows.

### Why not in this block
- This block fixes the failing `main` deploy path first; cross-workflow extraction/composite action can follow after deploy is stable again.

### Risk if deferred
- Future edits can reintroduce divergence between deploy and livecheck SSH handling.

### Linked follow-up Task Package(s)
- `TBD`: extract shared SSH bootstrap into one reusable workflow/composite action if deploy fix proves stable.

### Expiry/trigger to stop deferral
- Open the follow-up if another SSH-format/auth drift appears in deploy or livecheck.

## Next-block contract (mandatory)
### Next block objective
- Automate post-deploy knowledge activation release guard + closeout after deploy transport is stable again.

### First deterministic check command
- `gh run view 23112703782 --job 67133128703 --log`

### Blocked-by conditions
- Deploy SSH path must stop failing at authentication.

### Owner role for closure
- `Top Architect | Brain`

## Branch / Worktree / Merge
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect after merge
