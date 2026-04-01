# TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-RESIDUAL-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TIMEOUT-OWNER-POST-WAIVER-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-timeout-owner-post-waiver-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-FROZEN-WAIVER-IMPLEMENTATION-A922`, `CONSULTANT-CORE-TIMEOUT-OWNER-BROADER-REWORK-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the residual seam audit for the pending-timeout branch after Block M. This block must prove whether the inline pending-timeout state/meta/send authority in frozen `decision.py` is narrow enough to become the next real deletion target, and must reject the move if it would drag pending-resume derivation or broader pending lifecycle authority into scope.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-timeout-owner-post-waiver-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before audit closure)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '15154,15318p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15439,15623p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1,220p' truffles-api/app/services/timeout_owner_boundary_service.py`
  - `sed -n '8557,8665p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "pending_soft_pass_timeout_booking_resume_boundary|provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve|timeout_owner_boundary_source" truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - the pending-timeout branch at `truffles-api/app/routers/webhook/decision.py:15158-15318` still owns inline booking-state write, expected-reply sync, canonical dialog-state sync, session-memory interaction sync, trace/meta updates, send/result-message assembly, and return.
  - that branch already consumes the same typed `resolve_timeout_owner_boundary(...)` output as the helper-owned main branch.
  - the branch-specific delta versus `apply_timeout_owner_boundary_resolution(...)` is narrow: `boundary_state.source="pending_handoff"`, pending soft-pass metadata fields, and a pending-specific result-message string.
  - pending-timeout input derivation is still frozen in `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8557`, and that derivation helper is reused by other pending-resume paths outside the timeout branch.
  - existing deterministic coverage already proves the pending-timeout timeout-resume boundary behavior and the resolved-handoff timeout-resume boundary behavior in `truffles-api/tests/test_message_endpoint.py`.
- `INFERENCE to verify in this block`:
  - the pending-timeout inline apply/send cluster is likely the next real deletable seam, but only if the next block can reduce `decision.py:15158-15318` to bounded helper invocation without claiming deletion of the reused pending-resume derivation helper.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change"`
- **Date/time (local):** `2026-03-17 20:09 +0500`
- **Why this query is precise:** this residual audit needs one external migration rule for deciding whether the pending-timeout branch can be moved by a small parallel change that retires the old branch instead of creating another long-lived dual path.
- **Sources opened (from this query):**
  - `Parallel Change` — `https://martinfowler.com/bliki/ParallelChange.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** a migration step is healthy when the old path is retired after the new path is proven, not when both paths stay live indefinitely.
- **Decision:** `reuse/integrate` — treat the pending-timeout branch as admissible only if the next block can delete its inline authority body and keep the reused pending derivation helper explicit as residual debt.
- **Rejected options:**
  - jump directly into a broad pending-resume rewrite
  - count helper reuse as progress while the old inline pending-timeout authority stays live
  - claim deletion of `_derive_pending_booking_resume_boundary_payload(...)` in the same block

## Root cause (mandatory)
- **Symptom:** Block M proved that the pending-timeout branch is structurally close to the helper-owned main timeout-owner path, but the repo still lacks one explicit verdict on whether that branch is a real next deletion target or whether it drags too much pending-resume lifecycle authority with it.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:15158-15318` and confirm the pending-timeout branch still performs inline state/meta/send authority.
  2. inspect `truffles-api/app/routers/webhook/decision.py:15623` and confirm the main timeout-owner branch already exits through `apply_timeout_owner_boundary_resolution(...)`.
  3. inspect `truffles-api/app/services/timeout_owner_boundary_service.py:65` and confirm the helper already owns the main branch apply/send authority.
  4. inspect `truffles-api/app/routers/webhook/decision.py:8557` and confirm pending-timeout derivation still lives in a reused frozen helper.
- **Evidence to capture:**
  - exact overlap between pending-timeout inline authority and the existing helper-owned main branch
  - exact branch-specific delta that would remain if the inline apply/send authority is extracted
  - whether the reused pending derivation helper can stay explicit residual debt
  - whether the next honest block is a bounded freeze-waived implementation or a broader rework decision
- **Five Whys (or equivalent):**
  1. Why is another verdict needed after Block M? Because Block M only proved that pending-timeout is the likely next seam, not that its unique pending-specific delta is still bounded enough.
  2. Why is the branch still a candidate? Because it already consumes the same typed resolver output and repeats the same authority pattern the helper now owns for the main branch.
  3. Why is it not automatic? Because the branch also touches pending soft-pass metadata and sits near reused pending-resume derivation logic.
  4. Why is that a risk? Because the program could accidentally claim a small deletion while actually reopening broader pending lifecycle ownership.
  5. Why is this block admissible? Because it decides whether one more old inline authority body can die without widening the waiver scope beyond the residual seam.
- **Root cause statement:** Block M narrowed the next candidate correctly, but the pending-timeout branch still needs one residual audit because it combines a clearly repeated inline apply/send cluster with nearby reused pending-resume derivation logic. Without this audit, the program could over-claim a narrow deletion that actually expands into broader pending lifecycle rework.
- **Fix mechanism:**
  - compare the pending-timeout branch line-by-line against the helper-owned main branch
  - isolate the truly repeated inline apply/send authority from the reused pending derivation helper
  - publish one verdict: bounded implementation admissible, or broader rework required

