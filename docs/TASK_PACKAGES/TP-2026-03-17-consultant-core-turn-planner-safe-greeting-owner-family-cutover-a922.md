# TP-2026-03-17-consultant-core-turn-planner-safe-greeting-owner-family-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-GREETING-OWNER-FAMILY-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-EXPLICIT-HANDOFF-FAMILY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-explicit-handoff-owner-family-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-GREETING-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий admissible deterministic controller family: ingress lexical greeting routes should no longer enter frozen `truffles-api/app/routers/webhook/decision.py` before persistence. This block must consume the existing `ingress_lexical_greeting` controller snapshot family and directly materialize the bounded greeting/thanks/ack smalltalk replies through typed owner artifacts, without widening into `out_of_domain` or style-reference behavior.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-explicit-handoff-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "ingress_lexical_greeting|ControllerRouteSnapshot|OwnerCutoverAction|GREETING_RESPONSE|THANKS_RESPONSE|ACKNOWLEDGEMENT_RESPONSE" truffles-api/app/core/intent_routing.py truffles-api/app/core/turn_executor.py truffles-api/app/services/ai_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `sed -n '235,280p' truffles-api/app/core/intent_routing.py`
  - `sed -n '140,147p' truffles-api/app/services/ai_service.py`
  - `sed -n '3800,4185p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - greeting/thanks/ack are already normalized as one controller snapshot family with reason `ingress_lexical_greeting`
  - `reasoning_core` still only primes the controller override and then delegates the family into frozen `decision.py`
  - reply text for this family already exists as stable deterministic constants in `ai_service.py`
  - `out_of_domain` remains mixed with firebreak/AI-response semantics and is not the next safe family
- `Detected drift (docs vs code)`: execution strategy now forbids new bridge growth and demands richer owner deletions, but the deterministic greeting family still relies on legacy controller execution despite already having a bounded snapshot contract and deterministic reply surface.

## One web search (mandatory before implementation)
- **Query (exact):** `Python typing Literal official docs`
- **Date/time (local):** `2026-03-17 12:56 +0500`
- **Why this query is precise:** the block needs a typed extension of `OwnerCutoverAction` so the owner artifact can record `smalltalk` without widening the contract back to untyped `str`.
- **Sources opened (from this query):**
  - `typing — Support for type hints / typing.Literal` — `https://docs.python.org/3/library/typing.html#typing.Literal`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `typing.Literal` is the correct narrow type surface for extending a closed action union without weakening contract typing.
- **Decision:** `reuse/integrate` — extend `OwnerCutoverAction` with `"smalltalk"` and keep the owner artifact contract typed.
- **Rejected options:**
  - widening owner action typing to generic `str`
  - adding another ingress detector family instead of consuming the existing controller snapshot family
  - widening the block into `out_of_domain`
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** greeting/thanks/ack turns still depend on frozen `decision.py`, even though ingress already emits them as one bounded controller snapshot family.
- **Minimal reproduction:**
  1. Inspect `detect_controller_route_snapshot(...)` in `truffles-api/app/core/intent_routing.py`.
  2. Observe that greeting/thanks/ack are already normalized to `reason="ingress_lexical_greeting"`.
  3. Inspect `reasoning_core.handle_webhook_payload(...)` and confirm it only stores the controller override before delegating into frozen `decision.py`.
  4. Inspect `TurnExecutor` and observe that owner artifact typing still lacks a dedicated `smalltalk` action.
- **Evidence to capture:**
  - direct owner bypass for greeting, thanks, and acknowledgement messages
  - owner artifact / turn outcome uses typed `action="smalltalk"`
  - `out_of_domain` controller route still cleanly delegates
  - fallback-to-delegate remains clean when routing disallows bot replies
- **Five Whys (or equivalent):**
  1. Why does the family still hit legacy? Because no direct owner handler consumes the controller snapshot family.
  2. Why is a new bridge not needed? Because the family is already emitted by existing ingress/controller snapshots.
  3. Why is this family safe now? Because reply text is deterministic and already lives in reusable constants.
  4. Why not take `out_of_domain` with it? Because `out_of_domain` still mixes controller routing with firebreak/AI-response semantics and is not a deterministic smalltalk family.
  5. Why is `TurnExecutor` part of the root cause? Because the typed owner action set still cannot express `smalltalk` directly.
