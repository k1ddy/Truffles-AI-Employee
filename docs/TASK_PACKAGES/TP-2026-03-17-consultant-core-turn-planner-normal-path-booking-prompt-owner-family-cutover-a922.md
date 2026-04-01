# TP-2026-03-17-consultant-core-turn-planner-normal-path-booking-prompt-owner-family-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-NORMAL-PATH-BOOKING-PROMPT-OWNER-FAMILY-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-GREETING-FAMILY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-POST-BOOKING-PROMPT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий richer semantic authority seam: safe normal-path `booking_prompt` turns should no longer enter frozen `truffles-api/app/routers/webhook/decision.py` to build booking prompt text, expected-reply transitions, booking-state writes, and typed outcome/meta. Этот блок должен использовать уже существующие new-core seams (`TurnPlanner`, `DialogStateService`, `TurnExecutor`, shared owner finalizer) и сделать frozen legacy unreachable для bounded normal booking prompt family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "booking_prompt|_next_booking_prompt|intent_queue_choice == \\\"booking\\\"" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1780,1945p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '22430,22910p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '260,345p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '638,690p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '380,455p' truffles-api/app/core/turn_executor.py`
- `FACT findings`:
  - legacy still owns the main normal booking prompt authoring path in `decision.py`, including prompt text selection, `expected_reply_type`/reason transitions, booking state persistence, and user-message trace/meta for normal booking collect turns
  - `intent_routing` still uses `resume_reason="booking_prompt"` as the semantic anchor for multiple normal/followup families, proving that `booking_prompt` remains a real continuity/semantic spine rather than a cosmetic label
  - the new-core owner finalizer already persists user/assistant messages, typed `TurnOutcome`, expected-reply context, dialog state, and booking payloads in one place
  - `TurnExecutor` already supports typed owner `action="booking_prompt"`, so the missing piece is a broader direct owner path, not a new contract
- `Detected drift (docs vs code)`:
  - canon now correctly says `booking_prompt` is the next admissible seam, but runtime still delegates all safe normal booking prompt authoring to frozen legacy.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Strangler Fig Application"`
- **Date/time (local):** `2026-03-17 13:35 +0500`
- **Why this query is precise:** this block is an incremental runtime-owner replacement of a still-central legacy family, and the implementation must keep the old helper reachable only as a compatibility shim while moving live authority to the new owner.
- **Sources opened (from this query):**
  - `Strangler Fig Application` — `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** replace a central legacy slice by routing an increasing bounded family through the new implementation while shrinking the old path until it becomes compatibility-only or unreachable.
- **Decision:** `reuse/integrate` — reuse the existing shared owner finalizer and read-only `_next_booking_prompt(...)` compatibility helper to move the safe `booking_prompt` family into new core without editing frozen legacy files.
- **Rejected options:**
  - another narrow specialist followup cut that still leaves generic `booking_prompt` alive
  - rewriting booking prompts from scratch instead of reusing the current helper semantics
  - bundling `style_reference` or `out_of_domain` into this block
- **Open questions:** whether safe `intent_queue -> booking` should be included in the first bounded cut or admitted in an immediately following sibling block if the safe family becomes too broad.

## Root cause (mandatory)
- **Symptom:** safe normal booking prompt turns still depend on frozen `decision.py`, even though new core already owns most of the surrounding typed planning, artifact assembly, expected-reply, and booking payload substrate.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/decision.py` around the LLM-policy-core booking prompt path and the `intent_queue_choice == "booking"` path.
  2. Observe that legacy still sets `expected_reply_context`, writes booking prompt trace/meta, computes `bot_response`, and persists booking state for these normal prompt families.
  3. Inspect `truffles-api/app/services/reasoning_core.py` and confirm the shared owner finalizer already handles user/assistant save, expected-reply, dialog state, booking payload, and typed owner artifact assembly.
  4. Inspect `truffles-api/app/core/turn_executor.py` and confirm typed `action="booking_prompt"` already exists.
- **Evidence to capture:**
  - direct owner bypass for safe normal `booking_prompt` turns
  - typed `TurnOutcome.action="booking_prompt"` on the owner path
  - booking payload and expected-reply continuity preserved in `DialogStateService`
  - fallback to legacy remains clean for non-safe envelopes
- **Five Whys (or equivalent):**
  1. Why is `booking_prompt` still legacy-owned? Because no broader direct owner path consumes the normal collect prompt family.
  2. Why hasn’t this already moved with the narrower collect owners? Because the earlier blocks only removed bounded followup/service-query slices, not the generic prompt spine.
  3. Why is it admissible now? Because the new-core substrate for planning, dialog state, booking payload, and owner artifact assembly is already in place.
  4. Why not take `style_reference` or `out_of_domain` first? Because those seams still mix semantic meaning with broader boundary/media/firebreak behavior.
  5. Why does deleting `booking_prompt` matter? Because many remaining booking and followup routes still normalize around it, so retiring it removes a central legacy authority rather than another leaf seam.
