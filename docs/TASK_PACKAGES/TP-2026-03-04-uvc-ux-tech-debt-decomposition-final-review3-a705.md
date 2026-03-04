# TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-review3-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-REVIEW3-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE7-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE8-A705` (only if residual remains)

## Название/цель
Сделать финальный review после wave7 на merged-main evidence и принять fail-closed решение по `UX-11/UX-12`: `Fixed` либо `Open + wave8`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave7-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: review block changes docs/evidence only; runtime surfaces unchanged.
- `REQ-2` no shortcuts:
  - solution: closure decision uses deterministic merged-main evidence, not milestone count.
- `REQ-3` optimize existing tabs first:
  - solution: if residual remains, next block is internal wave8 decomposition only.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`

## One web search (mandatory before implementation)
- **Query (exact):** `SonarQube maintainability and cognitive complexity definitions`
- **Date/time (local):** `2026-03-04 15:05 +0500`
- **Sources opened (from this query):**
  - `https://docs.sonarsource.com/sonarqube-server/10.6/user-guide/code-metrics/metrics-definition`
- **Found reusable solution:** closure should be based on objective maintainability signals and explicit quality checks.
- **Decision:** use objective merged-main evidence and keep fail-closed contract.
- **Rejected options:** marking `Fixed` only because wave count increased.

## Root cause (mandatory)
- **Symptom:** risk that `UX-11/UX-12` remain high-blast-radius even after wave7.
- **Minimal reproduction:** compare merged-main LOC + deterministic checks + residual hotspots in monolith entry files.
- **Evidence:** wave7 artifact and merged-main check outputs.
- **Five Whys:**
  1. why uncertain closure: extractions may still leave orchestration concentration;
  2. why risky: routine edits still may touch broad files;
  3. why review needed: prevent false `Fixed` status;
  4. why fail-closed: protects quality contract;
  5. why now: wave7 completion requires explicit final decision.
- **Root cause statement:** structural debt may persist despite wave7 and must be judged by evidence.
- **Fix mechanism:** evidence-based final decision + wave8 contract only if needed.

## Reuse-first plan (mandatory)
- Reuse existing wave artifacts, deterministic suites, and canon sync pattern.
- No new runtime implementation in review block.

## Invariant
- No runtime code changes.
- No new routes/tabs.
- Decision is evidence-first and fail-closed.

## Scope
- Revalidate merged-main wave7 baseline.
- Publish final-review3 artifact with explicit `UX-11/UX-12` decision.
- Sync canon/session docs.

## Out of scope
- Runtime wave8 implementation.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-review3-a705.md`
- `STATE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STRUCTURE.md`
- session docs/index

## Plan (1..N)
1. Capture merged-main wave7 deterministic baseline.
2. Publish final-review3 artifact with `Fixed/Open` decision.
3. Sync canon/session docs and run `session_check`.
4. Open PR.

## DoD
- final-review3 artifact published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave7 merged PR URL + commit SHA.
- merged-main deterministic outputs.
- final-review3 artifact + canon sync diff.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `Fixed` without deterministic merged-main evidence.
- Mixing runtime refactor into review block.

## Риски/блокеры
- Parallel main changes can skew LOC baseline.
- Review can be biased if deterministic checks are skipped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided from merged-main wave7 evidence.
- `Why not in this block`: review block is governance-only.
- `Risk if deferred`: repeated high-context edits in monoliths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave8-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if final-review3 is `Open`, wave8 must start immediately as next block.

## Next-block contract (mandatory)
- `Next block objective`: either mark `UX-11/UX-12` as `Fixed` or execute wave8 bounded extraction.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave7 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
