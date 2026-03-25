# TP-2026-03-17-consultant-core-timeout-owner-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TIMEOUT-OWNER-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FROZEN-BOUNDARY-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TIMEOUT-OWNER-POST-WAIVER-AUDIT-A922`, `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-RESIDUAL-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded freeze-waived deletion inside the timeout-owner family. This block targets only the main timeout-owner state/meta/send assembly in frozen `decision.py`, moving that authority into a non-frozen helper while keeping the still-frozen input derivation and pending-timeout branch explicit as residual debt.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_owner_resolver.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-timeout-owner-frozen-waiver-implementation-a922.md`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/timeout_owner_boundary_service.py`
  - `truffles-api/app/services/owner_resolver.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_owner_resolver.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '15593,15766p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15154,15318p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '230,339p' truffles-api/app/services/owner_resolver.py`
  - `sed -n '2329,2538p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '381,450p' truffles-api/app/core/turn_executor.py`
  - `rg -n "timeout_owner_boundary" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_owner_resolver.py`
- `FACT findings`:
  - the main frozen timeout-owner authority seam lives at `truffles-api/app/routers/webhook/decision.py:15610`, where the router writes booking state, expected-reply context, canonical dialog state, session-memory interaction state, policy-guard override, trace/meta evidence, send/commit, and returns the response.
  - the pending timeout boundary branch at `truffles-api/app/routers/webhook/decision.py:15154` is separate and still live; it must remain residual in this block.
  - `resolve_timeout_owner_boundary(...)` already returns a typed `TimeoutOwnerBoundaryResolution` in `truffles-api/app/services/owner_resolver.py:302`.
  - non-frozen `reasoning_core` already has one reusable owner-cutover finalizer at `truffles-api/app/services/reasoning_core.py:2329`, and typed owner artifacts already exist in `truffles-api/app/core/turn_executor.py:381`.
  - existing targeted runtime coverage already exists for timeout-owner matched-expected-reply and resume-contract paths in `truffles-api/tests/test_message_endpoint.py` and pure resolver coverage exists in `truffles-api/tests/test_owner_resolver.py`.
- `Detected drift (docs vs code)`:
  - the waiver decision proved a non-frozen bypass from `reasoning_core` is not yet truthful, but it did not yet define which frozen timeout-owner seam is small enough to delete safely under waiver. This TP narrows that to the main state/meta/send assembly only.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Branch by Abstraction"`
- **Date/time (local):** `2026-03-17 19:18 +0500`
- **Why this query is precise:** this block needs one bounded migration pattern for moving a live frozen authority block behind a new helper without claiming that the whole family is already gone.
- **Sources opened (from this query):**
  - `Branch By Abstraction` — `https://martinfowler.com/bliki/BranchByAbstraction.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** a bounded migration can delete one supplier block by introducing an abstraction used by the current client, moving the implementation behind it, and deleting the old supplier body only for the selected sub-component.
- **Decision:** `reuse/integrate` — move only the main timeout-owner state/meta/send assembly behind a non-frozen helper, keep the callsite bounded, and do not claim full timeout-family deletion.
- **Rejected options:**
  - attempt a full timeout-owner family rewrite in one block
  - claim `reasoning_core` bypass when the input contract still lives in frozen `decision.py`
  - move pending-timeout and main-timeout branches together without first proving they share a safe bounded seam
- **Open questions:** whether `owner_resolver.py` needs any small request/result extension once the non-frozen helper request shape is drafted.

## Root cause (mandatory)
- **Symptom:** after Block K, the program had a truthful waiver decision but still lacked one bounded implementation target inside the frozen timeout-owner family.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:15610` and confirm the main timeout-owner branch still owns state/meta/send authority.
  2. inspect `truffles-api/app/routers/webhook/decision.py:15154` and confirm the pending-timeout branch is separate and still live.
  3. inspect `truffles-api/app/services/owner_resolver.py:302` and confirm the typed resolution payload already exists.
  4. inspect `truffles-api/app/services/reasoning_core.py:2329` and `truffles-api/app/core/turn_executor.py:381` and confirm the repo already has reusable non-frozen owner-finalization patterns.
