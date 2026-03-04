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
