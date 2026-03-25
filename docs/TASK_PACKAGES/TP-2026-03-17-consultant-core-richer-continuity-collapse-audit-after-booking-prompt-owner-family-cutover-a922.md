# TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-RICHER-CONTINUITY-COLLAPSE-AUDIT-POST-BOOKING-PROMPT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-NORMAL-PATH-BOOKING-PROMPT-OWNER-FAMILY-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-normal-path-booking-prompt-owner-family-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-MANAGER-EXPECTED-REPLY-STATE-SYNC-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Зафиксировать richer continuity-collapse target после закрытия normal-path `booking_prompt` owner family и не дать программе скатиться в старые micro-bridge continuity slices. Этот блок должен доказательно показать, какие continuity seams уже фактически схлопнуты, какие ещё живы, какой из них реально admissible без frozen-file edits, и обновить canon так, чтобы следующий агент шёл уже в один конкретный implementation block.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-normal-path-booking-prompt-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/pending.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "expected_reply_type|expected_reply_reason|pending_resume|last_question|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
  - `sed -n '228,560p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '831,970p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '590,640p' truffles-api/app/services/state_service.py`
  - `sed -n '111,180p' truffles-api/app/routers/webhook/pending.py`
  - `sed -n '22328,22596p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - the safe normal-path `booking_prompt` family is now exhausted: remaining booking-labelled legacy branches in frozen `decision.py` are mixed recovery/media/boundary/tool-interrupt seams (`policy_core_invalid_schema_specialist_followup`, `policy_core_timeout_specialist_followup`, `collect_reschedule_handoff`, style-sidecar prompt envelopes, and tool-interrupt prompt recovery), so Block D can close honestly instead of farming one more micro-slice
  - `session_memory.py` no longer owns the old live payload shaping seam; question bookkeeping, normalization, freshness, and interaction-state sync already delegate to `DialogStateService`
  - `state_service.py` already uses `DialogStateService.capture_pending_resume_payload(...)` and `DialogStateService.restore_pending_resume_payload(...)`, so a `state_service`-only follow-up would not delete a new live writer authority
  - frozen `pending.py` still owns direct `_build_pending_resume_snapshot(...)` and `_restore_pending_resume(...)`, so pending-resume restore remains a high-value continuity seam but is blocked for the immediate next block by the frozen-file constraint
  - `context_manager.py::_set_expected_reply_context(...)` remains the richest non-frozen continuity seam because it still writes expected-reply fields, canonical dialog-state sync, session-memory interaction-state sync, re-entry clear, and question bookkeeping orchestration as one live authority outside `DialogStateService`
- `Detected drift (docs vs code)`:
  - canon still names Block D as active even though the closure audit now shows no remaining pure normal-path `booking_prompt` seam and the next admissible move has shifted to continuity collapse

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "single source of truth" "source code"`
- **Date/time (local):** `2026-03-17 17:20 +0500`
- **Why this query is precise:** the audit must choose the next continuity block by identifying the one place that should become the authoritative writer instead of letting multiple wrappers keep shaping the same state.
- **Sources opened (from this query):**
  - `Research, Review, Rebuild` — `https://martinfowler.com/articles/research-review-rebuild.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** when surrounding documentation drifts, take the code path that already carries the authoritative invariants as the single source of truth and treat wrappers as supplementary compatibility layers.
- **Decision:** `reuse/integrate` — keep `DialogStateService` as the continuity source of truth, keep wrappers thin, and lock the next block on the remaining non-frozen writer seam that still shapes expected-reply/question-contract state outside the service.
- **Rejected options:**
  - reviving already-collapsed `session_memory.py` micro-bridges as the next block
  - taking frozen `pending.py` restore as the immediate next cut despite the explicit freeze
  - continuing Block D with another mixed `booking_prompt` label just because the word still appears in legacy traces
- **Open questions:** whether the next implementation block should move the whole `_set_expected_reply_context(...)` family in one cut or split out the trace-only side effects if they prevent a clean writer deletion.

## Root cause (mandatory)
- **Symptom:** after the normal-path `booking_prompt` cutover, the repo still has multiple continuity candidates, but canon had not yet locked which remaining live writer seam is both admissible and unfrozen.
- **Minimal reproduction:**
  1. Run `rg -n "expected_reply_type|expected_reply_reason|pending_resume|last_question|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`.
  2. Inspect `truffles-api/app/routers/webhook/session_memory.py` and confirm the live session-memory shaping helpers already delegate to `DialogStateService`.
  3. Inspect `truffles-api/app/services/state_service.py` and confirm pending-resume capture/restore already reuses `DialogStateService` there.
  4. Inspect frozen `truffles-api/app/routers/webhook/pending.py` and observe that direct pending-resume snapshot/restore authority is still local, but blocked by freeze.
  5. Inspect `truffles-api/app/routers/webhook/context_manager.py` and observe that `_set_expected_reply_context(...)` still performs a multi-writer continuity sync outside `DialogStateService`.
- **Evidence to capture:**
  - Block D is closed only because the remaining legacy `booking_prompt` branches are mixed seams, not because they were ignored
  - `session_memory.py` and `state_service.py` are not valid next blocks because they no longer hold the richest remaining writer authority
  - frozen `pending.py` is explicitly blocked for the immediate next cut
  - `context_manager._set_expected_reply_context(...)` is locked as the next implementation target