- **Root cause statement:** the system already has a typed new-core path for prompt ownership, but the still-central normal `booking_prompt` family was never moved onto it, leaving frozen `decision.py` in charge of the main booking prompt spine and its continuity side effects.
- **Fix mechanism:**
  - add one bounded direct owner path for safe normal `booking_prompt` turns in `reasoning_core`
  - reuse the shared owner finalizer plus current booking prompt helper semantics
  - preserve expected-reply and booking payload through `DialogStateService`
  - fall back cleanly to legacy for non-safe envelopes

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_finalize_turn_planner_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py`
  - `DialogStateService.build_collect_owner_state(...)`
  - `DialogStateService.build_collect_owner_booking_payload(...)`
  - `TurnExecutor.build_owner_cutover_artifact(...)`
  - read-only `_next_booking_prompt(...)` helper in `truffles-api/app/routers/webhook/decision.py`
- **External reuse:**
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the block should delete old authority by reusing the existing typed seams and current prompt semantics, not by creating a second prompt system.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `32`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is the next real semantic-owner cutover and requires runtime code plus focused tests and canon sync.

## Invariant
- No frozen-router edits.
- No new ingress bridge family.
- Existing narrower collect/followup owners must not regress.
- Non-safe booking prompt envelopes must still fall back to legacy.

## Scope
- Add a bounded direct owner path for safe normal `booking_prompt` turns.
- Reuse current prompt semantics and persist booking payload/expected-reply through new core.
- Add focused reasoning-core/runtime-contract/dialog-state tests.
- Sync canon/session artifacts if green.

## Out of scope
- `style_reference`
- `out_of_domain`
- timeout/degrade recovery families
- invalid-schema specialist recovery
- proof-path or multi-pack work
- frozen router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-normal-path-booking-prompt-owner-family-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Define the safe normal `booking_prompt` candidate boundary and its fallback gates.
3. Implement the direct owner path in `reasoning_core` using the shared owner finalizer.
4. Preserve booking payload and expected-reply continuity through `DialogStateService`.
5. Add focused reasoning-core/runtime-contract/dialog-state coverage.
6. Run focused and full validations.
7. Sync canon/session artifacts only if green.

## DoD
- safe normal `booking_prompt` turns bypass frozen `decision.py`, including the bounded initial `service`, `service -> datetime`, `service + exact datetime -> name`, no-reference `check_booking_prompt` reference-prompt progressions, and named-specialist followup prompts that preserve the same missing slot with explicit specialist preference
- owner artifacts emit typed `action="booking_prompt"`
- booking payload / expected-reply continuity are preserved through new core
- legacy fallback remains for non-safe envelopes
- no new bridge family and no frozen-router edits

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_prompt_owner or llm_booking_prompt_owner or intent_queue_booking_prompt_owner or bookability_time_collect_owner or specialist_name_collect_owner or service_choice_specialist_time_collect_owner or check_booking_prompt_owner or specialist_followup_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- focused owner-path tests for normal `booking_prompt` turns
- runtime-contract evidence for typed `action="booking_prompt"`
- dialog-state evidence for booking payload and expected-reply continuity
- green full reasoning-core/dialog-state/runtime-contract/architecture checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** focused `booking_prompt` tests first, then full suites
- **Stop condition:** if the block cannot delete a bounded `booking_prompt` family without frozen-file edits or new bridge growth, stop and return to seam re-splitting instead of forcing another partial bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-family deletion only; no new entrypoints
- **Go/no-go signals:** focused booking prompt owner tests plus full suites and governance checks green
- **Rollback:** revert owner-path/test/doc changes and regenerate the packet
- **Post-release monitoring window:** next block must move into the continuity collapse around the remaining booking restore/reset seams, not back into micro-slice seam farming

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - canon may count `booking_prompt` as deleted only if the safe normal family is proven through direct owner tests and non-safe envelopes still delegate cleanly.

## Rollback
1. Revert the reasoning-core/dialog-state/test/doc changes for this block.
2. Regenerate the packet.
3. Re-run the governance checks.

## No-go
- no frozen-router edit
- no new ingress detector family
- no widening into `style_reference` or `out_of_domain`
- do not count the block as done unless the old `booking_prompt` family is proven unreachable for the bounded safe normal path

## Risks / blockers
- `booking_prompt` may still hide more than one family and require one safe boundary split between generic prompt, intent-queue booking entry, and richer recovery variants
- over-absorbing timeout or invalid-schema recovery would break the block boundary and dilute deletion proof

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - timeout/degrade booking prompt recoveries remain legacy-owned
  - `style_reference` remains legacy-owned
  - `out_of_domain` remains legacy-owned
- **Why not in this block:**
  - this block only takes the safe normal `booking_prompt` family and leaves mixed or recovery-heavy families for later continuity/boundary blocks
- **Risk if deferred:**
  - the central booking prompt spine remains in frozen legacy and keeps multiple followup families anchored to legacy continuity behavior
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - before the program takes any other semantic cut in this worktree

## Next-block contract (mandatory)
- **Next block objective:** `single_continuity_writer_completion_after_booking_prompt_owner_family_cutover`
- **First deterministic check command:** `rg -n "expected_reply_type|expected_reply_reason|pending_resume|last_question|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
- **Blocked-by conditions:** failure to prove safe `booking_prompt` deletion or unresolved continuity regressions around booking restore/reset seams
- **Owner role for closure:** `Top Architect`
