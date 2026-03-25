# TP-2026-03-25 Consultant Core Canonical Semantic Query Substrate + Booking Prompt Owner A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-SEMANTIC-QUERY-SUBSTRATE-BOOKING-PROMPT-OWNER-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `9636381f`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `UNLOCKS`: removal of one more shadow semantic dialect by making deterministic booking-owner boundary helpers query the same canonical semantic contract instead of split legacy fields

## Название/цель
Закрыть следующий bounded shadow path after `semantic_contract.v1`: deterministic booking-owner compatibility helpers still read user meaning through split legacy semantic fields and router-local helper heuristics instead of the canonical semantic contract. This block moves that query layer onto one canonical semantic substrate and removes one more semantic dialect from the system.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_owner_resolver.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `git status --short --branch` is clean after commit `9636381f`.
- `app/core/booking_prompt_owner.py` is not imported by active runtime code; repo search shows it is referenced only by its own file and tests.
- `app/routers/webhook/decision.py` still contains a large cluster of legacy semantic helper functions (`_extract_semantic_specialist_preference`, `_should_preserve_*`, `_resolve_policy_collect_interrupt_arbitration`) that interpret split semantic fields outside the canonical `semantic_contract`.
- `app/core/booking_prompt_owner.py` still imports those router helpers directly and builds `memory_profile` without passing through the canonical `semantic_contract`.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses official docs`
- **Date/time (local):** 2026-03-25 19:27:00 +05
- **Sources opened:**
  - Python official docs, `dataclasses — Data Classes` — `https://docs.python.org/3/library/dataclasses.html`
- **Existing solutions found:** the Python stdlib already provides lightweight immutable/frozen dataclass support suitable for a bounded canonical semantic view/query object; no extra framework or second schema system is needed.
- **Decision:** reuse the existing `app/services/owner_resolver.py` deterministic boundary module and add a small immutable semantic-contract query view there instead of introducing another ad hoc dict dialect or another modeling stack.
- **Rejected options:**
  - keeping router-local helper heuristics as a second semantic query substrate
  - adding post-hoc semantic repair inside booking prompt owner
  - introducing a new external modeling layer for this bounded deterministic query step
- **Source quality:** official Python primary source

