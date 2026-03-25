# TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-daypart-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-CHOICE-SPECIALIST-DAYPART-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-CHOICE-SPECIALIST-TIME-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-time-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded legacy semantic seam: deterministic service-choice specialist `daypart_followup` turns should no longer enter frozen `truffles-api/app/routers/webhook/decision.py` before persistence. This block must also fix the underlying collect-owner continuity gap by letting the shared owner finalizer preserve safe booking slot state (`service` / `datetime` / `last_question`) in canonical context for bounded booking-followup owners, without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-time-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "daypart_followup|service_choice_specialist_time_collect|build_collect_owner_state|booking_state\[|_set_booking_context" truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '22060,22610p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '248,340p' truffles-api/app/core/dialog_state_service.py`
- `FACT findings`:
  - frozen `decision.py` already collapses `daypart_followup` into the same booking-side specialist availability collect owner family as the service-choice `day` / `weekday` / `weekend` turns, but unlike the empty-datetime family it also copies the provided `datetime` token into `booking_state` before setting the question contract
  - the shared owner finalizer already materializes expected reply, question contract, and canonical dialog-state projections, but it does not currently preserve booking slot state for safe collect owners
  - the richer generic booking-prompt seam is not currently admissible without a broader direct LLM-owner extraction, because it does not come from the ingress policy snapshot family that current direct owner cutovers consume
- `Detected drift (docs vs code)`: direct collect owner cutovers already exist for bounded specialist/booking families, but slot-preserving booking continuity still depends on legacy collect materialization.

## One web search (mandatory before implementation)
- **Query (exact):** `Python copy deepcopy official docs`
- **Date/time (local):** `2026-03-17 11:48 +0500`
- **Why this query is precise:** the block needs a service-owned booking payload setter/normalizer that preserves detached-copy semantics while moving booking-context writes out of legacy collect materialization.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard-library way to preserve detached nested payload semantics when moving context shaping into a service-owned setter.
- **Decision:** `reuse + integrate` — keep booking payload shaping on explicit detached-copy semantics inside `DialogStateService`; do not invent a custom copy helper.
- **Rejected options:**
  - direct in-place mutation of existing `conversation.context["booking"]`
  - a new ad-hoc booking copy helper outside `DialogStateService`
  - widening immediately to the generic booking-prompt LLM seam
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** deterministic service-choice specialist `daypart_followup` turns are still only primed for delegate, and the shared collect-owner finalizer still cannot preserve the prefilled `datetime` slot that frozen legacy writes into `booking_state` for this family.
- **Minimal reproduction:**
  1. Run the existing reasoning-core delegate-priming test for `Какой мастер будет делать маникюр завтра вечером?`.
  2. Observe that reasoning-core stops at override priming and still hands the turn to frozen `decision.py`.
  3. Inspect the legacy collect branch and confirm that it copies `service` and `datetime` into `booking_state`, sets `last_question="datetime"`, then materializes the booking specialist availability followup prompt.
- **Evidence to capture:**
  - direct owner path bypasses frozen delegate for safe `daypart_followup`
  - booking slot state is preserved in conversation context before canonical question-contract sync
  - existing specialist exact-time and service-choice time collect owners now preserve safe booking slot state through the same shared finalizer path
  - fallback still delegates cleanly when owner conversation materialization is unavailable
- **Five Whys (or equivalent):**
  1. Why does `daypart_followup` still need frozen legacy? Because the owner finalizer can set the question contract but cannot yet preserve the prefilled booking `datetime` token.
  2. Why is that a problem? Because the prompt looks correct, but downstream bounded booking continuity can lose slot state.
  3. Why not take the richer generic booking-prompt seam instead? Because that would require direct LLM-owner extraction beyond the current policy-snapshot cutover surface.
  4. Why is `daypart_followup` safe once booking slot state is preserved? Because frozen `decision.py` already maps it into the same specialist availability collect family with deterministic prompt semantics.
  5. Why now? Because the richer audit shows this is the next admissible bounded deletion after the service-choice empty-datetime family, and it also repairs the underlying collect-owner continuity gap.
- **Root cause statement:** bounded collect owner cutovers still lack service-owned booking slot persistence, so deterministic prefilled-datetime specialist followups remain legacy-owned even though their prompt semantics are already deterministic and reusable.
- **Fix mechanism:**
  - add a service-owned booking payload normalizer/setter/builder in `DialogStateService`
  - extend the shared collect owner finalizer to apply safe booking slot state before expected-reply canonical sync
  - consume that path for deterministic `daypart_followup`, and retrofit existing safe specialist collect owners that depend on preserved booking slots

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic `_build_specialist_availability_followup_response(...)` helper in frozen legacy
  - existing `context_manager._set_expected_reply_context(...)` canonical sync path
