# TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-RESIDUAL-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-TIMEOUT-POST-WAIVER-AUDIT-A922`, `CONSULTANT-CORE-TIMEOUT-OWNER-BROADER-REWORK-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded freeze-waived deletion for the pending-timeout branch. This block targets only the inline pending-timeout state/meta/send authority in frozen `decision.py`, moving it behind the existing timeout-owner helper while leaving `_derive_pending_booking_resume_boundary_payload(...)` and broader pending lifecycle authority explicit residual debt.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/timeout_owner_boundary_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
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
  - `rg -n "pending_soft_pass_timeout_booking_resume_boundary|provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve|timeout_booking_interrupt_resume_boundary_bypasses_exhausted_limit|timeout_owner_boundary_source" truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - the pending-timeout branch at `truffles-api/app/routers/webhook/decision.py:15158-15318` still owns inline booking-state write, expected-reply sync, canonical dialog-state sync, session-memory interaction sync, trace/meta updates, send/result-message assembly, and return.
  - that branch already consumes the same typed `TimeoutOwnerBoundaryResolution` contract as the helper-owned main timeout-owner path.
  - the existing helper already accepts the two largest branch-specific pivots needed for pending-timeout reuse: `boundary_state_source` and `pending_question_contract`.
  - the remaining pending-timeout-only delta is bounded to pending soft-pass metadata and a pending-specific result-message string.
  - `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8557` remains frozen reused derivation authority and is shared with other pending-resume paths.
- `Detected drift (docs vs code)`:
  - Block N proved the next honest move is implementation, but current helper does not yet expose the small pending-specific metadata/result-message hooks needed to delete the pending inline body without duplicating logic again.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Branch by Abstraction"`
- **Date/time (local):** `2026-03-17 20:13 +0500`
- **Why this query is precise:** this block needs one bounded migration pattern for deleting a second inline client branch by routing it through an existing helper while preserving a small branch-specific delta as explicit parameters.
- **Sources opened (from this query):**
  - `Branch By Abstraction` — `https://martinfowler.com/bliki/BranchByAbstraction.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** a bounded migration is valid when the old client body is reduced to a thin callsite against the extracted abstraction and the branch-specific delta is expressed explicitly rather than kept as a second live body.
- **Decision:** `reuse/integrate` — extend the existing timeout-owner helper just enough to carry pending-specific metadata/result-message behavior, then delete the pending inline apply/send body from frozen `decision.py`.
- **Rejected options:**
  - build a second timeout-owner helper for pending only
  - broaden the block to delete `_derive_pending_booking_resume_boundary_payload(...)`
  - reopen a non-frozen bypass claim from `reasoning_core`

## Root cause (mandatory)
- **Symptom:** after Block N, the next seam is known, but the pending-timeout branch still keeps a full inline authority body in frozen `decision.py` even though the main timeout-owner branch has already moved behind `apply_timeout_owner_boundary_resolution(...)`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:15158-15318` and confirm the pending-timeout branch still performs inline state/meta/send authority.
  2. inspect `truffles-api/app/routers/webhook/decision.py:15623` and confirm the main timeout-owner branch already exits through the helper.
  3. inspect `truffles-api/app/services/timeout_owner_boundary_service.py:65` and confirm the helper already owns the shared apply/send authority shape.
  4. compare the pending-timeout branch-specific delta: pending soft-pass metadata, `boundary_state.source="pending_handoff"`, and a pending-specific result-message string.
- **Evidence to capture:**
  - the reduced frozen callsite for pending-timeout
  - helper support for pending-specific metadata/result-message behavior
  - preserved deterministic behavior for pending soft-pass and existing main/resolved timeout-owner regressions
  - explicit residual debt for pending derivation/helper reuse
- **Five Whys (or equivalent):**
  1. Why is another implementation block admissible? Because Block N proved the pending-timeout branch is a repeated inline authority pattern, not a broader rework in disguise.
  2. Why is helper reuse truthful here? Because the old inline body can become deleted or reduced to bounded invocation.
  3. Why is the scope still narrow? Because the derivation helper and broader pending lifecycle ownership stay explicit residual debt.
  4. Why not start broader pending-resume work now? Because that would exceed the proven residual seam and mix timeout-owner progress with continuity rework.
  5. Why is a frozen waiver still needed? Because the remaining old authority body still sits in frozen `decision.py`.
- **Root cause statement:** the main timeout-owner branch was already extracted, but the structurally similar pending-timeout branch still keeps a second live inline authority body in frozen `decision.py`. The truthful next step is not broader rework; it is deleting that second inline body by extending the existing helper just enough to preserve the pending-specific delta explicitly.
- **Fix mechanism:**
  - extend `apply_timeout_owner_boundary_resolution(...)` with narrow pending-specific metadata/result-message inputs
  - replace the pending-timeout inline apply/send body in `decision.py` with one bounded helper invocation
  - keep `_derive_pending_booking_resume_boundary_payload(...)` and broader pending lifecycle seams explicit residual debt

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the pending-timeout inline authority at `truffles-api/app/routers/webhook/decision.py:15158-15318`.
- **FACT:** this block does **not** claim deletion of `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8557`.
- **FACT:** this block does **not** claim deletion of broader pending-resume snapshot/restore authority in `truffles-api/app/routers/webhook/pending.py`.
- **INFERENCE:** the block is admissible because deleting the inline pending-timeout apply/send body removes a second live timeout-owner authority cluster instead of adding another wrapper-only layer.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `app.services.timeout_owner_boundary_service.apply_timeout_owner_boundary_resolution`
  - `app.services.owner_resolver.resolve_timeout_owner_boundary`
  - `_derive_pending_booking_resume_boundary_payload(...)` as explicit reused residual input producer
  - existing timeout-owner endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Branch By Abstraction`
- **Why not reinvent the wheel:** the repo already has the helper, the resolver contract, and the pending derivation helper; the missing work is only deleting the second inline apply/send body and expressing its small branch-specific delta explicitly.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-pending-timeout-boundary`
- **Why this profile fits:** this is a real runtime change with a bounded frozen-file waiver and matching canon/test updates.