## Root cause (mandatory)
- **Symptom:** one more shadow semantic dialect remains after `semantic_contract.v1`: deterministic booking-owner helpers still inspect meaning through split fields (`subject_kind`, `capability`, `pending_question_target`, `entity_refs`, `tool_args`) and router-local heuristics instead of querying the canonical semantic contract.
- **Minimal reproduction:** inspect `app/core/booking_prompt_owner.py` and `app/routers/webhook/decision.py`; compare their helper contracts to `dialog_state.meta["semantic_contract"]` and the new active runtime path.
- **Evidence:**
  - `truffles-api/app/core/booking_prompt_owner.py`
  - `truffles-api/app/services/owner_resolver.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - repo search showing no active runtime imports of `booking_prompt_owner`
- **Five Whys:**
  1. Why is there still semantic drift? Because deterministic owner-boundary helpers still read split semantic fields directly.
  2. Why do they read split fields directly? Because they predate the canonical `semantic_contract` and kept their own helper predicates.
  3. Why is that risky? Because the same meaning can now be represented in both `semantic_contract` and router-local helper arguments, and those can diverge.
  4. Why does that matter if the path is bounded/compatibility-only? Because keeping a second query dialect alive expands future failure families and keeps tests coupled to shadow semantics.
  5. Why is this a semantic-protocol issue rather than pure cleanup? Because the defect is still “multiple layers speak different semantic languages” even when the helpers are deterministic.
- **Root cause statement:** the system still has a shadow deterministic semantic-query substrate for booking-owner compatibility logic; it interprets split legacy semantic fields instead of querying the canonical `semantic_contract`, so semantic meaning can drift even after the active runtime path was aligned.
- **Fix mechanism:** centralize those deterministic semantic queries in one canonical view/query helper inside `owner_resolver`, feed `booking_prompt_owner` from the canonical contract/memory profile, and make legacy router helpers thin compatibility wrappers over the same canonical query substrate.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `semantic_contract.v1` already persisted in runtime state and memory profile
  - `DialogStateService.load_runtime_payload()` for canonical continuity loading
  - `app/services/owner_resolver.py` as the deterministic owner-boundary seam
- **External reuse:** Python stdlib `dataclasses`
- **Why not reinvent the wheel:** the missing piece is not another schema or router; it is one shared deterministic query surface over the already-landed canonical semantic contract.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 1
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** the block is a bounded deterministic semantic-query migration and test alignment, not a runtime architecture reset.

## Invariant
- Policy-core remains the only semantic owner.
- Deterministic layers only query, validate, persist, or preserve the canonical semantic contract; they do not reinterpret raw user text.
- No new phrase/regex semantic branching is introduced.
- No booking-only local hack justified as substrate work.

## Scope
- add one canonical deterministic semantic query view over `semantic_contract`
- migrate `booking_prompt_owner` to query canonical semantic state instead of router-local semantic helpers
- make legacy router semantic helper functions thin compatibility wrappers over the same query substrate or delete clearly dead local-only logic if now unnecessary
- add/update focused tests proving canonical semantic contract reaches the compatibility boundary

## Out of scope
- active runtime owner changes
- retrieval/transport changes
- full deletion of `app/routers/webhook/decision.py`
- acceptance baseline refresh

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-query-substrate-booking-prompt-owner-a922.md`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_owner_resolver.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`

## Plan (1..N)
1. Define a canonical deterministic semantic query view in `owner_resolver` over `semantic_contract` + referents/entity refs.
2. Migrate `booking_prompt_owner` to use that view and pass canonical semantic contract in its policy-core memory profile when available.
3. Convert legacy router semantic helper functions into thin wrappers over the same view so they stop speaking a different semantic dialect.
4. Add/update tests for the canonical query substrate and the compatibility boundary.
5. Run required local checks.

## DoD
- deterministic booking-owner compatibility helpers query one canonical semantic view instead of a router-local semantic dialect
- `booking_prompt_owner` passes canonical semantic contract through memory profile when available
- legacy router helper behavior, where still retained, is backed by the same canonical query substrate
- tests prove the canonical semantic contract reaches this boundary and shadow semantic drift is reduced

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/owner_resolver.py truffles-api/app/core/booking_prompt_owner.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_owner_resolver.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_owner_resolver.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- targeted test output for owner resolver + reasoning-core compatibility boundary
- required local suite outputs

## Rollback
- `git revert <commit>` for the bounded migration commit
- if compatibility tests show adjacent semantic regression, stop and reopen RCA rather than reintroducing router-local semantic heuristics

## No-go
- no new semantic regex branching
- no new shadow semantic owner
- no runtime semantic repair layer
- no booking-only schema fork
- no keeping router-local semantic helpers as authoritative after the canonical query substrate exists

## Risks/Blockers
- legacy tests may be coupled to split semantic helper signatures rather than the canonical contract
- booking prompt owner compatibility path may surface stale assumptions about pending-resume context shapes
- router helper wrappers may still leave some dead code behind if not pruned carefully

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: the legacy expected-reply pipeline in `app/routers/webhook/decision.py` still speaks a separate semantic dialect (`expected_reply_type`/`expected_reply_reason` fast-path state) instead of directly querying `semantic_contract`.
- `Why not in this block`: this block only centralizes the bounded booking-owner semantic query family and propagates canonical runtime memory into that compatibility boundary; deleting or migrating the full expected-reply pipeline is a larger active-runtime slice.
- `Risk if deferred`: the same semantic meaning can still drift between canonical runtime state and legacy expected-reply compatibility branches, which can re-open follow-up/interrupt failures outside this bounded owner family.
- `Linked follow-up Task Package(s)`: next block should align or delete the legacy expected-reply compatibility pipeline so active router question-contract logic reads the canonical semantic substrate instead of a second dialect.
- `Expiry/trigger to stop deferral`: before claiming full consultant-core semantic substrate closure.

## Next-block contract (mandatory)
- `Next block objective`: align the active expected-reply/question-contract pipeline in `app/routers/webhook/decision.py` with `semantic_contract` and remove the separate legacy semantic dialect if it is no longer required.
- `First deterministic check command`: `rg -n "_apply_expected_reply_contract|_should_use_expected_reply_collect_fast_path|EXPECTED_REPLY_(SERVICE|TIME|NAME)" truffles-api/app/routers/webhook/decision.py`
- `Blocked-by conditions`: failing required local suites or evidence that an active runtime branch still requires the legacy expected-reply dialect without a canonical semantic bridge.
- `Owner role for closure`: Brain / Top Architect
