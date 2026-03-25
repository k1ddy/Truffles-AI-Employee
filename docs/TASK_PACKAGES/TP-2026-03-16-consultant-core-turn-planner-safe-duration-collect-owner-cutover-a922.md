# TP-2026-03-16-consultant-core-turn-planner-safe-duration-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-DURATION-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-VALIDATOR-BLOCK-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-NEXT-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить еще один bounded legacy semantic seam без bridge growth: перевести deterministic `duration` `service_clarify` collect path из frozen delegate в прямой owner path внутри `truffles-api/app/services/reasoning_core.py`, реиспользуя уже существующий collect finalizer.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1220,2125p' truffles-api/app/services/reasoning_core.py`
  - `python3 - <<'PY' ... info._build_info_intent_reply('duration', service_query=None, client_slug='demo_salon', message_text='Сколько длится?') ... PY`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'pricing_collect_owner or master_query_collect_owner or duration_collect_override'`
- `FACT findings`:
  - `reasoning_core` already owns bounded `pricing` and `master_query` collect cutovers through the shared collect finalizer.
  - bounded `duration` `service_clarify` policy override already exists, but there is still no direct owner cutover for it, so the runtime still re-enters frozen `decision.py` for that deterministic normal path.
  - the existing duration truth helper already returns a stable non-empty service-clarify reply for missing-service turns, but the current direct owner inventory does not accept or finalize that path.
- `Detected drift (docs vs code)`: execution strategy lock says the next valid move is richer semantic owner cutover via `turn_planner`, yet duration collect remains only an override bridge.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict.copy official docs`
- **Date/time (local):** `2026-03-16 23:52 +0500`
- **Why this query is precise:** the block reuses reply meta from existing truth helpers and must preserve detached-copy semantics when normalizing metadata for the direct owner finalizer.
- **Sources opened (from this query):**
  - `Built-in Types — dict.copy` — `https://docs.python.org/3/library/stdtypes.html#dict.copy`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dict.copy()` is the standard shallow-copy mechanism for preserving detached top-level mutation semantics when normalizing metadata.
- **Decision:** `reuse + integrate` — reuse existing duration truth helper output and normalize copied metadata inside the direct owner path instead of inventing a new collect response builder.
- **Rejected options:**
  - adding another ingress bridge family
  - touching frozen router files
  - widening immediately into broader duration/pricing truth-gate semantics
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic service-missing `duration` turns still fall back into frozen `decision.py` even though the same path already has a policy override and a reusable collect finalizer.
- **Minimal reproduction:**
  1. Inspect `_try_handle_turn_planner_safe_pricing_collect_owner_cutover(...)` and `_try_handle_turn_planner_safe_master_query_collect_owner_cutover(...)`.
  2. Observe there is no matching duration collect owner path.
  3. Trigger the existing duration collect override and note that the request still delegates to the frozen router.
- **Evidence to capture:**
  - new direct owner path bypasses frozen delegate for approved deterministic duration service-clarify replies
  - non-approved duration reply envelopes still fall back cleanly to legacy delegate
- **Five Whys (or equivalent):**
  1. Why does duration collect still hit frozen legacy? Because no direct owner cutover exists for that bounded override.
  2. Why was it left behind? Because earlier collect owner work focused first on pricing and master-query seams that already had obviously collect-shaped helper output.
  3. Why is it safe now? Because the semantic owner already says `duration` + `collect`, and the reply text is deterministic truth-backed missing-service clarification.
  4. Why not broaden into all duration/truth-gate semantics? Because only the missing-service bounded collect seam is deterministic enough for owner replacement without widening stateful behavior.
  5. Why do this now? Because the strategy lock requires richer owner replacement, and this block deletes an existing legacy semantic seam without bridge growth.
- **Root cause statement:** the runtime already has the semantic decision and finalization machinery for duration service-clarify, but it still lacks the bounded direct owner path that would make frozen legacy unreachable for that normal path.
- **Fix mechanism:**
  - add a safe duration collect owner candidate + acceptance gate in `reasoning_core`
  - reuse existing deterministic duration reply generation
  - finalize through the shared collect owner path and keep unsafe envelopes on legacy fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `TurnPlanner.build_from_policy_override(...)`
  - `_finalize_turn_planner_owner_cutover(...)`
  - existing duration collect policy override
  - existing duration truth helper output
- **External reuse:**
  - official Python `dict.copy()` docs
- **Why not reinvent the wheel:** the block only fills the missing direct owner path around already-existing semantic and continuity contracts.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded owner-replacement cutover plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new generic ingress bridge family.
- No widening into grounded duration fact or other truth-gate paths.
- Non-approved duration reply envelopes must still fall back to legacy delegate before persistence.

## Scope
- Add a bounded duration collect owner candidate in `reasoning_core`.
- Reuse the shared collect finalizer for approved duration service-clarify replies.
- Add focused regression coverage and sync canon/session artifacts.

## Out of scope
- changes to frozen `decision.py` / `booking.py` / `pending.py`
- broader duration truth-gate rewrite
- new ingress bridges
- boundary-owner work beyond existing current block closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-duration-collect-owner-cutover-a922.md`
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
2. Add a bounded safe duration collect owner path in `reasoning_core`.
3. Reuse existing deterministic duration reply generation and shared collect finalizer.
4. Add focused positive/fallback regression coverage.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` directly owns deterministic `duration` `service_clarify` collect replies for the approved bounded envelope.
- frozen `decision.py` is unreachable for that approved normal path.
- non-approved duration collect envelopes still fall back cleanly to legacy delegate.
- no new bridge family is introduced.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'duration_collect_owner or pricing_collect_owner or master_query_collect_owner'`
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
- reasoning-core regression for duration collect owner bypass
- fallback regression for unapproved duration reply envelope
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + architecture only for this bounded slice
- **Stop condition:** if the candidate needs new phrase bridges or broader truth-gate rewrite, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement only; no new entrypoints or bridge families
- **Go/no-go signals:** targeted and full reasoning-core checks green, architecture/guard checks green
- **Rollback:** revert reasoning-core direct owner path, tests, and doc sync
- **Post-release monitoring window:** next block should either delete another owner seam or return to boundary/continuity completion without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the duration collect owner cutover and generated packet output.

## Rollback
1. Revert the duration collect owner path, tests, and doc sync.
2. Regenerate packet.
3. Re-run reasoning-core/architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no bridge growth counted as progress
- no widening into broader duration/pricing truth semantics

## Risks / blockers
- if the duration reply helper emits a non-deterministic or fact-shaped envelope outside the approved bounded pattern, the path must stay on legacy fallback
- if saved metadata becomes inconsistent with collect continuity, the block must stop and tighten the acceptance gate

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader semantic owner still remains in frozen legacy
  - boundary owner is still partial
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one deterministic duration collect seam
- **Risk if deferred:**
  - duration service-missing turns would continue to depend on the frozen router despite already having policy override + collect finalizer infrastructure
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement or boundary-owner block
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate requires new bridge growth or frozen-router edits

## Next-block contract (mandatory)
- **Next block objective:** next bounded owner-replacement or boundary-owner seam that deletes another legacy authority without new bridge growth
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k 'owner_cutover'`
- **Blocked-by conditions:** any candidate requiring frozen-router edits, new ingress bridge growth, or broader stateful booking semantics
- **Owner role for closure:** `Top Architect`