- **Five Whys (or equivalent):**
  1. Why can’t we keep extending Block D? Because the remaining `booking_prompt` branches are mixed with recovery, media, or tool-interrupt semantics instead of another pure normal-path owner seam.
  2. Why not return to old continuity micro-slices? Because the earlier session-memory bridges already collapsed those local writers; revisiting them would be fake progress.
  3. Why not take pending-resume restore immediately? Because the remaining direct writer lives in frozen `pending.py`.
  4. Why is `context_manager._set_expected_reply_context(...)` different? Because it is still non-frozen and still shapes several live continuity payloads together.
  5. Why must this be locked in canon now? Because otherwise the next agent can still choose a finished seam, a frozen seam, or another mixed booking micro-slice and claim motion without deletion value.
- **Root cause statement:** the program already collapsed many small continuity writers, but canon had not yet frozen which remaining live writer seam is both non-frozen and deletion-worthy after Block D; without that ranking, the next step could easily regress into fake progress.
- **Fix mechanism:**
  - audit the remaining continuity writers after Block D closure
  - explicitly block frozen or already-collapsed seams
  - lock one richer non-frozen continuity implementation target
  - regenerate canon/agent packet so the next move is machine-readable

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/services/state_service.py`
  - existing `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-*.md` bridge evidence as historical proof that those micro-writers were already collapsed
- **External reuse:**
  - Martin Fowler `Research, Review, Rebuild`
- **Why not reinvent the wheel:** the audit matters only if it points to the already-existing continuity source of truth (`DialogStateService`) and deletes another real writer seam instead of creating new wrappers.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this block is governance and seam ranking only; runtime behavior does not change here.

## Invariant
- No frozen-router edits.
- No runtime implementation hidden inside the audit.
- The audit must lock exactly one next continuity implementation target.
- Already-collapsed session-memory micro-seams must not be reintroduced as “next work”.

## Scope
- Audit the remaining continuity seams after Block D closure.
- Rank admissibility and deletion value.
- Publish the next implementation target and explicit blocked seams.
- Update canon/session artifacts and regenerate the agent packet.

## Out of scope
- runtime code changes
- new tests outside packet/architecture doc checks
- edits to frozen `pending.py`
- a pending-resume implementation cutover
- boundary or proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan (1..N)
1. Publish this audit TP with RCA and one exact web search.
2. Re-run the continuity next-block contract seam scan and inspect the remaining live writers.
3. Rank blocked, already-collapsed, and admissible continuity seams.
4. Lock one next implementation target and explicitly mark blocked seams.
5. Update `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, and session/canon artifacts.
6. Regenerate the agent packet and run governance checks.

## DoD
- one evidence-backed next continuity implementation target is chosen
- Block D is explicitly closed as normal-path complete
- frozen `pending.py` restore is explicitly marked blocked for the immediate next block
- `context_manager._set_expected_reply_context(...)` is explicitly locked as the next admissible continuity cut
- machine-readable canon points to this audit block and to the next implementation move
- governance checks are green

## Checks
- `rg -n "expected_reply_type|expected_reply_reason|pending_resume|last_question|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- the seam-scan command output
- the new audit TP
- updated `docs/SOURCE_OF_TRUTH.yaml`
- regenerated `docs/_generated/AGENT_PACKET.*`
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** no runtime quality suites; doc and architecture checks only
- **Stop condition:** if the audit cannot identify a non-frozen seam that deletes a real continuity writer family, stop and escalate instead of reviving a finished micro-bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only governance lock; no runtime rollout
- **Go/no-go signals:** packet regeneration and governance checks green
- **Rollback:** revert doc/canon updates and regenerate the packet
- **Post-release monitoring window:** next block must start from the locked continuity target, not from a newly improvised booking or session-memory micro-slice

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
  - canon may point to the continuity block only if the audit evidence still shows that remaining `booking_prompt` labels are mixed seams, `session_memory.py` is already collapsed, frozen `pending.py` is blocked, and `context_manager._set_expected_reply_context(...)` remains the richest non-frozen live writer seam.

## Rollback
1. Revert the new audit TP and canon/session updates.
2. Regenerate the packet from the previous source of truth.
3. Re-run the governance checks.

## No-go
- no runtime implementation hidden inside the audit
- no reopening of Block D without new deletion evidence
- no promotion of frozen `pending.py` into the immediate next block
- no claim that the audit itself counts as continuity convergence

## Risks / blockers
- `context_manager._set_expected_reply_context(...)` may still prove too broad if trace-only side effects cannot be separated from state writing cleanly
- frozen `pending.py` keeps a tempting higher-value continuity seam out of immediate reach
- the residual `booking_prompt` labels in legacy can still mislead future agents unless the mixed-seam classification stays explicit in canon

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `pending.py` still owns direct pending-resume snapshot/restore authority
  - `context_manager.py` still owns expected-reply/question-contract state-sync authority
  - broader semantic authority still remains in frozen `decision.py`
- **Why not in this block:**
  - this block only ranks and locks the next continuity deletion target; it does not implement the cutover
- **Risk if deferred:**
  - the program can backslide into a frozen seam, a finished seam, or another mixed booking micro-slice and lose demolition discipline
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922.md`
- **Expiry/trigger to stop deferral:**
  - before any new consultant-core continuity implementation block starts in this worktree

## Next-block contract (mandatory)
- **Next block objective:** `context_manager_expected_reply_state_sync_owner_cutover_after_continuity_audit`
- **First deterministic check command:** `rg -n "_set_expected_reply_context|_sync_canonical_dialog_state|_sync_session_memory_interaction_state" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/core/dialog_state_service.py`
- **Blocked-by conditions:** inability to make `_set_expected_reply_context(...)` thin without frozen-file edits, or proof that trace-only side effects cannot be cleanly separated from continuity writing
- **Owner role for closure:** `Top Architect`
