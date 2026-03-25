# TP-2026-03-17-consultant-core-pending-resume-activation-preserve-broader-rework-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-BROADER-REWORK-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-REWORK-PLAN-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one post-waiver decision block after the pending-resume helper-family deletion. The goal is to classify the remaining `decision.py` activation/preserve cluster truthfully and decide whether the next move is still one bounded deletion path or a broader owner-capture rework plan.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before decision)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-broader-rework-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "def _build_pending_resume_snapshot|def _restore_pending_resume" truffles-api/app/routers/webhook/pending.py`
  - `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|pending_handoff_resume_boundary|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10620,10720p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '14950,15020p' truffles-api/app/routers/webhook/decision.py`
  - `pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `FACT findings`:
  - frozen `pending.py` no longer defines `_build_pending_resume_snapshot(...)` or `_restore_pending_resume(...)`; the pending-ack path now calls `app.services.state_service._restore_pending_resume_payload(...)` directly.
  - pending-resume reason derivation, boundary payload derivation, and restore preparation now live in `DialogStateService` plus `state_service`.
  - the surviving live authority is the inline activation/preserve cluster in frozen `truffles-api/app/routers/webhook/decision.py`:
    - activation and optional restore/re-derive: `truffles-api/app/routers/webhook/decision.py:10627`
    - session-memory preserve vs reset handoff decision: `truffles-api/app/routers/webhook/decision.py:10677`
    - pending-timeout fallback reuse of the same boundary contract: `truffles-api/app/routers/webhook/decision.py:14964`
  - this surviving cluster no longer owns the underlying pending-resume contract internals, but it still decides whether the boundary is active, whether handover state is restored on soft-pass, whether session memory is preserved, and whether timeout fallback can reuse the boundary contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" residual seam audit`
- **Date/time (local):** `2026-03-17 21:37 +0500`
- **Why this query is precise:** the remaining problem is no longer an isolated helper body; it is a residual authority seam after partial migration, so the correct decision is whether to continue bounded change or stop for broader convergence planning.
- **Sources opened (from this query):**
  - `Parallel Change` — `https://martinfowler.com/bliki/ParallelChange.html`
- **Source quality:** primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** after one side of a split contract already owns the internals, the next truthful move is to classify whether the remaining coordinator code is still a real deletable seam or whether it has become a broader residual that needs a new convergence plan.
- **Decision:** `reuse/integrate` — reuse the existing `DialogStateService` and `state_service` owner path for any future block; do not invent a new helper family unless the audit proves one bounded deletion path still exists.
- **Rejected options:**
  - another helper-family micro-slice inside `pending.py`
  - continuing implementation by moving coordinator lines around without deleting real authority
  - reopening timeout-owner cuts as if the pending-resume residual were still the same seam family

