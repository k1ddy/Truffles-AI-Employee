# TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#893` (`94ee1152`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE6-A705

## Название/цель
Выполнить closure-review после wave5: проверить merged-main метрики и deterministic evidence, принять fail-closed статус-решение по `UX-11/UX-12`, и зафиксировать следующий атомарный блок без пропусков/дублей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave5-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review is governance/evidence only; runtime UX/actions unchanged.
  - proof: no runtime code changes in this block.
- `REQ-2` no shortcut/costyl:
  - solution: status derives from measured baseline (`LOC + deterministic checks`), not from merged PR count.
  - proof: explicit closure rationale in artifact + canon docs.
- `REQ-3` optimize existing surfaces before new tabs:
  - solution: next block is wave6 decomposition in existing files; no new top-level routes.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `truffles-api/app/services/console_router_utils.py`
  - `console-web/src/components/provisioning-wizard-shell-panels.tsx`
  - `truffles-api/tests/test_console_router_utils.py`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py truffles-api/tests/test_console_router_utils.py`
  - `pytest -q truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `FACT findings`:
  - merged wave5 baseline: `console.py=24897`, `ProvisioningWizard.tsx=4679`.
  - deterministic checks are green (`16 passed`), but closure threshold for monolith blast-radius is still not reached.

## One web search (mandatory before implementation)
- **Query (exact):** `sonarqube maintainability rating technical debt ratio definitions`
- **Date/time (local):** `2026-03-04 12:58 +0500`
- **Sources opened (from this query):**
  - `https://docs.sonarsource.com/sonarqube-server/10.7/user-guide/code-metrics/metrics-definition/`
- **Found reusable solution:** close maintainability debt only when objective debt metrics/complexity trend meet defined threshold, not by milestone count.
- **Decision:** `integrate` objective closure criteria and keep residual open when large-file blast-radius remains high.
- **Rejected options:** mark `UX-11/UX-12` fixed after wave5 merge without threshold attainment.

## Root cause (mandatory)
- **Symptom:** after wave5 merge, `UX-11/UX-12` still show high residual blast-radius despite multiple extractions.
- **Minimal reproduction:**
  1. run `wc -l` on `console.py` and `ProvisioningWizard.tsx`.
  2. verify deterministic checks pass.
  3. compare with closure expectation for monolith decomposition.
- **Evidence:** post-merge `wc` (`24897/4679`), `pytest 16 passed`, wave5 merged PR `#893`.
- **Five Whys:**
  1. Why not fixed? Sizes and concern concentration remain high.
  2. Why despite wave5? Parallel main updates increased router size again.
  3. Why is this risky? Small feature edits still require touching many unrelated concerns.
  4. Why no shortcut? Declaring fixed would hide objective residual risk.
  5. Why closure-review now? wave5 contract requires explicit decision and follow-up block.
- **Root cause statement:** bounded wave5 extraction improved structure but did not reduce total monolith blast-radius below closure threshold.
- **Fix mechanism:** keep `UX-11/UX-12` open with explicit wave6 decomposition contract and measurable stop criteria.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse existing extracted utility/component modules; next wave extends same decomposition pattern.
- **External reuse:** Sonar metric definitions for objective maintainability closure.
- **Why not build from scratch:** closure-review is governance decision, not rewrite.

## Invariant
- No runtime behavior changes.
- No new tabs/routes.
- Quality/session gates stay fail-closed.

## Scope
- Confirm merged-main evidence for wave5.
- Publish closure-review status decision artifact.
- Sync `STATE`, backlog, master report, structure/index/session.
- Bind next block (`wave6`) with deterministic first check and blockers.

## Out of scope
- wave6 runtime code changes.
- e2e contract redesign.
- any policy-core/booking logic changes.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705.md` (new)
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave6-a705.md` (new)
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Plan (1..N)
1. Create closure-review TP and switch active session metadata.
2. Capture deterministic merged-main evidence and closure decision.
3. Publish closure-review artifact + wave6 follow-up TP.
4. Sync canon docs and run session gate.
5. Open PR.

## DoD
- closure-review TP + artifact are published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- wave6 follow-up TP linked with deterministic next-block contract.
- `SESSION_AGENT=a705 scripts/session_check.sh` passes.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py truffles-api/tests/test_console_router_utils.py`
- `pytest -q truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave5 merged PR reference: `#893` (`94ee1152`).
- deterministic check outputs from `Checks`.
- canon sync diffs with explicit closure-review decision.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (doc/evidence closure block).
- E2E policy: reuse green wave5 acceptance evidence (`26 passed`) since runtime code unchanged.
- Stop condition: if closure decision requires new runtime changes, stop and move to wave6 block.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review commit.
- **Post-release monitoring window:** wave6 PR must rerun full targeted acceptance lane.

## Rollback
- `git revert COMMIT_SHA` and rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- mark `UX-11/UX-12` fixed without threshold evidence.
- hide residual debt behind wording-only updates.
- mix wave6 code changes into closure-review block.

## Risks/блокеры
- Continuing residual may accumulate if wave6 scope is too small.
- Parallel `main` changes can offset LOC reductions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: high residual concentration in `console.py` and `ProvisioningWizard.tsx` after wave5.
- `Why not in this block`: closure-review is decision/governance, not implementation.
- `Risk if deferred`: medium-high regression and review overhead.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave6-a705.md`.
- `Expiry/trigger to stop deferral`: if wave6 does not deliver measurable reduction in both monoliths, escalate to architecture-level decomposition decision.

## Next-block contract (mandatory)
- `Next block objective`: execute `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE6-A705` with one backend and one frontend bounded extraction.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: closure-review PR not merged or baseline checks red.
- `Owner role for closure`: Brain + Top Architect.