- **Evidence to capture:**
  - exact old authority seam selected for deletion
  - exact timeout-owner residuals left out of scope
  - reuse surfaces for the new helper
  - targeted tests that prove the selected seam still behaves the same after the move
- **Five Whys (or equivalent):**
  1. Why is another non-frozen bypass block not admissible? Because the timeout-owner input contract still lives in frozen `decision.py`.
  2. Why can work still continue? Because one narrower authority seam inside the frozen family is separable: the main state/meta/send assembly.
  3. Why pick that seam? Because it is large, behavior-rich, and already consumes a typed `TimeoutOwnerBoundaryResolution` payload.
  4. Why leave the pending-timeout branch out? Because it is a second live branch and would enlarge the waiver scope beyond the first bounded deletion.
  5. Why is this still progress? Because the old main assembly body in `decision.py` becomes deleted or reduced to a bounded callsite, rather than merely wrapped.
- **Root cause statement:** Block K stopped speculative bypass work correctly, but the next implementation move still needed a smaller target. The real bounded deletion is not the whole timeout-owner family; it is the main `decision.py:15610-15766` state/meta/send assembly that already consumes a typed resolver output and can move behind one non-frozen helper without pretending the still-frozen input derivation or pending-timeout branch are gone.
- **Fix mechanism:**
  - introduce one non-frozen timeout-owner helper for the main branch only
  - replace the main frozen assembly body with a bounded call into that helper
  - keep pending-timeout and derivation seams explicit as residual debt
  - prove matched-expected-reply and resume-contract behavior stays stable with targeted tests

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the main timeout-owner assembly at `truffles-api/app/routers/webhook/decision.py:15610-15766`.
- **FACT:** this block does **not** claim deletion of the input-derivation surface at `truffles-api/app/routers/webhook/decision.py:11072`, `truffles-api/app/routers/webhook/decision.py:15435`, and `truffles-api/app/routers/webhook/decision.py:15535`.
- **FACT:** this block does **not** claim deletion of the pending-timeout branch at `truffles-api/app/routers/webhook/decision.py:15154-15318`.
- **INFERENCE:** the bounded implementation is admissible because deleting the main state/meta/send assembly changes which code owns the boundary contract, even though other timeout-owner residuals remain.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `app.services.owner_resolver.TimeoutOwnerBoundaryResolution`
  - `app.core.dialog_state_service.DialogStateService`
  - `app.core.turn_executor.TurnExecutor`
  - existing owner-cutover finalization patterns in `truffles-api/app/services/reasoning_core.py`
  - existing timeout-owner endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
  - existing pure resolver coverage in `truffles-api/tests/test_owner_resolver.py`
- **External reuse:**
  - Martin Fowler `Branch By Abstraction`
