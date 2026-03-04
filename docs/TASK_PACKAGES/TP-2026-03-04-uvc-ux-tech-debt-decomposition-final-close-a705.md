# TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-close-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#891` (`7ad5dc3d`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE5-A705

## Название/цель
Закрыть final-close после wave4 по `UX-11` и `UX-12`: подтвердить merged-main evidence, зафиксировать окончательное статус-решение по debt без эвфемизмов, и выпустить явный follow-up контракт для следующей полной волны.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave4-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: final-close only synchronizes evidence/state, no UI flow mutation.
  - proof: no runtime code touched; deterministic checks stay green.
- `REQ-2` no shortcut/costyl:
  - solution: status decision is evidence-based (`LOC + tests + lint + merged PR`) and fail-closed.
  - proof: explicit residual rationale and next-block contract.
- `REQ-3` optimize existing surfaces before new tabs:
  - solution: no new routes/tabs; follow-up remains decomposition of existing monoliths.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `truffles-api/app/services/console_onboarding_readiness.py`
  - `console-web/src/components/provisioning-wizard-readiness-panel.tsx`
  - `truffles-api/tests/test_console_onboarding_readiness.py`
  - `truffles-api/tests/test_console_control_tower_program.py`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/app/services/console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_control_tower_program.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_control_tower_program.py`
- `FACT findings`:
  - merged wave4 baseline: `console.py=24888`, `ProvisioningWizard.tsx=4742`.
  - module checks green (`pytest 7 passed`, lint clean).

## One web search (mandatory before implementation)
- **Query (exact):** `sonarqube code metrics definition cognitive complexity maintainability rating`
- **Date/time (local):** `2026-03-04 12:19 +0500`
- **Sources opened (from this query):**
  - `https://docs.sonarsource.com/sonarqube-server/10.7/user-guide/code-metrics/metrics-definition/`
- **Found reusable solution:** close technical-debt status using explicit measurable gates (complexity/size/smell trend) instead of PR-count heuristics.
- **Decision:** `integrate` metric-driven closeout logic into canon status decision and keep residual open when threshold is not met.
- **Rejected options:** declare `UX-11/UX-12` fixed only because multiple extraction waves merged.

## Root cause (mandatory)
- **Symptom:** after wave4 merge, debt status could still be interpreted inconsistently without explicit final-close criteria.
- **Minimal reproduction:**
  1. Inspect `UX-11/UX-12` rows in backlog and wave4 evidence.
  2. Compare current LOC snapshot with closure expectations.
  3. Verify deterministic checks remain green while files are still high-blast-radius.
- **Evidence:** `wc` snapshot (`24888/4742`), wave4 merged PR `#891`, targeted pytest/lint outputs.
- **Five Whys:**
  1. Why ambiguous? Final-close status was not yet recorded after wave4 merge.
  2. Why important? Teams can misread mitigation as closure.
  3. Why risky? Large monoliths still concentrate unrelated concerns.
  4. Why not mark fixed now? Objective reduction is meaningful but below closure threshold.
  5. Why proceed with final-close now? Wave4 contract requires explicit closure/residual decision.
- **Root cause statement:** missing post-wave4 final status decision and threshold-based closure contract for `UX-11/UX-12`.
- **Fix mechanism:** run deterministic merged-main checks, publish fail-closed status, and bind next block with explicit follow-up ID.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse wave1-4 extracted modules and existing deterministic tests; no new runtime path.
- **External reuse:** Sonar metric definitions for objective debt framing.
- **Why not build from scratch:** this block is governance/closure synchronization, not runtime redesign.

## Invariant
- No runtime behavior change.
- No new top-level tabs/routes.
- No weakening of quality/session gates.

## Scope
- Revalidate merged-main deterministic baseline for `UX-11/UX-12`.
- Publish final-close decision artifact.
- Sync `STATE`, `UX_BACKLOG`, master report, session/index, and audit index.

## Out of scope
- Wave5 runtime decomposition code.
- Any semantic/policy-core changes.
- Additional e2e expansion beyond wave4 evidence.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-close-a705.md` (new)
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-close-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`

## Plan (1..N)
1. Switch active session metadata to final-close block and add dedicated TP.
2. Capture deterministic merged-main checks and baseline metrics.
3. Publish final-close artifact with explicit status decision.
4. Sync canonical docs and follow-up contract.
5. Run session gate and open PR.

## DoD
- Final-close TP/artifact exist and are linked in canon docs.
- `UX-11/UX-12` status has explicit post-wave4 decision with rationale.
- Residual debt has explicit follow-up TP ID and next deterministic check command.
- `SESSION_AGENT=a705 scripts/session_check.sh` passes.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/app/services/console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_control_tower_program.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-readiness-panel.tsx --file src/components/provisioning-wizard-derived.ts --file src/components/provisioning-wizard-utils.ts`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Merged PR reference for wave4: `#891` (`7ad5dc3d`).
- Deterministic check outputs from `Checks` section.
- Canon sync diffs for `STATE`, backlog, master report, session/index.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (`doc/evidence closeout only`).
- E2E policy: reuse green wave4 acceptance evidence; rerun only if runtime code changes are introduced.
- Stop condition: any attempt to re-open runtime scope in this block triggers scope reset.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closeout.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert final-close commit.
- **Post-release monitoring window:** next wave runtime PR (`wave5`) must rerun platform-admin e2e acceptance lane.

## Rollback
- `git revert COMMIT_SHA` and rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Mark `UX-11/UX-12` fixed without measurable threshold.
- Hide residual debt as wording-only mitigation.
- Introduce runtime code in final-close block.

## Risks/блокеры
- Over-accepting residual can delay needed decomposition.
- Under-scoped wave5 may fail to reduce blast radius materially.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `console.py` and `ProvisioningWizard.tsx` remain high-blast-radius despite wave1-4 reduction.
- `Why not in this block`: final-close is governance synchronization; runtime decomposition continues in next dedicated wave.
- `Risk if deferred`: medium-high regression risk for future multi-concern edits.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave5-a705.md`.
- `Expiry/trigger to stop deferral`: any upcoming change touching >3 unrelated concerns in either monolith mandates wave5 execution first.

## Next-block contract (mandatory)
- `Next block objective`: execute `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE5-A705` with another bounded feature-slice extraction in backend and frontend monoliths.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: final-close PR not merged or baseline checks red.
- `Owner role for closure`: Brain + Top Architect.
