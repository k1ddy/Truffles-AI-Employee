# TP-2026-03-16-consultant-core-turn-planner-safe-info-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-INFO-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-EXECUTION-STRATEGY-LOCK-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-COMPLETION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать первый реальный owner-replacement cutover после strategy lock: turns, already covered by existing safe policy overrides for `contact`, `hours`, `promotions`, and `promotions_rules`, must stop delegating their first semantic owner step into frozen `truffles-api/app/routers/webhook/decision.py`. `turn_planner` should build the typed `PolicyDecision`, and `reasoning_core` should realize/send/save that bounded fact reply directly, so the legacy router becomes unreachable for this slice on the normal runtime path.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,220p' truffles-api/app/core/turn_planner.py`
  - `sed -n '1620,1810p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '434,560p' truffles-api/app/routers/webhook/info.py`
  - `rg -n 'primes_(hours|promotions|promotions_rules|contact)_policy_override' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - the strategy lock is active, but the first richer semantic owner cutover has not happened yet.
  - `reasoning_core` still delegates all richer semantic slices into frozen `decision.py` even when an existing policy override already gives a complete safe fact contract.
  - `turn_planner` still has only scaffold builders for degrade/preflight and cannot yet build a normal typed `PolicyDecision` from an existing policy-core override payload.
  - `info.py` already contains truth-first reply builders for bounded safe info intents, so the missing piece is owner replacement, not new domain detection.
- `Detected drift (docs vs code)`: execution strategy says progress requires old-authority deletion or unreachability, but the current runtime still counts only bridge priming for these safe info intents.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org SQLAlchemy 2.0 select scalar_one_or_none official docs`
- **Date/time (local):** `2026-03-16 19:53 +0500`
- **Why this query is precise:** this block needs one read-only conversation lookup seam for owner replacement, and the implementation should reuse the existing ORM query style instead of inventing a new persistence pattern.
- **Sources opened (from this query):**
  - `SQLAlchemy ORM Querying Guide (SELECT)` — `https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** the standard ORM select/query pattern is already sufficient for deterministic read-only conversation lookup and does not require a new repository abstraction for this bounded cutover.
- **Decision:** `reuse + integrate` — keep the existing SQLAlchemy session query style for conversation/client lookup inside the bounded owner cutover.
- **Rejected options:**
  - adding a new repository layer just for this first owner cutover
  - widening the block into a persistence refactor
  - adding any new detector family in `info_signal_service.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** even after the strategy lock, safe fact intents with complete existing policy overrides still route their first semantic owner step through frozen `decision.py`.
- **Minimal reproduction:**
  1. Send `Какой у вас номер телефона?` into `reasoning_core.handle_webhook_payload(...)`.
  2. Observe that `detect_policy_core_route_snapshot(...)` builds a complete `contact` fact override.
  3. Observe that the runtime still delegates into `decision_router._handle_webhook_payload(...)` instead of using `turn_planner` + direct fact realization.
- **Evidence to capture:**
  - `turn_planner` now produces a typed `PolicyDecision` from the existing policy override payload.
  - `reasoning_core` now returns a direct owner-cutover response for safe info fact intents without calling frozen `decision.py`.
  - if direct truth realization is unavailable, the runtime falls back to the legacy delegate instead of dropping the turn.
- **Five Whys (or equivalent):**
  1. Why does the legacy router still own these safe turns? Because `reasoning_core` only primes overrides; it never consumes them as a real semantic owner.
  2. Why can’t `reasoning_core` consume them today? Because `turn_planner` cannot yet convert a normal policy override payload into the typed `PolicyDecision` contract.
  3. Why is that a problem? Because bridge priming alone does not delete old authority; it only moves inference earlier.
  4. Why is this the right first owner cutover? Because `contact/hours/promotions/promotions_rules` already have bounded truth-first reply builders and do not require new detector growth.
  5. Why fix this now? Because the execution strategy lock explicitly requires owner replacement as the next non-negotiable move.