- **Why not reinvent the wheel:** the repo already has typed resolution, dialog-state, and owner-outcome building blocks; the missing step is wiring one bounded frozen authority seam into them.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-timeout-owner-main-assembly`
- **Why this profile fits:** the block is a real runtime change with a bounded frozen-file waiver and matching canon/test updates.

## Invariant
- No new semantic hardcode families.
- No claim of full timeout-owner family deletion.
- Pending-timeout branch remains untouched unless the implementation proves it was not modified.
- `reasoning_core` is not allowed to clone broad timeout derivation logic in this block.

## Scope
- freeze-waived edit for the main timeout-owner assembly seam in `truffles-api/app/routers/webhook/decision.py`
- one non-frozen helper/service that owns the main branch state/meta/send assembly
- targeted matched-expected-reply and resume-contract regressions
- canon/session/state sync after implementation

## Out of scope
- `reasoning_core` timeout-owner bypass
- pending-timeout boundary branch at `truffles-api/app/routers/webhook/decision.py:15154-15318`
- tool-reply `TurnOutcome` path
- pending-resume derivation authority
- multi-pack closure work

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_owner_resolver.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-timeout-owner-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one non-frozen timeout-owner helper request/result surface for the main branch only.
2. Move the main timeout-owner state/meta/send assembly from `decision.py:15610-15766` into that helper.
3. Reduce the frozen callsite to bounded derivation plus helper invocation.
4. Prove matched-expected-reply and resume-contract paths stay stable with targeted tests.
5. Sync canon/session/state and rerun governance checks.

## DoD
- the old main timeout-owner assembly body is deleted from `truffles-api/app/routers/webhook/decision.py:15610-15766` or reduced to a bounded helper invocation with no duplicate state/meta/send authority left there
- one non-frozen helper owns booking state write, expected-reply sync, canonical dialog-state sync, session-memory interaction sync, policy-guard override, trace/meta updates, and send/commit/return for the main timeout-owner branch
- targeted matched-expected-reply and resume-contract tests are green
- pending-timeout branch remains residual and explicitly unclaimed
- required governance checks are green

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/app/services/owner_resolver.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_owner_resolver.py`
- `pytest -q truffles-api/tests/test_owner_resolver.py -k "timeout_owner_boundary"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "timeout_owner_boundary and (matched_expected_reply or resume_contract)"`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- the new helper implementation and reduced frozen callsite
- targeted timeout-owner endpoint/resolver tests
- updated canon/session/state artifacts
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted timeout-owner deterministic tests only
- **Stop condition:** if the change starts pulling pending-timeout or broad derivation logic into scope, stop and reopen a broader rework decision instead of growing this waiver block
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded freeze-waived runtime change with local deterministic closure before any rollout; deploy only after matched-expected-reply and resume-contract timeout-owner traces/meta remain stable on canary traffic
- **Go/no-go signals:**
  - old main assembly body in `decision.py` is deleted or reduced to bounded invocation only
  - targeted timeout-owner tests stay green
  - final trace/meta still show the same timeout-owner recovery contract for matched-expected-reply and resume-contract paths
- **Rollback:** revert the bounded helper and the matching frozen callsite reduction, then rerun targeted timeout-owner tests and governance checks
- **Post-release monitoring window:** first canary conversations that hit timeout-owner matched-expected-reply and resume-contract paths must preserve `reason_code`, `expected_reply_reason`, `timeout_owner_boundary_source`, and transport/send outcome

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
  - canon must describe the deleted main seam and the still-live residual timeout-owner seams separately.

## Rollback
1. Revert the bounded helper and frozen callsite reduction.
2. Re-run the targeted timeout-owner tests.
3. Revert canon/session/state updates if the runtime rollback is accepted.

## No-go
- no broad timeout-family rewrite
- no reasoning-core clone of timeout derivation logic
- no claim that pending-timeout branch or derivation seams are deleted in this block
- no wrapper-only helper that leaves the old main state/meta/send body effectively intact

## Risks / blockers
- the helper boundary may need one small request/result type addition before code compiles cleanly
- if the frozen callsite still owns significant state/meta/send logic after refactor, the block fails the deletion test
- existing endpoint coverage may need one extra assertion if behavior shifts from inline metadata ordering to helper-owned ordering

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - timeout-owner input derivation remains frozen
  - pending-timeout branch remains frozen and live
  - tool-reply boundary authority remains frozen and live
- **Why not in this block:**
  - the waiver scope is intentionally bounded to the main timeout-owner assembly seam only
- **Risk if deferred:**
  - the repo may confuse a partial timeout-owner deletion with full boundary closure
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-timeout-owner-post-waiver-audit-a922` (to be authored after implementation)
  - `TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922` (to be authored if the pending branch remains the next surviving seam)
- **Expiry/trigger to stop deferral:**
  - before any claim that timeout-owner boundary ownership is complete

## Next-block contract (mandatory)
- **Next block objective:** after the bounded waiver implementation lands, audit the remaining timeout-owner residuals and decide whether the pending-timeout branch or another boundary seam is the next admissible target
- **First deterministic check command:** `rg -n "pending_timeout_boundary_resolution|timeout_owner_boundary_resolution|timeout_owner_boundary_source" truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- **Blocked-by conditions:** if the old main assembly body is not actually deleted, or the change expands into pending-timeout scope, stop and reopen a broader rework decision
- **Owner role for closure:** `Top Architect`
