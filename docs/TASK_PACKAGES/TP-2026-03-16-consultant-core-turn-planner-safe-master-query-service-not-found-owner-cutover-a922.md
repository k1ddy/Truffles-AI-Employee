# TP-2026-03-16-consultant-core-turn-planner-safe-master-query-service-not-found-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-SERVICE-NOT-FOUND-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-DURATION-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-duration-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NEXT-SAFE-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить еще один bounded legacy semantic seam без bridge growth: если grounded `master_query` fact path truth-first образом возвращает deterministic `service_not_found`, `reasoning_core` должен завершать этот turn через shared collect finalizer и не заходить в frozen `decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-collect-owner-cutover-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-duration-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1400,1458p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '2099,2238p' truffles-api/app/services/reasoning_core.py`
  - `python3 - <<'PY' ... build_master_reply_from_pack(... service_query=\"Несуществующая услуга\" ...) ... PY`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'master_query_collect_owner or master_query_owner'`
- `FACT findings`:
  - grounded `master_query` fact owner cutover currently accepts only `service_match`.
  - `build_master_reply_from_pack(...)` already returns deterministic collect-shaped `service_not_found` replies with truth metadata and `clarify_reason=\"master_service_not_found\"`.
  - current accept gate for `master_query` collect owner is stricter than actual pack metadata shape, so the missing-service and service-not-found collect seams are both still too dependent on legacy fallback.
- `Detected drift (docs vs code)`: strategy lock requires owner replacement, but grounded `master_query` still re-enters frozen legacy when truth metadata says `service_not_found`.

## One web search (mandatory before implementation)
- **Query (exact):** `Python str.casefold official docs`
- **Date/time (local):** `2026-03-17 00:10 +0500`
- **Why this query is precise:** the bounded accept gates in this block must normalize truth metadata tokens case-insensitively without adding branching noise or locale-sensitive comparisons.
- **Sources opened (from this query):**
  - `Built-in Types — str.casefold()` — `https://docs.python.org/3/library/stdtypes.html#str.casefold`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `str.casefold()` is the standard-library normalization primitive for aggressive case-insensitive token comparison.
- **Decision:** `reuse + integrate` — tighten the accept gates with explicit `casefold()` normalization and reuse the existing collect finalizer instead of adding a new bridge family or a parallel reply builder.
- **Rejected options:**
  - adding a new ingress detector family
  - touching frozen router files
  - widening into broader specialist/booking collect semantics
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** grounded `master_query` turns that truthfully resolve to `service_not_found` still delegate to frozen `decision.py`, and the already-shipped safe collect cutover for `master_query` relies on stricter metadata than the real pack reply emits.
- **Minimal reproduction:**
  1. Prime a grounded `master_query` fact override with `tool_args.service_query`.
  2. Return a deterministic `build_master_reply_from_pack(...)` result with `master_reply_mode=\"service_not_found\"`.
  3. Observe that `reasoning_core` falls back to legacy because only `service_match` is accepted on the fact path.
- **Evidence to capture:**
  - grounded `master_query` `service_not_found` reply bypasses frozen delegate through shared collect finalization
  - malformed/unapproved `service_not_found` metadata still falls back to legacy
- **Five Whys (or equivalent):**
  1. Why does the safe path still hit legacy? Because the grounded fact owner gate only accepts `service_match`.
  2. Why is that incomplete? Because the same truth helper already emits a deterministic collect response for `service_not_found`.
  3. Why did the collect owner path not absorb it automatically? Because it only covers missing-service policy overrides, not grounded service-not-found turns.
  4. Why is it safe to cut over now? Because the semantic owner already tells us this is `master_query`, and the downstream truth helper gives a bounded collect contract with a specific clarify reason.
  5. Why keep it bounded? Because broader master/specialist stateful semantics would widen scope beyond a safe owner replacement.
- **Root cause statement:** `reasoning_core` still treats grounded `master_query service_not_found` as an unsupported downstream shape, even though the truth helper and shared collect finalizer already provide enough information for direct owner completion.
- **Fix mechanism:**
  - extend master-query acceptance to match actual truth metadata shape
  - synthesize a bounded collect decision from the grounded policy override for approved `service_not_found`
  - keep malformed or broader envelopes on legacy fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing grounded `master_query` fact owner path
  - `TurnPlanner.build_from_policy_override(...)`
  - existing shared collect finalizer
  - `build_master_reply_from_pack(...)`
  - `resolve_master_intent(...)`
- **External reuse:**
  - official Python `str.casefold()` docs
- **Why not reinvent the wheel:** the block only reuses existing planner/finalizer/truth helper seams and deletes one more legacy path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement block plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new generic phrase-bridge family.
- Only approved grounded `master_query service_not_found` collect replies become direct-owner.
- Malformed or broader master-query envelopes must still fall back to legacy delegate before persistence.

## Scope
- Extend master-query accept gates to the real pack metadata shape.
- Add a bounded service-not-found collect owner cutover for grounded `master_query`.
- Add focused positive/fallback regression coverage.
- Sync canon/session artifacts.

## Out of scope
- frozen `decision.py` / `booking.py` / `pending.py`
- broader specialist recommendation semantics
- new ingress bridges
- booking/stateful collect flows
- multi-pack acceptance work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-service-not-found-owner-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
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
2. Extend master-query accept gates to the actual truth metadata shape.
3. Add a bounded grounded `service_not_found` collect owner path reusing the shared collect finalizer.
4. Add focused positive/fallback regression coverage.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- approved grounded `master_query service_not_found` replies bypass frozen `decision.py`
- bounded `master_query service_clarify` accept gate matches the actual pack metadata shape
- malformed `service_not_found` envelopes still fall back to legacy delegate
- no new bridge family is introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'master_query_collect_owner or master_query_service_not_found_owner or master_query_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core regression for grounded `master_query service_not_found` owner bypass
- fallback regression for malformed `service_not_found` metadata
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + contracts + architecture only for this bounded slice
- **Stop condition:** if the candidate needs new bridge growth or broader stateful master/booking semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement only; no new entrypoints or bridge families
- **Go/no-go signals:** reasoning-core + contracts + architecture suites green, semantic bridge growth guard green
- **Rollback:** revert the owner cutover change, tests, and doc sync
- **Post-release monitoring window:** next block must either delete another owner seam or move to boundary/continuity completion without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the master-query service-not-found owner cutover and generated packet output.

## Rollback
1. Revert the master-query service-not-found owner path, tests, and doc sync.
2. Regenerate packet.
3. Re-run reasoning-core/architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader specialist or booking stateful semantics
- no counting this block as progress unless grounded `service_not_found` becomes direct-owner

## Risks / blockers
- if the grounded `service_not_found` reply needs broader handoff or manager semantics in hidden branches, the cutover would be unsafe
- if accept gates are too loose, malformed master-query replies could bypass legacy incorrectly

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader semantic owner still remains in frozen legacy
  - boundary owner is still partial
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one more bounded master-query seam
- **Risk if deferred:**
  - grounded `master_query` turns would keep re-entering legacy even when truth metadata is deterministic enough for direct owner completion
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement or boundary-owner block
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate requires bridge growth or frozen-router edits

## Next-block contract (mandatory)
- **Next block objective:** next bounded owner-replacement or boundary-owner seam that deletes another legacy authority without new bridge growth
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k 'owner_cutover'`
- **Blocked-by conditions:** if the next candidate needs broader stateful collect/handoff behavior or frozen-router edits
- **Owner role for closure:** `Top Architect`
