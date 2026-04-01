# TP-2026-03-27-consultant-core-workstream1-memory-profile-canonical-read-cut-a922

Название/цель:
- Следующий крупный bounded cut внутри Workstream 1: убрать remaining pre-owner semantic authority из `ConsultantRuntime._build_policy_core_memory_profile(...)`.
- Сделать так, чтобы owner-facing `memory_profile` читал semantic carry-over только из canonical `semantic_state`, а legacy runtime carriers больше не могли заново задавать смысл следующему owner turn.

Canon refs:
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `STATE.md` NOW: `workstream1_runtime_owner_precedence_cut`

Invariant:
- `SemanticDecisionV1` remains the only hot-path semantic owner.
- Pre-owner memory may carry forward canonical semantic state, but may not reconstruct meaning from legacy runtime compatibility carriers.
- Operational carry-over such as booking slot state may remain, but it may not silently fabricate semantic contract or pending-question meaning.

Scope:
- `truffles-api/app/core/consultant_runtime.py`
- targeted regressions in `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

Out of scope:
- legacy webhook strangler
- `booking_prompt_owner.py` dormant path redesign
- TurnJournal / ConversationProjection implementation
- llm-quality acceptance

Touch-list:
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-memory-profile-canonical-read-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

Work mode:
- implementation

One web search (mandatory before implementation):
- Query: `site:docs.python.org Python copy deepcopy documentation`
- Date/time: `2026-03-27 Asia/Almaty`
- Opened sources:
  - `https://docs.python.org/3/library/copy.html`
- Source quality:
  - high-signal official Python documentation
- Found reusable solution:
  - `copy.deepcopy(...)` isolates nested mutable structures so later writes cannot mutate the source object graph.
- Decision:
  - `reuse/integrate`
  - use `deepcopy` when materializing owner-facing memory-profile semantic payloads from canonical state so downstream normalization/merge steps cannot mutate canonical nested referents or pending-question payloads in place.
- Rejected options:
  - shallow `dict(...)` copies only — rejected because nested `referents` / `entity_refs` / `open_questions` payloads would still alias the canonical state structures.

Root cause (mandatory):
- Symptom:
  - even after runtime owner-first reads, the next owner call can still receive stale semantic meaning through `memory_profile` because `_build_policy_core_memory_profile(...)` reads `project_runtime_*` helpers that fall back to legacy `meta.semantic_contract`, `pending_question_contract`, and projection fields when canonical semantic state is absent.
- Minimal reproduction:
  - construct a `DialogState` with no usable `semantic_state`, populate stale `meta.semantic_contract`, `pending_question_contract`, and `meta.current_goal`, then build `memory_profile`.
  - current runtime sends those legacy semantic fields back into the next owner call as if they were canonical carry-over.
- Evidence:
  - `truffles-api/app/core/consultant_runtime.py:606-690`
  - `truffles-api/app/core/dialog_state_service.py:866-939`
  - `docs/system_forensics/files/app_core_consultant_runtime.md`
- Five Whys:
  1. Why does stale meaning reach the next owner call? Because memory-profile assembly reads `project_runtime_semantic_frame/contract/pending_question_contract`, which still project from legacy carriers when canonical state is missing.
  2. Why is that wrong? Because `memory_profile` is pre-owner context; if it replays legacy semantic carriers as truth, the next owner turn is being seeded by non-owner semantic authority.
  3. Why doesn't the previous runtime owner-first cut solve this? Because that cut only fixed post-owner runtime reads; `_build_policy_core_memory_profile(...)` still runs before the next owner call.
  4. Why is this dangerous? Because stale legacy state can bias or rewrite the next semantic owner decision without any explicit degrade or reason-code.
  5. Why does this block Workstream 1 completion? Because pre-owner memory remains a live owner-adjacent semantic authority path, so legacy owner-adjacent paths are not yet shadow-only.
- Root cause statement:
  - `ConsultantRuntime._build_policy_core_memory_profile(...)` still reconstructs owner-facing meaning from legacy runtime compatibility projections instead of reading only canonical semantic state plus bounded operational carry-over.
- Fix mechanism:
  - build memory-profile semantic fields (`active_goal`, `semantic_contract`, `pending_question_contract`) from canonical `semantic_state.materialized_frame` only; keep `slot_state` as bounded operational carry-over; deep-copy canonical nested payloads before emitting them.