## Old authority seams under audit (mandatory)
- **FACT:** pending-timeout inline authority still lives at `truffles-api/app/routers/webhook/decision.py:15158-15318`.
- **FACT:** reused pending-resume derivation still lives at `truffles-api/app/routers/webhook/decision.py:8557`.
- **FACT:** the helper-owned main timeout-owner apply/send authority already lives at `truffles-api/app/services/timeout_owner_boundary_service.py:65`.
- **FACT:** this block does not audit the broader pending-resume snapshot/restore authority in frozen `pending.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `app.services.timeout_owner_boundary_service.apply_timeout_owner_boundary_resolution`
  - `app.services.owner_resolver.resolve_timeout_owner_boundary`
  - `_derive_pending_booking_resume_boundary_payload(...)` as an explicit reused residual helper
  - existing deterministic timeout-owner endpoint tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
- **Why not reinvent the wheel:** the repo already has the helper, the resolver contract, the pending derivation helper, and deterministic coverage; this block only has to prove whether the old inline branch can be reduced to those existing pieces without broadening scope.

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `9`
- **Code dominance:** `docs`
- **Why this profile fits:** this is a residual seam classification block; it should select the next truthful runtime move without changing runtime code.

## Invariant
- no runtime implementation in this block
- no claim that pending-timeout derivation is deleted
- no broad pending lifecycle rewrite hidden behind a timeout-owner label
- no helper-growth counted as progress without old inline authority deletion

## Scope
- audit the pending-timeout inline authority after Block M
- compare it against the existing helper-owned main branch
- decide whether the next block can be a bounded freeze-waived implementation
- sync canon/session artifacts to the residual audit block

## Out of scope
- pending-timeout implementation
- broader pending-resume rewrite
- `pending.py` changes
- tool-reply boundary work
- multi-pack closure work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Compare the pending-timeout inline branch against the helper-owned main branch.
2. Separate repeated apply/send authority from reused pending derivation logic.
3. Decide whether one bounded implementation block can delete the inline branch body.
4. Lock one machine-readable next move in canon.

## DoD
- the residual audit states explicitly whether the pending-timeout branch is the next real deletable seam
- the audit names the exact residuals that remain out of scope if that seam is selected
- canon moves to the pending-timeout residual audit block with one machine-readable next move
- no runtime progress is overstated beyond the already-proven Block L deletion

## Checks
- `sed -n '15154,15318p' truffles-api/app/routers/webhook/decision.py`
- `sed -n '15439,15623p' truffles-api/app/routers/webhook/decision.py`
- `sed -n '1,220p' truffles-api/app/services/timeout_owner_boundary_service.py`
- `rg -n "pending_soft_pass_timeout_booking_resume_boundary|provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve|timeout_owner_boundary_source" truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- explicit overlap map between the pending-timeout branch and the helper-owned main branch
- explicit residual map for reused pending derivation authority
- updated canon/session artifacts for the residual audit block
- green governance checks after the canon move

## Rollback
1. Revert the residual-audit TP and canon/session updates.
2. Regenerate the agent packet.
3. Re-run architecture/governance checks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc-only seam classification plus governance checks
- **Stop condition:** if the audit proves the pending-timeout branch cannot be isolated from broader pending lifecycle authority, stop and author the broader rework decision instead of an implementation TP.
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only residual audit; no runtime rollout
- **Go/no-go signals:** residual seam classification completed; packet and governance checks green
- **Rollback:** revert audit docs/canon sync and regenerate packet
- **Post-release monitoring window:** the next implementation block must stay inside the residual seam proved here and must not claim derivation or broader pending lifecycle deletion

## No-go
- no pending-timeout implementation in this block
- no new frozen-file waiver beyond the already-approved Block L scope
- no claim that `_derive_pending_booking_resume_boundary_payload(...)` is deleted
- no jump to broader pending-resume rewrite without explicit verdict

## Risks / blockers
- the branch-specific pending soft-pass metadata may hide more live authority than the helper currently owns
- reused pending derivation logic may prove too entangled for a narrow next block
- current deterministic tests may prove the branch behavior but still leave exact result-message parity as a follow-up contract for implementation

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - pending-timeout inline state/meta/send authority remains live
  - `_derive_pending_booking_resume_boundary_payload(...)` remains frozen reused derivation authority
  - broader pending-resume snapshot/restore authority remains frozen outside this track
- **Why not in this block:**
  - this block is residual classification only and must not blur into runtime implementation
- **Risk if deferred:**
  - the program can mis-size the next timeout-owner step and reopen broader pending lifecycle scope under a narrow label
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922`
  - `TP-2026-03-17-consultant-core-timeout-owner-broader-rework-decision-a922`
- **Expiry/trigger to stop deferral:**
  - before any next timeout-owner implementation claim

## Next-block contract (mandatory)
- **Next block objective:** if this residual audit proves the pending-timeout branch can be reduced to bounded helper invocation while leaving pending derivation explicit as residual debt, author `TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922`; otherwise author `TP-2026-03-17-consultant-core-timeout-owner-broader-rework-decision-a922`.
- **First deterministic check command:** `rg -n "pending_timeout_boundary_resolution|apply_timeout_owner_boundary_resolution|_derive_pending_booking_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py`
- **Blocked-by conditions:** if the pending-timeout branch cannot be isolated from reused pending derivation authority or if the required diff would exceed the already-bounded timeout-owner residual seam, stop and open the broader rework decision instead of implementation.
- **Owner role for closure:** `Top Architect`
