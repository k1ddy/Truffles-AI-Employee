# TP-2026-04-01-console-k6-cadence-split-a922

- Название/цель: разделить Console k6 на три режима без случайного live-прогона на каждом PR: автоматический PR smoke для non-prod, ручной live smoke и nightly live drift check.

## Canon refs
- `TECH.md`
- `docs/DEV_SETUP.md`
- `.github/workflows/ci.yml`
- `ops/k6/console_smoke.js`

## One web search (mandatory before implementation)
- Query: `GitHub Actions workflow_dispatch schedule events official docs`
- Date/time: `2026-04-01 Asia/Almaty`
- Opened sources:
  - `https://docs.github.com/actions/using-workflows/events-that-trigger-workflows`
- Found reusable solution:
  - keep PR gating in `pull_request`
  - move live/scheduled load checks into a dedicated workflow
- Decision: `reuse/integrate`
- Why: existing repo already has a safe read-only k6 script; the missing piece is workflow cadence split, not a new tool.
- Rejected variants:
  - run live k6 from `ci.yml` on every PR
  - run PR k6 against live API by default

## Root cause (mandatory)
- Symptom: `console-k6` almost never runs and is constantly seen as skipped in CI.
- Minimal reproduction: inspect `.github/workflows/ci.yml` and observe `console-k6` requires `workflow_dispatch` plus `run_k6=true`.
- Evidence:
  - `.github/workflows/ci.yml`
  - `ops/k6/console_smoke.js`
  - `TECH.md`
- Five Whys:
  1. Why skipped: job only runs on `workflow_dispatch`.
  2. Why manual-only: current target is live Console API.
  3. Why not automatic: live load smoke must not hit prod on every PR.
  4. Why still ineffective: there is no separate PR-safe non-prod lane.
  5. Why confusion persists: one job name currently mixes manual live intent with CI expectations.
- Broken invariant: Console perf smoke cadence is not aligned with the intended environments.
- Shared mechanism: workflow-trigger design for Console k6.
- Why surfaced issue belongs to this mechanism: skip behavior comes from workflow conditions and target selection, not from the k6 script itself.
- Open-world envelope expected to improve:
  - PRs touching console surfaces get an automatic smoke lane when non-prod target is configured.
  - live drift is checked outside PR CI on a schedule.
- Root cause statement: the repo had one manual live-only k6 job but no dedicated PR-safe or nightly cadence.
- Fix mechanism:
  - add `console-k6-pr` to `ci.yml`
  - move live/manual and nightly live into a dedicated workflow
  - allow optional selection headers in the k6 script

## Invariant
- k6 remains read-only.
- PR lane must not default to live API.
- live smoke stays explicit and observable.

## Scope
- `.github/workflows/ci.yml`
- `.github/workflows/console-k6.yml`
- `ops/k6/console_smoke.js`
- `TECH.md`
- `docs/DEV_SETUP.md`

## Out of scope
- provisioning a new preview Console API environment
- mutating k6 scenarios
- changing Console API auth model

## Plan
1. Add a PR k6 lane gated by console-related path changes and explicit non-prod secrets.
2. Move live manual smoke into a dedicated workflow.
3. Add nightly scheduled live smoke.
4. Extend the k6 script with optional tenant-selection headers.
5. Update operator docs.

## DoD
- PR console changes can trigger `console-k6-pr`.
- Live/manual and nightly k6 are available outside the main CI pipeline.
- k6 script supports optional selection headers.
- Docs explain the three modes and required secrets.

## Checks
- `python3 - <<'PY' ... yaml.safe_load(...)` for workflow syntax
- `node --check ops/k6/console_smoke.js`
- `git diff --check`

## Evidence
- workflow files diff
- updated `TECH.md`
- updated `docs/DEV_SETUP.md`

## Rollback
- revert `.github/workflows/ci.yml`
- remove `.github/workflows/console-k6.yml`
- revert `ops/k6/console_smoke.js`
- revert docs

## No-go
- no prod-by-default PR k6 target
- no mutating load tests
- no silent skip for live/nightly missing secrets

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - no proven ephemeral/non-prod Console API lane is provisioned in repo/CI yet
- Why not in this block:
  - that requires infra and seeded auth/data, not just workflow surgery
- Risk if deferred:
  - `console-k6-pr` may skip until preview secrets exist
- Linked follow-up Task Package(s):
  - future preview Console API provisioning TP
- Expiry/trigger to stop deferral:
  - if console surfaces keep changing but `console-k6-pr` never executes on a real non-prod target

## Next-block contract (mandatory)
- Next block objective: provision a stable non-prod Console API target for `console-k6-pr`
- First deterministic check command:
  - `gh secret list -R k1ddy/Truffles-AI-Employee | rg 'CONSOLE_K6_PR_'`
- Blocked-by conditions:
  - missing preview URL, auth, or seeded tenant selection headers
- Owner role for closure:
  - Brain / Top Architect with infra access