Plan:
1. Add canonical-only semantic-state reads inside `_build_policy_core_memory_profile(...)`.
2. Remove legacy `project_runtime_*` fallback usage from pre-owner memory-profile assembly.
3. Preserve bounded operational carry-over for booking slot state and booking fallback goal only.
4. Add regressions proving stale legacy `meta.semantic_contract`, `pending_question_contract`, and `meta.current_goal` do not survive into owner-facing `memory_profile` without canonical semantic state.
5. Run deterministic checks.
6. Update `STATE.md` and `STRUCTURE.md` truthfully.

DoD:
- Owner-facing `memory_profile.semantic_contract` is absent unless it comes from canonical semantic state.
- Owner-facing `memory_profile.pending_question_contract` is absent unless it comes from canonical semantic state.
- Legacy `meta.current_goal` does not become `memory_profile.active_goal` when canonical semantic state is absent.
- Bounded `slot_state` carry-over still works.
- Deterministic regressions pass.

Checks:
- `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "memory_profile and (canonical or legacy or slot_state or semantic_state)"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

Evidence:
- changed authority map in code
- deterministic test output
- updated `STATE.md`
- updated `STRUCTURE.md`

Rollback:
- Revert only the touched runtime/test/doc files from this TP.
- If canonical-only memory-profile reads break unrelated deterministic flows, narrow the cut to semantic fields only; do not restore legacy semantic fallback.

No-go:
- no new semantic hardcode in runtime core
- no new semantic fallback to `meta.semantic_contract` / `pending_question_contract`
- no widening into webhook legacy mesh in this block
- no llm-quality claims without actual run evidence

Risks/blockers:
- Some old tests may still model pre-canonical dialog state payloads and will need explicit canonical fixtures instead of hidden legacy fallback.
- Over-tightening could accidentally remove bounded operational slot carry-over if assertions are too broad.

Residual architecture debt (mandatory):
- Current residuals accepted in this block:
  - legacy webhook compatibility readers remain outside runtime core
  - dormant `booking_prompt_owner.py` second-lane residue remains in repo
  - canonical state bootstrap still has legacy fallback code inside `DialogStateService`
- Why not in this block:
  - this block is limited to pre-owner runtime memory-profile authority, not full legacy strangler or canonical bootstrap redesign.
- Risk if deferred:
  - the next owner call could still be shaped by legacy compatibility readers outside runtime core even after this cut.
- Linked follow-up Task Package(s):
  - `TP-2026-03-27-consultant-core-workstream1-runtime-owner-precedence-cut-a922.md`
  - next TP TBD for legacy webhook compatibility readers
- Expiry/trigger to stop deferral:
  - if any owner-facing memory-profile semantic field still originates from legacy runtime carriers after this block, deferral expires immediately.

Next-block contract (mandatory):
- Next block objective:
  - close the remaining owner-adjacent legacy readers in the active webhook compatibility mesh.
- First deterministic check command:
  - `rg -n "semantic_contract|pending_question_contract|memory_profile|llm_policy_core\.payload" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/_legacy.py truffles-api/app/services/reasoning_core.py`
- Blocked-by conditions:
  - consultant runtime memory-profile still emits semantic carry-over from legacy runtime carriers
  - canaried owner turns still accept stale semantic carry-over before owner issuance
- Owner role for closure:
  - Brain / Top Architect

## Implementation result
- Status: completed for this bounded family.
- Authority removed:
  - pre-owner `memory_profile` no longer reconstructs semantic carry-over from legacy runtime carriers (`meta.semantic_contract`, `pending_question_contract`, `meta.current_goal`) when canonical semantic state is absent.
  - the next owner call now sees semantic carry-over only from canonical `semantic_state`, plus bounded operational slot carry-over.
- Files touched:
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-memory-profile-canonical-read-cut-a922.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Deterministic checks:
  - `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "memory_profile and (canonical or legacy or slot_state or semantic_state or continuity)"` -> `5 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `74 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `24 passed`
  - `git diff --check` -> `pass`
- Residual debt left for next block:
  - active webhook compatibility readers still consume/write owner-adjacent semantic carriers outside runtime core
  - dormant `booking_prompt_owner.py` second-lane residue remains in repo
  - canonical bootstrap in `DialogStateService` still contains legacy fallback code for non-canonical payloads