- **External reuse:**
  - official Python `copy.deepcopy` documentation
- **Why not reinvent the wheel:** the block should reuse the existing collect-owner finalizer and deterministic followup helper, only adding the missing service-owned booking payload projection they need.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** this block combines one bounded owner deletion with the minimum shared continuity mechanism needed to keep the collect-owner contract semantically correct.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No direct generic LLM booking-prompt extraction in this block.
- Shared collect finalizer semantics must remain backward-compatible for already-cut safe owners.

## Scope
- Add service-owned booking payload shaping in `DialogStateService` for safe collect-owner materialization.
- Extend the shared owner finalizer to apply safe booking slot state before canonical question-contract sync.
- Add a bounded direct owner path for deterministic service-choice specialist `daypart_followup` turns.
- Retrofit existing safe specialist collect owners to reuse the same booking payload path where required.
- Add focused reasoning-core regressions.
- Sync canon/session artifacts.

## Out of scope
- generic LLM booking-prompt owner extraction
- frozen router files
- reschedule / verification / handoff branches
- new ingress snapshot families
- broader booking timeout/restore semantics

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-daypart-collect-owner-cutover-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add service-owned booking payload normalizer/setter/builder helpers in `DialogStateService`.
3. Extend the shared collect owner finalizer to apply safe booking slot state and grounded referents before canonical question-contract sync.
4. Add a bounded `daypart_followup` direct owner path in `reasoning_core`, reusing the existing specialist availability helper.
5. Retrofit existing safe specialist collect owners to pass safe booking slot state through the shared finalizer where needed.
6. Add focused regressions for direct bypass, booking-slot preservation, and fallback.
7. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic service-choice specialist `daypart_followup` bypasses frozen `decision.py`
- shared collect owner finalizer preserves safe booking slot state in context before canonical sync
- existing safe specialist collect owners that require preserved booking slots reuse the same path
- fallback still delegates cleanly when owner conversation materialization is unavailable
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'booking_payload'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'service_choice_specialist_daypart_collect_owner or specialist_name_collect_owner or service_choice_specialist_time_collect_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_reasoning_core.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- focused reasoning-core tests proving direct owner bypass for safe `daypart_followup`
- focused tests proving booking slot state is preserved through the shared collect owner finalizer
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused dialog-state + reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if slot-preserving collect owner state lands cleanly, the next block must return to a richer owner audit instead of continuing specialist micro-slices by inertia
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement plus bounded continuity bridge only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** focused regressions + full reasoning-core + architecture green; packet/session gates green
- **Rollback:** revert the new dialog-state/reasoning-core helpers, tests, and doc sync
- **Post-release monitoring window:** next block must prefer richer owner deletion over more specialist micro-families

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the daypart collect owner cutover and its booking-slot-preserving continuity bridge.

## Rollback
1. Revert the new dialog-state/reasoning-core helpers/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no generic LLM booking-prompt cutover in this block
- no counting the block as done unless `daypart_followup` bypasses frozen delegate and the shared collect owner path preserves booking slot state

## Risks / blockers
- if booking payload shaping diverges from legacy collect semantics, downstream booking followups could regress even when the visible reply still looks correct
- if this block silently widens into generic booking-prompt extraction, it will exceed the current admissible owner-cutover surface and break the strategy lock

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer generic booking-prompt collect ownership still remains legacy-owned
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only repairs safe collect-owner booking slot continuity and deletes one deterministic prefilled-datetime specialist seam; the richer generic collect seam would require a broader direct LLM-owner extraction
- **Risk if deferred:**
  - prefilled-datetime specialist collect continuity stays partially dependent on legacy booking-state materialization
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - after this block, the next move must return to richer owner audit; another specialist micro-slice requires explicit architectural waiver

## Next-block contract (mandatory)
- **Next block objective:** re-run the richer owner-replacement audit after the slot-preserving collect-owner bridge and daypart cutover land.
- **First deterministic check command:** `rg -n "LLM policy core booking prompt sent|policy_tool_action == \"collect\" and policy_collect_slot|build_collect_owner_booking_payload|daypart_followup" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the next candidate still requires direct LLM-owner extraction or frozen-router edits, do not take it as another bounded cut without explicit approval.
- **Owner role for closure:** `Top Architect`
