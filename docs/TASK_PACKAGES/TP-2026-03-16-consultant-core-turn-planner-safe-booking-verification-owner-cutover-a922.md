# TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-BOOKING-VERIFICATION-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-FRESHNESS-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий owner-replacement block после session-memory freshness bridge: bounded safe booking-verification fact replies should stop delegating through frozen `truffles-api/app/routers/webhook/decision.py` when ingress already has a valid `check_booking` policy override and an active bot-owned conversation context. `reasoning_core` should directly own the safe read-only `calendar.get_booking` ok-path while all collect/not-found/mismatch/handoff behavior remains delegated.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/arch_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
    - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "booking_verification|calendar.get_booking|safe_.*owner_cutover" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1560,1668p' truffles-api/app/services/tool_registry_service.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_verification_policy_override'`
  - `python3 scripts/semantic_bridge_growth_guard.py`
- `FACT findings`:
  - ingress already primes a bounded `check_booking` / `calendar.get_booking` policy override through `detect_policy_core_route_snapshot(...)`.
  - despite that, the whole booking-verification fact path still delegates through frozen `decision.py`; there is no direct owner replacement in `reasoning_core` yet.
  - `execute_tool_action(..., tool_action="calendar.get_booking")` is already read-only and returns a bounded `tool_decision` contract; the safe `ok` result is a viable direct-owner slice.
  - `not_found`, `time_mismatch`, collect-like, and handoff-adjacent booking-verification behavior still carry broader outcome/state semantics and should remain delegated in this block.
- `Detected drift (docs vs code)`: owner-replacement progress is still missing for this already-bridged booking-verification fact seam.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org dataclasses dataclass Python official documentation`
- **Date/time (local):** `2026-03-16 22:02 +0500`
- **Why this query is precise:** this block reuses the existing read-only `ReasoningCoreConversationSnapshot` dataclass instead of adding an ad-hoc mutable context envelope for direct owner cutover gating.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** the standard-library dataclass contract is the correct baseline for passing read-only structured snapshot context through the cutover path without inventing a new mutable payload shape.
- **Decision:** `reuse + integrate` — reuse the existing `ReasoningCoreConversationSnapshot` contract for gating and conversation lookup instead of building another ad-hoc context dict.
- **Rejected options:**
  - adding a new mutable conversation context carrier just for this cutover
  - widening this block into collect/not-found/time-mismatch booking-verification semantics
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** booking-verification turns already have an ingress policy override, but even the safe read-only `calendar.get_booking` ok-path still runs through frozen `decision.py`.
- **Minimal reproduction:**
  1. Send an explicit booking-verification message that ingress classifies as `intent="check_booking"`, `action="fact"`, `tool_action="calendar.get_booking"`.
  2. Observe that `reasoning_core` primes the override but still delegates to `decision_router._handle_webhook_payload(...)`.
  3. Observe that no direct owner replacement exists in `reasoning_core` for the safe `calendar.get_booking` ok-path.
- **Evidence to capture:**
  - `reasoning_core` directly handles the safe booking-verification ok-path.
  - frozen `decision.py` becomes unreachable for that bounded normal path.
  - fallback to legacy delegate remains intact for not-found/mismatch or missing active conversation context.
- **Five Whys (or equivalent):**
  1. Why is legacy semantic authority still present here? Because booking-verification only has ingress override priming, not owner replacement.
  2. Why is that a problem? Because the old semantic owner still decides a read-only fact path that the new core can already classify safely.
  3. Why can this block stay bounded? Because `calendar.get_booking` already exposes a narrow read-only `tool_decision` contract and the safe `ok` result does not require new state writes.
  4. Why not include not-found/time-mismatch/collect behavior? Because those outcomes still carry broader follow-up and state semantics that are not safe to cut over in this block.
  5. Why fix this now? Because it deletes one more real legacy semantic seam without any new phrase-bridge growth.
- **Root cause statement:** booking-verification override priming exists, but `reasoning_core` still lacks a direct owner replacement for the safe `calendar.get_booking` ok-path, so frozen `decision.py` remains the semantic owner for that bounded fact seam.
- **Fix mechanism:**
  - add a bounded direct owner path in `reasoning_core` for safe booking-verification ok replies
  - gate it on an active bot-owned conversation snapshot / conversation id and safe downstream `tool_decision == "ok"`
  - keep all other booking-verification outcomes on the existing delegate path

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `TurnPlanner.build_from_policy_override(...)`
  - existing direct owner finalizer in `reasoning_core`
  - existing `execute_tool_action(..., tool_action="calendar.get_booking")`
  - existing `ReasoningCoreConversationSnapshot` dataclass for read-only active conversation context
- **External reuse:**
  - official Python dataclass contract
- **Why not reinvent the wheel:** this is an owner replacement slice, not a new booking-verification protocol.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded owner-replacement cutover with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Only the safe `calendar.get_booking` ok-path moves into direct owner replacement.
- `not_found`, `time_mismatch`, collect, and handoff-adjacent booking-verification behavior stay delegated.

## Scope
- Add a bounded direct owner path in `reasoning_core` for safe booking-verification ok replies.
- Reuse active conversation snapshot / provided conversation id instead of inventing a new context carrier.
- Add focused regression tests and keep delegate fallback for non-safe outcomes.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- collect/not-found/time-mismatch booking-verification cutover
- broader booking planner ownership
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-owner-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add a bounded booking-verification owner-replacement helper to `reasoning_core`.
3. Wire it into the direct owner sequence without any new bridge growth.
4. Add focused regression coverage and rerun required non-growth/architecture checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` directly owns the safe booking-verification ok-path.
- frozen `decision.py` is unreachable for that bounded normal path.
- non-safe booking-verification outcomes still delegate.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core tests showing direct owner replacement for safe booking verification ok-path
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + one targeted fallback compatibility test + architecture only for this bounded block
- **Stop condition:** if this slice needs collect/not-found/time-mismatch state ownership or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** reasoning-core + targeted fallback + architecture suites green; growth/session gates green
- **Rollback:** revert the new direct owner helper, tests, and doc sync
- **Post-release monitoring window:** next block should delete another existing owner seam or return to continuity only if bounded writer deletion is still real

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe booking-verification owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core direct owner helper, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into booking-verification collect/not-found/time-mismatch ownership
- no counting this block as done unless frozen `decision.py` becomes unreachable for the bounded safe ok-path

## Risks / blockers
- if this block tries to own not-found/time-mismatch outcomes, expected-reply and follow-up semantics can drift.
- if it ignores active conversation context, `calendar.get_booking` can silently degrade into false not-found behavior.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader booking-verification outcomes still remain in legacy `decision.py`
  - single continuity writer is still not complete
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded safe ok-path owner replacement slice; widening to other outcomes would mix richer booking-state semantics into the block
- **Risk if deferred:**
  - frozen `decision.py` keeps owning a read-only fact path that new core can already classify safely
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - if the next booking owner slice needs stateful mismatch/collect semantics, split it and do not widen this block retroactively

## Next-block contract (mandatory)
- **Next block objective:** either delete another bounded direct owner seam after safe booking verification, or return to continuity only if the next writer deletion is still bounded and real
- **First deterministic check command:** `rg -n "calendar.get_booking|safe_booking_verification|turn_planner_safe_booking_verification" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** next slice requires new bridge growth, frozen-router edits, or booking state ownership wider than the safe ok-path
- **Owner role for closure:** `Top Architect`
