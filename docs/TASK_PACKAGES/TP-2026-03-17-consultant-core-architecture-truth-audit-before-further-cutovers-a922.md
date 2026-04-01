# TP-2026-03-17-consultant-core-architecture-truth-audit-before-further-cutovers-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ARCHITECTURE-TRUTH-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTROLLED-DEMOLITION-MASTER-2026-03-15`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-restore-blocker-audit-after-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-AUDIT-A922`, `CONSULTANT-CORE-BOUNDED-REWORK-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать stop-the-line architecture-truth audit до любых новых runtime cutover blocks. Блок должен дать фактический ответ на три вопроса: что по master program реально done/partial/not started, какие authority seams реально deleted/unreachable, и не воспроизводит ли новый core ту же плохую multi-owner architecture shape под новыми именами. Итогом должен стать evidence-backed verdict: `continue as planned`, `bounded rework`, или `delete specific new-core slices`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-restore-blocker-audit-after-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-architecture-truth-audit-before-further-cutovers-a922.md`
  - `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '1,220p' docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
  - `sed -n '1,200p' docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
  - `sed -n '1,120p' docs/ACTIVE_PROGRAM.md`
  - `sed -n '1,220p' docs/SOURCE_OF_TRUTH.yaml`
  - `sed -n '1,40p' STATE.md`
  - `rg -n "sync_context_manager_expected_reply_state|build_expected_reply_context_sync_result|capture_pending_resume_payload|restore_pending_resume_payload|build_controlled_degrade|build_preflight_reject|build_block_override|build_degrade_override|action=\"booking_prompt\"|action=\"smalltalk\"|action=\"escalate\"" truffles-api/app/core truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - the master program defines six top-level migration blocks (`Governance Lock`, `Runtime Contracts`, `Semantic Core Cutover`, `Continuity Collapse`, `Proof Path Excision`, `Multi-Pack Proof`), but repo truth is currently tracked across many bounded child blocks rather than one explicit master closure table
  - governance lock and runtime contracts have direct machine-readable evidence in repo; semantic, continuity, boundary, proof, and multi-pack closure remain mixed across partial owner cutovers and audits
  - current canon already proves some important negative facts: Block D normal-path booking prompt family is exhausted, continuity no longer has another equally bounded non-frozen micro-cut after Block F, and the next admissible move had shifted to boundary-owner audit
  - the highest current risk is not that every new-core slice is fake, but that progress can be narrated too optimistically without a block-by-block authority deletion ledger and an explicit check against reproducing the old multi-owner power shape
- `Detected drift (docs vs code)`:
  - master intent is clear, but repo does not yet expose one concise factual report that says which master blocks are truly done, which are partial, and what rewrite threshold would force deletion of new-core slices

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com fitness functions evolutionary architecture`
- **Date/time (local):** `2026-03-17 18:08 +0500`
- **Why this query is precise:** this audit needs a high-signal reference for architecture fitness functions and atomic migration steps so the verdict is based on measurable convergence toward target architecture rather than narrative progress.
- **Sources opened (from this query):**
  - `How to break a Monolith into Microservices` — `https://martinfowler.com/articles/break-monolith-into-microservices.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** each migration step should move the system closer to the target architecture, and the anti-pattern is building the new path without retiring the old one.
- **Decision:** `reuse/integrate` — evaluate every consultant-core block as an architecture fitness step: either it retires old authority and improves the target shape, or it does not count as real progress.
- **Rejected options:**
  - continue using percentage-style progress estimates without a seam ledger
  - assume a new-core file is success by itself without proving old authority retirement
  - force more implementation blocks before checking whether the new core is reproducing the old power shape
- **Open questions:** whether the audit verdict should immediately trigger bounded rework of any current new-core slice or only tighten the next-block contract.

## Root cause (mandatory)
- **Symptom:** repo has real migration work and real guard evidence, but there is still no single factual audit that says how much of the master program is actually complete, what old authority has really died, and whether the new core is converging to the target architecture instead of re-encoding the old one.
- **Minimal reproduction:**
  1. Read `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md` and list the six top-level blocks.
  2. Compare them against `docs/ACTIVE_PROGRAM.md`, `docs/SOURCE_OF_TRUTH.yaml`, and the top `NOW` facts in `STATE.md`.
  3. Observe that many bounded child cutovers are real, but master-block closure is still implicit and spread across session logs.
  4. Observe that current canon now blocks further continuity micro-slices and points to boundary-owner work, but there is still no explicit rewrite/no-rewrite verdict on the new core itself.
- **Evidence to capture:**
  - a master-block truth table with `done/partial/not started/blocked`
  - an authority deletion ledger for semantic, continuity, boundary, and proof tracks
  - a checklist of old-architecture failure modes and whether they are still being reproduced in the new core
  - a behavior-evidence gap map distinguishing deterministic evidence from broader realism acceptance evidence
  - an explicit verdict for each major subsystem: `keep`, `bounded rework`, or `delete/rebuild`
- **Five Whys (or equivalent):**
  1. Why is remaining work hard to state factually? Because the program is implemented through many bounded child blocks but lacks a master closure ledger.
  2. Why does that matter? Because without that ledger, progress can be narrated more optimistically than the repo actually proves.
  3. Why is this dangerous? Because the new core can slowly reproduce the same multi-owner power shape while looking cleaner on the surface.
  4. Why not continue directly to boundary work? Because the user explicitly raised the risk that the new architecture itself may need deletion or rewrite.
  5. Why do this now? Because stop-the-line architecture truth is cheaper than compounding the wrong shape through more implementation.
- **Root cause statement:** the migration program has real bounded wins, but it still lacks one explicit architecture-truth audit that converts many local cutover facts into a hard verdict about actual remaining work and about whether the new core is converging or reproducing the old architecture.
- **Fix mechanism:**
  - create one factual master-block closure report
  - map real authority deletion vs surviving authority
  - check new-core files against old-architecture reproduction criteria
  - publish a rewrite/no-rewrite verdict before further cutovers

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing canon docs and bounded child TPs
  - `docs/SOURCE_OF_TRUTH.yaml` and `docs/ACTIVE_PROGRAM.md`
  - existing runtime contracts and architecture guards
  - current session evidence already recorded in `STATE.md`
- **External reuse:**
  - Martin Fowler migration/fitness-function guidance
- **Why not reinvent the wheel:** the repo already contains the raw facts; this block consolidates them into a truthful closure ledger and rewrite verdict instead of inventing a new tracking system.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is a stop-the-line governance audit and verdict block; runtime code does not change here.

## Invariant
- No runtime code edits.
- No frozen-router edits.
- No new implementation block may start before the audit verdict is recorded.
- The audit must separate FACT from inference and must not use percentage claims as closure evidence.

## Scope
- Build a master-program truth table.
- Build an authority deletion ledger.
- Check new-core files against old-architecture reproduction risks.
- Map behavior evidence gaps.
- Publish rewrite/no-rewrite verdicts per subsystem.
- Sync canon/session artifacts and regenerate the agent packet.

## Out of scope
- runtime implementation changes
- boundary-owner implementation
- continuity implementation
- proof/eval implementation
- realism test execution
- frozen-file policy changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-architecture-truth-audit-before-further-cutovers-a922.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan (1..N)
1. Publish this stop-the-line audit TP with RCA and one exact web search.
2. Build the master-block truth table from master TP + DEC + active canon + session evidence.
3. Build the authority deletion ledger for semantic, continuity, boundary, proof, and pack-agnostic tracks.
4. Evaluate new-core files against old-architecture reproduction criteria.
5. Publish rewrite/no-rewrite verdicts and next-step recommendations in one audit report.
6. Sync `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, session artifacts, and packet.
7. Run governance checks.

