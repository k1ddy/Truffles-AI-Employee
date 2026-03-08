# TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review2-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW2-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE6-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE7-A705` (only if residual remains)

## Название/цель
Выполнить closure-review после wave6: принять fail-closed статус-решение по `UX-11/UX-12` на merged-main evidence и зафиксировать следующий атомарный контракт без пропусков/дублей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave6-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review2 is governance/evidence only; runtime UX/actions unchanged.
  - proof: no runtime code changes in this block.
- `REQ-2` no shortcut/costyl:
  - solution: decision derives from merged-main metrics (`LOC + deterministic checks`), not merged PR count.
  - proof: explicit rationale in closure-review2 artifact and canon.
- `REQ-3` optimize existing surfaces before new tabs:
  - solution: next block (if needed) is `wave7` decomposition in existing files; no new top-level routes.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24743`, `4617`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_fleet_state.py truffles-api/tests/test_console_fleet_state.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py` -> `24 passed`

## One web search (mandatory before implementation)
- **Query (exact):** `SonarQube cognitive complexity and maintainability metrics definitions`
- **Date/time (local):** `2026-03-04 13:17 +0500`
- **Sources opened (from this query):**
  - `https://docs.sonarsource.com/sonarqube-server/10.6/user-guide/code-metrics/metrics-definition`
- **Found reusable solution:** debt closure should rely on objective maintainability/complexity signals, not on milestone count.
- **Decision:** `integrate` objective closure criteria and keep residual open when large-file blast-radius remains high.
- **Rejected options:** mark `UX-11/UX-12` fixed immediately after wave6 merge without closure threshold evidence.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` may still remain open after wave6 despite additional extraction.
- **Minimal reproduction:**
  1. run `wc -l` for `console.py` and `ProvisioningWizard.tsx`;
  2. run deterministic checks (`py_compile`, `pytest`);
  3. compare residual blast-radius with closure expectation.
- **Evidence:** merged-main wave6 baseline (`24743/4617`, `pytest 24 passed`) + previous closure-review chain.
- **Five Whys:**
  1. Why possible residual? monolith concentration remains high even after bounded splits.
  2. Why after wave6? extraction was intentionally bounded to minimize behavior risk.
  3. Why risky? small feature edits still touch high-context files.
  4. Why no early `Fixed`? would hide residual maintenance risk.
  5. Why closure-review2 now? wave6 contract requires explicit merged-main decision.
- **Root cause statement:** current decomposition improved structure but may still be above closure threshold for `UX-11/UX-12`.
- **Fix mechanism:** make fail-closed status decision from merged-main evidence; if open, launch wave7 with bounded slices.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse existing decomposition pattern (`console_*` services and `provisioning-wizard-*` modules).
- **External reuse:** Sonar metric definitions as objective maintainability reference.
- **Why not build from scratch:** closure-review2 is decision/governance block, not rewrite.

## Invariant
- No runtime behavior changes.
- No new tabs/routes.
- Quality/session gates remain fail-closed.

## Scope
- Revalidate merged-main wave6 evidence.
- Publish closure-review2 artifact and explicit `UX-11/UX-12` status decision.
- Sync canon docs and session index.

## Out of scope
- Wave7 runtime extraction.
- Contract redesign beyond status decision.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review2-a705.md` (new)
- `STATE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STRUCTURE.md`
- session docs/index

## Plan (1..N)
1. Capture merged-main deterministic baseline after wave6 merge.
2. Publish closure-review2 artifact (`Fixed` vs `Open` decision).
3. Sync canon/session docs and run `session_check`.
4. Open PR.

## DoD
- closure-review2 artifact published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_fleet_state.py truffles-api/tests/test_console_fleet_state.py`
- `pytest -q truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave6 merged PR URL + commit SHA.
- merged-main deterministic check outputs.
- closure-review2 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (docs/evidence decision block).
- E2E policy: reuse green wave6 acceptance evidence (`26 passed`) since runtime unchanged.
- Stop condition: if decision requires runtime code, stop and move to wave7 block.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review2 commit.
- **Post-release monitoring window:** wave7 PR must rerun targeted acceptance lane if launched.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `UX-11/UX-12` fixed without merged-main threshold evidence.
- Mixing runtime changes into closure-review2 docs block.

## Risks/блокеры
- Parallel `main` changes can offset LOC reduction.
- False closure if only module count changes without blast-radius reduction.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: TBD from merged-main wave6 evidence.
- `Why not in this block`: closure-review2 is governance decision, not implementation.
- `Risk if deferred`: prolonged high review/maintenance cost.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave7-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if wave6 still leaves high residual, open wave7 with explicit bounded slices.

## Next-block contract (mandatory)
- `Next block objective`: either close `UX-11/UX-12` as `Fixed` with evidence or launch `wave7` bounded extraction.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave6 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
