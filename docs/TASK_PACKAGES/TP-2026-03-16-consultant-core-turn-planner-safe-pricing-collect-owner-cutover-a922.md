# TP-2026-03-16-consultant-core-turn-planner-safe-pricing-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-PRICING-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NEXT-COLLECT-OWNER-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Расширить `turn_planner` owner replacement на следующий bounded `COLLECT` normal path: deterministic pricing `service_clarify`. Если ingress уже имеет existing `pricing` collect policy override, `reasoning_core` должен завершать turn напрямую через existing collect finalization path, а не входить в frozen `truffles-api/app/routers/webhook/decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/semantic_bridge_growth_guard.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1260,2060p' truffles-api/app/services/reasoning_core.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'pricing_collect_owner or master_query_owner'`
- `FACT findings`:
  - Existing `reasoning_core` already owns bounded grounded pricing FACT turns through the safe service-query owner cutover.
  - Existing pricing collect policy override already produces a typed `PolicyDecision` candidate with `intent="pricing"`, `action="collect"`, `tool_action="info"`, and a service question contract.
  - Existing collect finalizer already knows how to persist bounded expected-reply/question-contract/canonical dialog-state state via `DialogStateService`.
  - Existing pure helper `app.routers.webhook.info._build_info_intent_reply(...)` already produces deterministic pricing service-clarify replies from pack truth without needing frozen `decision.py`.
- `Detected drift (docs vs code)`: the new core already has the typed decision plus collect finalization primitives for this bounded pricing seam, but still re-enters frozen legacy because there is no direct owner cutover for the deterministic pricing clarify envelope.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict get official docs`
- **Date/time (local):** `2026-03-16 23:29 +0500`
- **Why this query is precise:** the new acceptance gate is intentionally dict-driven and must inspect bounded reply metadata conservatively without widening missing-key semantics into false acceptance.
- **Sources opened (from this query):**
  - `Python Standard Type Hierarchy / dict methods` — `https://docs.python.org/3/library/stdtypes.html#dict.setdefault`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python dict access/default semantics are explicit and stable; bounded acceptance can safely rely on strict token checks instead of permissive fallback defaults.