## Invariant
- no claim of deleting pending derivation authority
- no new semantic hardcode families
- no broader pending lifecycle rewrite
- main timeout-owner helper behavior must remain stable for existing non-pending regressions

## Scope
- freeze-waived edit for the pending-timeout inline authority seam in `decision.py`
- narrow helper extension for pending-specific metadata/result-message behavior
- targeted deterministic regressions for pending soft-pass and existing timeout-owner paths
- canon/session/state sync after implementation

## Out of scope
- `_derive_pending_booking_resume_boundary_payload(...)` deletion
- `pending.py` work
- broader timeout-owner rework
- tool-reply boundary work
- multi-pack closure work

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Extend the existing timeout-owner helper with explicit pending-specific metadata/result-message controls.
2. Replace the pending-timeout inline authority body in `decision.py` with a bounded helper invocation.
3. Record the new scoped frozen-file waiver lines in `docs/LEGACY_SUNSET.yaml`.
4. Prove pending soft-pass and existing timeout-owner regressions stay green.
5. Sync canon/session/state and rerun governance checks.

## DoD
- the old pending-timeout inline authority body in `truffles-api/app/routers/webhook/decision.py:15158-15318` is deleted or reduced to bounded helper invocation only
- `truffles-api/app/services/timeout_owner_boundary_service.py` owns pending-timeout state/meta/send behavior together with the existing main branch behavior
- pending soft-pass deterministic behavior stays green
- existing main/resolved timeout-owner deterministic behavior stays green
- `_derive_pending_booking_resume_boundary_payload(...)` remains explicit residual debt and is not over-claimed as deleted
- required governance checks are green

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve or timeout_booking_interrupt_resume_boundary_bypasses_exhausted_limit'`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reduced pending-timeout frozen callsite
- helper support for pending-specific metadata/result-message behavior
- deterministic timeout-owner regression evidence
- updated canon/session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted deterministic timeout-owner tests only
- **Stop condition:** if the diff starts pulling `_derive_pending_booking_resume_boundary_payload(...)`, `pending.py`, or broader pending lifecycle ownership into scope, stop and open the broader rework decision instead of growing this block
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded freeze-waived runtime change with deterministic closure before any rollout
- **Go/no-go signals:**
  - pending-timeout inline authority body is deleted or reduced to bounded helper invocation only
  - pending soft-pass and existing timeout-owner deterministic tests stay green
  - final metadata/trace still preserve `pending_guard`, `pending_action`, `pending_handoff_resume_boundary`, and `timeout_owner_boundary_source`
- **Rollback:** revert the helper extension, the reduced frozen callsite, and the matching waiver lines, then rerun targeted timeout-owner tests and governance checks
- **Post-release monitoring window:** first pending soft-pass timeout conversations must preserve pending-specific metadata plus timeout-owner recovery evidence without reopening the old inline authority body

## Rollback
1. Revert the helper extension and the pending-timeout frozen callsite reduction.
2. Restore `docs/LEGACY_SUNSET.yaml` waiver scope to the previous Block L lines only.
3. Regenerate the packet and rerun targeted tests plus governance checks.

## No-go
- no deletion claim for `_derive_pending_booking_resume_boundary_payload(...)`
- no `pending.py` edits
- no second pending-only helper
- no non-frozen bypass claim from `reasoning_core`

## Risks / blockers
- pending-specific metadata may need a slightly richer helper input surface than currently expected
- result-message parity may require a dedicated helper message override rather than a simple source reuse
- any attempt to absorb broader pending lifecycle ownership would invalidate this block

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `_derive_pending_booking_resume_boundary_payload(...)` remains frozen reused derivation authority
  - broader pending-resume snapshot/restore authority remains outside this seam
  - other timeout-owner residuals still require follow-up after this block
- **Why not in this block:**
  - this block is only the narrow pending-timeout inline authority deletion
- **Risk if deferred:**
  - a second live timeout-owner inline authority body would remain in frozen legacy even after the main branch extraction
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-timeout-post-waiver-audit-a922`
  - `TP-2026-03-17-consultant-core-timeout-owner-broader-rework-decision-a922`
- **Expiry/trigger to stop deferral:**
  - before any claim that the pending-timeout family is fully removed

## Next-block contract (mandatory)
- **Next block objective:** run a post-waiver audit for the pending-timeout seam and decide whether the next surviving timeout-owner authority is broader rework or another bounded residual cut
- **First deterministic check command:** `rg -n "pending_timeout_boundary_resolution|apply_timeout_owner_boundary_resolution|_derive_pending_booking_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py`
- **Blocked-by conditions:** if the implementation requires deleting or rewriting reused pending derivation logic, `pending.py`, or broader pending lifecycle ownership, stop and open the broader rework decision instead of continuing
- **Owner role for closure:** `Top Architect`