- **Root cause statement:** the runtime still lacked a typed owner-replacement path that could consume an existing policy-core override and directly realize/save/send a bounded fact reply, so frozen `decision.py` remained the first semantic owner even for safe fact intents.
- **Fix mechanism:**
  - teach `turn_planner` to build a typed `PolicyDecision` from an existing policy override payload
  - add a bounded direct-owner path in `reasoning_core` for safe `tool_action="info"` fact intents
  - reuse existing truth reply builders from `info.py`
  - preserve fallback to legacy delegate when the direct realization preconditions are not met

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot.to_override()` payload shape
  - existing `truffles-api/app/routers/webhook/info.py::_build_info_intent_reply(...)`
  - existing `get_or_create_user`, `get_or_create_conversation`, and `save_message`
  - existing trace helpers and `send_message_safe`
- **External reuse:**
  - standard SQLAlchemy query pattern from official docs
- **Why not reinvent the wheel:** this block should delete a semantic seam, not widen into a persistence or transport rewrite.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** first real owner-replacement runtime cutover plus required canon/session sync.

## Invariant
- No new generic ingress phrase-bridge family.
- No edit to frozen legacy semantic files.
- If direct owner realization cannot safely complete, runtime falls back to existing delegate path.
- Product contract remains FACT/COLLECT/HANDOFF; this block only cuts over one bounded FACT slice.

## Scope
- Add `turn_planner` support for typed normal-path `PolicyDecision` creation from an existing policy override payload.
- Add a bounded direct owner path in `reasoning_core` for safe info fact intents.
- Reuse existing info truth builders and transport/persistence helpers.
- Add regression tests proving frozen `decision.py` is unreachable for the chosen slice on the normal path.
- Sync canon/session artifacts.

## Out of scope
- new semantic detector families
- collect/handoff owner cutover
- continuity writer completion
- boundary owner cutover
- proof-path rewrite
- frozen-router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-info-owner-cutover-a922.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
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
2. Extend `turn_planner` with typed normal-path decision building from existing policy override payloads.
3. Add a bounded direct info-fact owner path in `reasoning_core` for safe intents already covered by existing overrides.
4. Add tests proving the direct owner path bypasses frozen `decision.py` and falls back cleanly when direct realization is unavailable.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `turn_planner` can build a typed `PolicyDecision` from an existing safe policy override payload.
- `reasoning_core` directly handles safe `contact/hours/promotions/promotions_rules` fact intents without delegating into frozen `decision.py` on the normal path.
- runtime falls back to legacy delegate if direct realization cannot produce a safe truth reply.
- tests prove both owner-cutover and fallback behavior.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime unit tests showing frozen delegate is not called for the cutover slice
- contract test showing `turn_planner` produces a typed decision from policy override payload
- updated source-of-truth / packet showing the new active block and cutover status

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + architecture only for this bounded block
- **Stop condition:** if direct owner cutover requires a new detector family or a frozen-router edit, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded runtime cutover behind existing safe policy overrides only
- **Go/no-go signals:** reasoning-core + contract + architecture suites green; arch/session gates green
- **Rollback:** revert planner direct-owner builder and reasoning-core direct info owner path only
- **Post-release monitoring window:** next block must continue owner replacement or single continuity writer work, not new bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the direct owner cutover block and packet output.

## Rollback
1. Revert `turn_planner` normal-path builder, `reasoning_core` direct info owner path, tests, and canon/session sync.
2. Regenerate packet.
3. Re-run contract/architecture/session gates.

## No-go
- no new `detect_*` or `looks_like_*` families
- no frozen-router edit
- no widening into continuity/proof refactors
- no counting a new override as progress unless the legacy semantic seam becomes unreachable for this slice

## Risks / blockers
- if direct owner path starts mutating before all truth preconditions are checked, fallback can become unsafe; reply resolution must happen before persistence.
- if the direct path tries to cover more than the existing safe info intents, it will widen into another bridge-farming block.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader planner/outcome ownership still remains in legacy `decision.py`
  - continuity still has fragmented writers
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is the first bounded owner replacement slice; widening further would mix goals and increase regression risk
- **Risk if deferred:**
  - without a successful first owner cutover, the repo could fall back into bridge-growth work even with the new guardrails
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-completion-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next block can delete another richer semantic seam or finish single-writer continuity ownership

## Next-block contract (mandatory)
- **Next block objective:** continue owner replacement with the next bounded semantic seam that can make a legacy `decision.py` branch unreachable, or move to single continuity writer completion if richer semantic owner cutover stalls without deletion value
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** need for new hotspot bridge growth, need for frozen-router edits, or inability to prove old-seam unreachability
- **Owner role for closure:** `Top Architect`