## DoD
- one factual audit report exists at `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- the report contains: master-block truth table, authority deletion ledger, reproduction-risk checklist, evidence-gap map, and rewrite/no-rewrite verdicts
- canon is updated so no new runtime cutover starts before this audit verdict is visible
- packet and governance checks are green

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- updated canon and packet
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** no runtime quality suites; canon/report/gov checks only
- **Stop condition:** if the audit cannot produce a factual verdict because evidence is missing, record the missing evidence explicitly and stop instead of guessing
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only stop-the-line audit; no runtime rollout
- **Go/no-go signals:** audit report completed; packet and governance checks green
- **Rollback:** revert audit docs/canon sync and regenerate packet
- **Post-release monitoring window:** the next implementation block must follow the audit verdict, not a cached previous plan

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Drift closeout rule`:
  - canon may point to this audit only if the report explicitly states what is done, what is partial, what is not started, and what rewrite thresholds would trigger bounded rework or deletion.

## Rollback
1. Revert the audit TP, report, and canon/session updates.
2. Regenerate the packet from the previous source of truth.
3. Re-run governance checks.

## No-go
- no runtime implementation hidden inside the audit
- no percentage closure claims without seam-level evidence
- no claim that the new core is healthy without checking for reproduction of old multi-owner behavior
- no continuation into boundary or semantic implementation before the verdict is published

## Risks / blockers
- some verdict sections will necessarily include inference from repo evidence; these must be labeled as inference, not fact
- the audit may reveal that some current new-core slices need bounded rework, which can invalidate the previously queued boundary plan
- the repo still lacks full realism evidence for the migrated behavior, so the behavior-evidence gap section may remain intentionally incomplete

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - boundary-owner implementation is deferred by one stop-the-line audit block
  - continuity remains incomplete and blocked at frozen `pending.py`
  - proof-path and multi-pack acceptance remain incomplete
- **Why not in this block:**
  - this block is specifically about truthfully deciding whether the current direction should continue, be reworked, or be partially deleted before more code changes
- **Risk if deferred:**
  - further implementation may compound the wrong architecture shape or overstate progress
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-restore-blocker-audit-after-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
  - `TP-2026-03-17-consultant-core-boundary-owner-audit-a922` (to be authored if verdict is `continue`)
  - `TP-2026-03-17-consultant-core-bounded-rework-decision-a922` (to be authored if verdict is `bounded rework`)
- **Expiry/trigger to stop deferral:**
  - before any new consultant-core runtime implementation block starts in this worktree

## Next-block contract (mandatory)
- **Next block objective:** publish the post-audit verdict and then either author the boundary-owner audit or a bounded-rework TP, depending on the report verdict
- **First deterministic check command:** `rg -n "Verdict summary|Master-block truth table|Authority deletion ledger|Old-architecture reproduction checklist|Behavior evidence gap map" docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- **Blocked-by conditions:** missing factual evidence for a verdict, or audit finding that one or more new-core slices should be deleted/reworked before any next owner cutover
- **Owner role for closure:** `Top Architect`
