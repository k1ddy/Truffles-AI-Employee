# TP-2026-03-04-uvc-ux-tech-debt-decomposition-closeout-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSEOUT-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#889` (`feeb60e1`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE4-A705 (only if residual remains open)

## Название/цель
Закрыть closeout-этап после wave1/2/3 по `UX-11` и `UX-12`: подтвердить merged evidence на `main`, зафиксировать финальный статус (`Fixed` или explicit residual), и синхронизировать канон без изменения runtime-поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave2-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave3-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closeout is doc/evidence only; no UI/API flow changes.
  - proof: targeted platform-admin contract lane remains green on merged main.
- `REQ-2` no shortcut/costyl:
  - solution: closeout decision based on deterministic checks + LOC/concern evidence.
  - proof: explicit status rationale in backlog/master/state.
- `REQ-3` optimize existing surfaces before new tabs:
  - solution: no new tabs/routes; only decomposition status and residual contract.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `truffles-api/app/services/console_control_tower_program.py`
  - `console-web/src/components/provisioning-wizard-derived.ts`
  - `truffles-api/tests/test_console_control_tower_program.py`
  - `console-web/e2e/platform-admin.spec.ts`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `pytest -q truffles-api/tests/test_console_control_tower_program.py`
  - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `FACT findings`:
  - wave1/2/3 merged (`#885`, `#888`, `#889`), but monolith LOC remains high (`console.py=24920`, `ProvisioningWizard.tsx=4819`).

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com technical debt metaphor principal interest`
- **Date/time (local):** `2026-03-04 13:02 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/TechnicalDebt.html`
- **Found reusable solution:** debt should be closed where change-frequency + interest justify it; stable-but-large modules may remain residual only with explicit interest/risk contract and follow-up trigger.
- **Decision:** `reuse/integrate` existing wave evidence + deterministic checks for closeout decision; avoid synthetic "fixed" without measurable closure criteria.
- **Rejected options:** declaring `UX-11/UX-12` fixed solely on merged PR count.

## Root cause (mandatory)
- **Symptom:** after wave3 merge, `UX-11/UX-12` still marked Open with mitigation, and no explicit closeout decision exists in canon.
- **Minimal reproduction:**
  1. Check master report line for decomposition block status.
  2. Check UX backlog rows `UX-11/UX-12` status.
  3. Verify merged wave PRs and current LOC snapshot.
- **Evidence:** merged commits `#885/#888/#889`, backlog rows still `Open`, high LOC snapshots.
- **Five Whys:**
  1. Why still open? Decomposition waves reduced risk but did not define closure threshold.
  2. Why threshold missing? Parent decomposition block ended with wave execution, not closeout criteria.
  3. Why risky? Teams may assume debt closed and skip further reductions.
  4. Why is that a problem? Future edits still hit high blast-radius files.
  5. Why closeout now? Wave3 next-block contract requires explicit status decision.
- **Root cause statement:** missing explicit closeout criteria/decision after merged wave1/2/3 left `UX-11/UX-12` in ambiguous state.
- **Fix mechanism:** run deterministic merged-main checks, record objective status rationale, set final status + next-block contract.

## Reuse-first plan (mandatory)
- **Internal reuse:** use existing wave artifacts and tests; no new runtime path.
- **External reuse:** Fowler technical-debt principal/interest framing for closure decision.
- **Why not build from scratch:** closeout is governance/evidence synchronization, not feature rewrite.

## Invariant
- Не менять runtime business semantics и API contracts.
- Не добавлять новые tabs/routes/actions.
- Не подменять evidence субъективным выводом без deterministic checks.

## Scope
- Confirm merged status/evidence of wave1/2/3 on current `main`.
- Re-run targeted deterministic checks for merge-safety evidence.
- Update `STATE`, master report, UX backlog, structure/index/session docs.
- Produce closeout artifact with final decision and follow-up contract.

## Out of scope
- Wave4 code decomposition itself.
- New runtime behavior/UI copy changes.
- Any policy-core or booking pipeline modifications.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closeout-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closeout-a705.md` (new)

## Plan (1..N)
1. Create closeout TP and switch active session metadata to closeout block.
2. Re-run deterministic merged-main checks (LOC + targeted pytest/lint/e2e + session check).
3. Record closeout decision for `UX-11/UX-12` (`Fixed` or `Open with residual`) with explicit rationale.
4. Sync canonical docs and publish closeout artifact.
5. Commit/push and open PR.

## DoD
- Closeout TP exists and is linked from active session.
- Deterministic checks revalidated on merged main.
- Canon docs explicitly state final `UX-11/UX-12` status and follow-up contract.
- Closeout artifact published and referenced in state/master/index/structure.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_control_tower_program.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-derived.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Merged PR references: `#885`, `#888`, `#889`.
- Check outputs from `Checks`.
- Updated `STATE` + backlog/master with explicit closeout status and follow-up trigger.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` targeted platform-admin e2e runs.
- Stop condition: repeated e2e fail without new RCA evidence.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc/evidence closeout only (no runtime change).
- **Go/no-go signals:** deterministic checks green; canon sync complete.
- **Rollback:** revert closeout commit.
- **Post-release monitoring window:** next merged PR `console-e2e` and `session-gate` checks.

## Rollback
- `git revert COMMIT_SHA` and rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `UX-11/UX-12` as fixed without deterministic merged-main evidence.
- Introducing new runtime code under closeout block.
- Skipping canon sync in `STATE/REPORT/UX_BACKLOG`.

## Risks/Blockers
- Evidence may prove debt still open and require Wave4 planning before formal closure.
- Concurrent main changes can shift LOC/check baselines during closeout.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: high LOC and multi-concern concentration remain in `console.py` and `ProvisioningWizard.tsx` after wave3.
- `Why not in this block`: closeout block is decision/governance; structural reduction continues in Wave4 if status stays open.
- `Risk if deferred`: medium-high review blast-radius for future edits.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE4-A705` (to be created if residual confirmed).
- `Expiry/trigger to stop deferral`: any next change touching >3 unrelated concerns in either file.

## Next-block contract (mandatory)
- `Next block objective`: execute Wave4 decomposition to move `UX-11/UX-12` from `Open` toward closure threshold.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: closeout PR not merged or deterministic checks red.
- `Owner role for closure`: Brain + Top Architect.