## Root cause (mandatory)
- **Symptom:** after Block R deleted the pending-resume helper family in `pending.py` and reduced the restore helpers in `decision.py`, one residual inline cluster still decides pending-resume activation, restore/preserve behavior, and timeout-boundary reuse.
- **Minimal reproduction:**
  1. prove `pending.py` helper-family deletion with `rg -n "def _build_pending_resume_snapshot|def _restore_pending_resume" truffles-api/app/routers/webhook/pending.py`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:10627-10709` to confirm `decision.py` still decides when the boundary is active and whether session memory is preserved instead of reset.
  3. inspect `truffles-api/app/routers/webhook/decision.py:14964-15010` to confirm the same residual state gates pending timeout boundary reuse.
  4. inspect `truffles-api/app/services/state_service.py:701-767` to confirm the owner path already supplies the lower-level restore preparation but not the higher-level activation/preserve coordinator.
- **Evidence to capture:**
  - zero-match proof for deleted `pending.py` helper bodies
  - exact residual cluster in `decision.py`
  - endpoint tests still proving `restore_soft_pass`, `pending_handoff_resume_boundary`, and timeout fallback behavior
- **Five Whys (or equivalent):**
  1. Why is pending-resume not fully converged yet? Because `decision.py` still owns the activation/preserve coordinator.
  2. Why not continue the same helper-family slicing? Because the isolated helper bodies are already gone.
  3. Why is the remaining code harder than the previous cuts? Because it mixes continuity restore state, session-memory preserve/reset behavior, and timeout boundary reuse in one inline cluster.
  4. Why does this require a decision instead of blind implementation? Because a naive extraction could just move coordinator code into another wrapper without killing real authority.
  5. Why is a broader rework plan likely? Because the residual cluster now spans continuity owner and boundary owner concerns, not only one helper body.
- **Root cause statement:** Block R successfully deleted the concrete pending-resume helper family, but the remaining live authority is now a coordinator cluster inside frozen `decision.py` that mixes pending boundary activation, session-memory preserve/reset behavior, and timeout-boundary reuse. The old seam is no longer a single helper body; it is a broader residual authority shape.
- **Fix mechanism:** stop micro-slice farming, record the residual cluster as the next truth-bearing target, and require one broader rework plan that names the future owner and the exact deletion path before any more runtime changes.

## Old authority seam to classify (mandatory)
- **FACT:** deleted in Block R:
  - frozen `truffles-api/app/routers/webhook/pending.py` helper bodies `_build_pending_resume_snapshot(...)` and `_restore_pending_resume(...)`
  - redundant legacy pending-ack `re_entry_required` writer
- **FACT:** surviving authority still live:
  - `truffles-api/app/routers/webhook/decision.py:10627-10709`
  - `truffles-api/app/routers/webhook/decision.py:14964-15010`
- **INFERENCE:** the surviving cluster is no longer an equally bounded helper-family seam; it is likely the smallest remaining authority island and needs broader owner-capture planning.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/timeout_owner_boundary_service.py`
  - existing endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
  - existing pending-pack coverage in `truffles-api/tests/test_pending_pack_lexicons.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
- **Why not reinvent the wheel:** the lower-level continuity owner path already exists; the missing piece is classifying whether the remaining coordinator cluster can be converged truthfully without just creating another wrapper.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout in this TP.
- **Go/no-go signals:** go only if canon, packet, and architecture guards stay aligned; no production traffic change is permitted from this block.
- **Rollback:** revert this TP and canon sync if a later runtime scan disproves the Block S verdict.
- **Post-release monitoring window:** not applicable for this doc-only decision block; rely on guard reruns in the same session.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Why:** this block is doc-only and uses only required governance checks, not expensive LLM or long runtime suites.

## Execution profile
- `TP mode`: `decision`
- `Doc touch budget (files)`: `10`
- `Code dominance`: `docs_only`
- `Override token`: `pending-resume-post-waiver-decision`
- `Why this profile fits`: this block should decide the next admissible implementation path, not grow runtime by guesswork.

## Invariant
- no new runtime implementation in this block
- no claim that pending-resume authority is fully converged
- no fake progress by renaming or wrapping the remaining `decision.py` coordinator cluster
- no new semantic hardcode in core or frozen files

## Scope
- classify the surviving pending-resume authority after Block R
- decide whether one more bounded deletion path exists or whether the next truthful move is a broader rework plan
- sync canon and evidence to that verdict

## Out of scope
- runtime implementation
- `booking.py`
- semantic owner work
- proof-path work
- multi-pack closure work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-broader-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Prove the previous helper-family seam is already deleted.
2. Inspect the remaining `decision.py` activation/preserve cluster and classify its real authority.
3. Decide whether the next block is still a bounded deletion path or a broader rework plan.
4. Sync canon to the chosen verdict and rerun governance checks.

## DoD
- one explicit verdict is recorded
- the next machine-readable move is updated
- no runtime files change in this decision block
- canon / packet / architecture test stay consistent

## Checks
- `rg -n "def _build_pending_resume_snapshot|def _restore_pending_resume" truffles-api/app/routers/webhook/pending.py`
- `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|pending_handoff_resume_boundary|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- one verdict recorded in canon
- updated `AGENT_PACKET`
- updated session/state entries

## Rollback
- revert the decision TP and canon sync if the verdict is proven wrong by later code evidence

## No-go
- do not implement a new helper cut in this block
- do not claim the remaining `decision.py` cluster is already thin enough without code proof
- do not reopen `pending.py` helper-family work as if it were still live authority

## Risks / blockers
- the remaining cluster spans continuity and boundary concerns, so a bad implementation block could blur owner boundaries instead of deleting them
- if the future plan cannot name one owner and one deleted seam, the correct status remains `BLOCKED`

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`:
  - frozen `decision.py` still owns pending-resume activation/preserve and timeout-boundary reuse coordination
  - thin pending-resume wrappers still remain in frozen `decision.py`
- `Why not in this block`:
  - this is a decision-only block
  - the remaining residual is no longer a simple helper-body deletion
- `Risk if deferred`:
  - the team may mistake coordinator extraction for real owner deletion
- `Linked follow-up Task Package(s)`:
  - `TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922` (to be authored only if this decision stands)
- `Expiry/trigger to stop deferral`:
  - stop deferral immediately if a future implementation proposal cannot state exactly which old coordinator seam becomes deleted or unreachable

## Next-block contract (mandatory)
- `Next block objective`: author one broader owner-capture rework plan for the surviving pending-resume activation/preserve cluster in frozen `decision.py`
- `First deterministic check command`: `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|pending_handoff_resume_boundary|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
- `Blocked-by conditions`:
  - if the next plan cannot name one future owner for activation/preserve behavior
  - if the proposed next block only introduces another coordinator wrapper
  - if the plan would expand into the whole pending lifecycle instead of the residual cluster
- `Owner role for closure`: `Top Architect`