- **Decision:** `reuse + integrate` — keep the pricing collect owner gate as a narrow metadata acceptance check around existing `_build_info_intent_reply(...)` output instead of adding any new routing bridge or broader parser.
- **Rejected options:**
  - new ingress phrase bridge family
  - widening immediately into duration collect or `service_not_found`
  - direct raw context mutation in `reasoning_core`
  - touching frozen `decision.py` / `booking.py` / `pending.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic pricing `service_clarify` turns like `Сколько стоит?` still enter frozen `decision.py` even though the same policy override, reply helper, and collect-state materialization path already exist outside legacy.
- **Minimal reproduction:**
  1. Prime the existing pricing collect policy override.
  2. Let `_build_info_intent_reply(...)` return a deterministic truth-backed pricing `service_clarify` collect reply.
  3. Observe that `reasoning_core` still delegates because there is no bounded pricing collect owner path.
- **Evidence to capture:**
  - safe pricing collect replies bypass frozen `decision.py`
  - expected reply + canonical dialog state are materialized by the new core
  - unsupported collect envelopes still fall back to legacy delegate
- **Five Whys (or equivalent):**
  1. Why does the pricing collect turn still hit legacy? Because owner replacement currently handles pricing FACT only.
  2. Why is that no longer sufficient? Because the shared collect finalizer already exists and can persist the bounded service-question contract safely.
  3. Why not cut over all info collect paths now? Because broader collect families still carry mixed semantics and larger state-risk envelopes.
  4. Why is this block safe? Because it accepts only one deterministic envelope: pricing + truth-backed `service_clarify` + bounded service question contract.
  5. Why do this now? Because it deletes another legacy semantic seam without any new bridge growth.
- **Root cause statement:** the new runtime already has a typed pricing collect decision and a bounded collect-state finalizer, but lacks a direct owner cutover that accepts only the deterministic pricing `service_clarify` reply envelope.
- **Fix mechanism:**
  - add a bounded pricing collect candidate/acceptance gate in `reasoning_core`
  - reuse `_build_info_intent_reply(...)` for deterministic reply generation
  - finalize the accepted reply through the existing collect owner path and continuity owner

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `TurnPlanner.build_from_policy_override(...)`
  - `DialogStateService.build_collect_owner_state(...)`
  - existing `_finalize_turn_planner_owner_cutover(...)`
  - `app.routers.webhook.info._build_info_intent_reply(...)`
- **External reuse:**
  - official Python dict semantics documentation
- **Why not reinvent the wheel:** this block only adds the missing bounded owner gate around already-existing typed decision, reply builder, and collect-state persistence seams.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement cutover plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Only deterministic pricing `service_clarify` becomes direct-owner.
- Unsupported collect replies still fall back to legacy.

## Scope
- Add one bounded pricing collect candidate/acceptance gate in `reasoning_core`.
- Reuse the existing collect finalizer for safe pricing clarify replies.
- Add focused regression coverage and sync canon/session artifacts.

## Out of scope
- duration collect owner cutover
- pricing `service_not_found`
- master-query changes
- booking/handoff/stateful outcome ownership
- frozen legacy semantic files
- new semantic bridge families

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-pricing-collect-owner-cutover-a922.md`
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
2. Add a bounded pricing collect owner candidate and acceptance gate in `reasoning_core`.
3. Reuse `_build_info_intent_reply(...)` plus the shared collect finalizer for the accepted envelope.
4. Add regression coverage for direct-owner bypass and unsupported collect fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic pricing `service_clarify` replies bypass frozen `decision.py`
- collect owner path writes expected reply + canonical dialog state through the existing continuity owner
- unsupported pricing collect envelopes still fall back to legacy delegate
- no new bridge family is introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'pricing_collect_owner or master_query_owner'`
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
- reasoning-core tests proving safe pricing collect bypass and unsupported collect fallback
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + contracts + architecture only for this bounded block
- **Stop condition:** if the pricing collect owner path needs broader duration/multi-intent/stateful booking semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement extension only; no new entrypoints or semantic bridges
- **Go/no-go signals:** reasoning-core + contracts + architecture suites green; continuity and semantic bridge guards green
- **Rollback:** revert the pricing collect owner gate, tests, and doc sync
- **Post-release monitoring window:** next block should either extend one more safe owner seam or move to a larger planner/outcome cutover without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe pricing collect owner cutover and generated packet output.

## Rollback
1. Revert the pricing collect owner gate, regression tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into duration, `service_not_found`, booking, or handoff semantics
- no counting this block as done unless deterministic pricing `service_clarify` becomes direct-owner and unsupported collect replies still fall back

## Risks / blockers
- if the pricing clarify helper emits broader collect envelopes than expected, the acceptance gate could become unsafe
- if the collect finalizer still depends on hidden state-restore semantics, direct-owner cutover would be unsafe

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader collect/handoff stateful outcomes still remain on the legacy delegate
  - proof path is still not fully black-box
  - boundary owner is still legacy-mixed
- **Why not in this block:**
  - this block only deletes one deterministic pricing collect envelope
- **Risk if deferred:**
  - frozen `decision.py` would keep owning a collect seam that the new core can already realize safely and contract-first
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement TP after this cutover, or boundary-owner cutover if no next safe seam remains
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate needs broader duration, booking mutation, handoff creation, or new bridge growth

## Next-block contract (mandatory)
- **Next block objective:** next richer owner-replacement seam that deletes another legacy semantic path without new bridge growth; if no bounded semantic seam remains, switch to boundary-owner cutover instead of returning to micro-bridges
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k 'owner_cutover and not delegate'`
- **Blocked-by conditions:** any candidate that needs booking mutation, handoff queue creation, duration collect widening, or frozen-router edits
- **Owner role for closure:** `Top Architect`