- **Root cause statement:** ingress already exposes one deterministic greeting controller family, but new-core execution still lacks a typed direct owner path for smalltalk completion, so greeting/thanks/ack turns continue falling through frozen `decision.py`.
- **Fix mechanism:**
  - extend typed owner action support in `TurnExecutor` to include `smalltalk`
  - add one bounded `reasoning_core` direct owner handler for the `ingress_lexical_greeting` controller family
  - reuse existing deterministic reply constants and fall back to legacy when routing does not allow bot replies or when the family is not the bounded greeting family

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ingress_lexical_greeting` controller snapshot in `truffles-api/app/core/intent_routing.py`
  - existing `TurnExecutor.build_owner_cutover_artifact(...)`
  - existing `_finalize_turn_planner_owner_cutover(...)`
  - existing deterministic reply constants and signal helpers in `truffles-api/app/services/ai_service.py`
- **External reuse:**
  - official Python `typing.Literal` documentation for the typed owner-action extension
- **Why not reinvent the wheel:** the snapshot family and reply texts already exist, so this block should consume them directly instead of adding another bridge or rebuilding smalltalk logic inside frozen legacy.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded controller-owner deletion plus a typed owner-action extension and focused contract coverage.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into `out_of_domain` or style-reference behavior.
- Greeting owner path must only take over when routing allows bot replies; otherwise it must fall back to legacy before persistence.

## Scope
- Extend `TurnExecutor` typed owner action support for smalltalk completion.
- Add one bounded `reasoning_core` direct owner handler for the lexical greeting controller family.
- Add focused reasoning-core and runtime-contract tests.
- Sync canon/session artifacts if the block is green.

## Out of scope
- `out_of_domain`
- style reference
- generic controller-route refactor
- frozen router files
- broader pending/manager-active state semantics
- proof-path or multi-pack work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-greeting-owner-family-cutover-a922.md`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
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
2. Extend `OwnerCutoverAction` with typed `smalltalk` support.
3. Implement a bounded `reasoning_core` direct owner handler for `ingress_lexical_greeting`.
4. Reuse deterministic smalltalk constants for greeting/thanks/ack and fall back to legacy when routing disallows bot replies.
5. Add focused direct-owner and contract tests, including a non-widening guard for `out_of_domain`.
6. Run focused and full validations.
7. Sync canon/session artifacts only if the block is green.

## DoD
- greeting/thanks/ack turns bypass frozen `decision.py` through a typed direct owner path
- owner artifact / turn outcome records `action="smalltalk"`
- direct-owner tests prove greeting, thanks, and acknowledgement replies
- `out_of_domain` controller route still delegates
- no new bridge families and no frozen-router edits

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'greeting_owner or controller_route_override_for_out_of_domain_delegate'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- direct-owner reasoning-core tests for greeting/thanks/ack plus fallback/non-widening coverage
- runtime-contract test proving typed `action="smalltalk"`
- green full reasoning-core/runtime-contract/architecture checks
- updated source-of-truth / packet showing the greeting family cutover

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** focused greeting owner tests first, then full reasoning-core + contracts + architecture
- **Stop condition:** if the greeting family cannot be deleted through the existing controller snapshot and deterministic reply surface without widening into `out_of_domain`, stop and return to richer audit instead of forcing another bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-family deletion only; no new entrypoints
- **Go/no-go signals:** focused greeting-owner tests + full reasoning-core/contracts/architecture green; packet/session gates green
- **Rollback:** revert the owner-path, typed action extension, tests, and doc sync
- **Post-release monitoring window:** next block should return to richer owner audit instead of taking another controller micro-slice by inertia

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - canon may count the lexical greeting family as deleted only if greeting/thanks/ack direct-owner paths are proven and `out_of_domain` still delegates.

## Rollback
1. Revert the turn-executor / reasoning-core / test / doc changes for this block.
2. Regenerate packet.
3. Re-run guards.

## No-go
- no frozen-router edit
- no new detector family
- no widening into `out_of_domain`
- do not count the block as done unless the bounded greeting family is proven through direct-owner tests

## Risks / blockers
- if the owner path replies when routing disallows bot replies, state-dependent pending behavior regresses
- if the block silently widens into `out_of_domain`, it stops being the bounded deterministic deletion justified by the audit

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `out_of_domain` controller route remains legacy-owned
  - single continuity writer is still not fully closed
  - boundary owner remains only partially cut over
- **Why not in this block:**
  - `out_of_domain` still mixes controller routing with firebreak/AI-response semantics and is not the same deterministic family
- **Risk if deferred:**
  - greeting smalltalk remains an existing deterministic family that still depends on frozen `decision.py`
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - once the lexical greeting family is closed, the next move must return to richer owner audit instead of taking `out_of_domain` by inertia

## Next-block contract (mandatory)
- **Next block objective:** `richer_owner_replacement_audit_after_safe_greeting_owner_family_cutover`
- **First deterministic check command:** `rg -n "ingress_domain_router_out_of_domain|style_reference_text|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py`
- **Blocked-by conditions:** lack of a broader admissible owner seam without new bridge growth
- **Owner role for closure:** `Top Architect`
