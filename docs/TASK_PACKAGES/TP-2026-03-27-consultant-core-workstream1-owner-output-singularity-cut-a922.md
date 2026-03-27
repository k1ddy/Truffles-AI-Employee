# TP-2026-03-27-consultant-core-workstream1-owner-output-singularity-cut-a922

Название/цель:
- Завершить следующий крупный cut внутри Workstream 1: убрать mixed owner output на hot path и заставить hot-path consumers принимать только `SemanticDecisionV1`, чтобы `route_llm_policy_core(...)` больше не был источником параллельного `semantic_frame`-смысла.
- Одним блоком закрыть producer + consumer сторону owner-adjacent legacy path: producer перестаёт отдавать legacy semantic carrier, planner принимает только canonical owner artifact, legacy reactivation reader переходит на canonical owner parsing.

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
- `STATE.md` NOW: `workstream1_owner_adjacent_shadow_cut`

Invariant:
- Canaried hot path must keep exactly one semantic owner per turn.
- `SemanticDecisionV1` remains the only meaning artifact on the hot path.
- Binding stays separate from meaning.
- Explicit degrade/preflight paths remain allowed and typed.

Scope:
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- related deterministic tests in `truffles-api/tests/test_intent.py`, `truffles-api/tests/test_consultant_core_runtime_contracts.py`, `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_turn_planner_expected_reply_validation.py`

Out of scope:
- TurnJournal / ConversationProjection implementation
- BindingPlanV1 extraction
- planner/runtime state canonicalization beyond owner-output consumer cut
- legacy webhook mesh broad rewrite outside direct owner-output consumption

Touch-list:
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `STATE.md`
- `STRUCTURE.md`

Work mode:
- implementation

One web search (mandatory before implementation):
- Query: `JSON Schema if then else official reference`
- Date/time: `2026-03-27 Asia/Almaty`
- Opened sources:
  - `https://json-schema.org/understanding-json-schema/reference/conditionals`
- Source quality:
  - high-signal primary documentation from `json-schema.org`
- Found reusable solution:
  - JSON Schema `if` / `then` can apply a subschema only when a property is present; this fits a contract rule like “if `semantic_decision` is present, shadow carriers must satisfy a stricter shadow-only schema”.
- Decision:
  - `reuse/integrate`
  - Add a conditional contract rule in `policy_decision.v1.jsonschema` instead of inventing ad-hoc validation-only logic.
- Rejected options:
  - custom Python-only schema guard without contract change — rejected because it would leave the runtime contract undocumented and unenforced at schema boundary.

Root cause (mandatory):
- Symptom:
  - Workstream 1 is still not closed because hot-path owner output is not singular: `route_llm_policy_core(...)` still returns a parallel `semantic_frame` carrier and planner/booking-reactivation consumers still accept legacy policy-shape payloads instead of requiring canonical `SemanticDecisionV1`.
- Minimal reproduction:
  - `route_llm_policy_core(...)` success returns `payload` plus `semantic_frame`.
  - `TurnPlanner._build_policy_core_decision(...)` still coerces non-`semantic_decision.v1` payloads through `SemanticDecisionV1.from_policy_core_payload(...)`.
  - `booking_prompt_owner.py` still reads raw `action/tool_action/slots/next_question/open_questions` directly from `policy_result["payload"]`.
- Evidence:
  - `truffles-api/app/services/intent_service.py:3118-3147`
  - `truffles-api/app/core/turn_planner.py:733-764`
  - `truffles-api/app/core/booking_prompt_owner.py:324-386`
  - repo search: `rg -n 'policy_result\.get\("payload"\)|from_policy_core_payload|result\["semantic_frame"\]' truffles-api/app truffles-api/tests`
- Five Whys:
  1. Why is owner output still split? Because the policy-core route still materializes and returns `semantic_frame` alongside canonical owner payload.
  2. Why does that matter if planner mostly reads `payload`? Because it keeps a second semantic carrier live at the producer boundary and invites legacy consumers to keep reading policy-shape fields.
  3. Why do legacy consumers keep doing that? Because planner still supports fallback coercion from policy-shape payloads and booking reactivation logic still parses raw policy fields from the payload.
  4. Why is that dangerous? Because it preserves owner-adjacent semantic compatibility paths instead of forcing one canonical owner contract.
  5. Why does that block Workstream 1? Because completion criteria require exactly one `SemanticDecisionV1` per canaried turn and legacy owner-adjacent paths to be shadow-only or deleted.
- Root cause statement:
  - Producer and consumer boundaries still accept policy-shape semantic payloads, so `SemanticDecisionV1` is canonical in practice but not yet exclusive in contract.
- Fix mechanism:
  - Remove success-path `semantic_frame` from `route_llm_policy_core(...)`, require `semantic_decision.v1` payloads in planner hot-path intake, switch booking reactivation to canonical owner parsing, and add schema-level conditional guard that owner-backed `PolicyDecision` instances keep shadow carriers shadow-only.

Plan:
1. Remove success-path `semantic_frame` from `route_llm_policy_core(...)` while preserving canonical `payload`, `binding`, and trace fields.
2. Tighten planner hot-path intake so `_build_policy_core_decision(...)` accepts only `SemanticDecisionV1` or payloads already shaped as `semantic_decision.v1`; reject legacy policy-shape payloads.
3. Move booking reactivation owner parsing onto `SemanticDecisionV1` instead of raw policy payload fields.
4. Add conditional schema guard to `policy_decision.v1.jsonschema` for owner-backed shadow carriers.
5. Update deterministic regressions and owner-contract tests.
6. Update `STATE.md` and `STRUCTURE.md` truthfully with removed authority and residual debt.

DoD:
- `route_llm_policy_core(...)` success payload contains canonical `semantic_decision.v1` only; no parallel success-path `semantic_frame` carrier.
- Planner hot-path consumer rejects legacy policy-shape payloads instead of translating them back into owner meaning.
- Booking reactivation owner consumer reads canonical `SemanticDecisionV1` rather than raw policy fields.
- PolicyDecision contract captures the shadow-only rule when `semantic_decision` is present.
- Deterministic checks pass.

Checks:
- `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py truffles-api/app/core/booking_prompt_owner.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "route_llm_policy_core or semantic_decision"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or policy_core_decision or schema"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reactivation"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `git diff --check`

Evidence:
- changed authority map in code
- deterministic test output from the commands above
- updated `STATE.md`
- updated `STRUCTURE.md`

Rollback:
- Revert touched files from this TP only.
- Restore previous route result / planner intake behavior if deterministic checks reveal hidden legacy dependency that cannot be removed inside this block.

No-go:
- no new semantic hardcode in core
- no new compatibility wrapper that keeps policy-shape payload as peer meaning
- no weakening of mutation guard
- no broad legacy mesh rewrite outside direct owner-output consumers

Risks/blockers:
- Some deterministic tests currently mock legacy policy-shape payloads and will need contract-aligned updates.
- Legacy metadata readers may still inspect stored `llm_policy_core.payload`; those reads are out of scope unless this block directly breaks them.

Residual architecture debt (mandatory):
- Current residuals accepted in this block:
  - runtime/state legacy projections still exist as canonical-state migration surfaces
  - pre-owner memory profile still includes projected semantic state from runtime storage
  - legacy webhook mesh still contains semantic compatibility logic
- Why not in this block:
  - this family is bounded to owner-output producer/consumer singularity, not canonical-state unification or legacy mesh strangler.
- Risk if deferred:
  - stale runtime/state projections can still influence online semantics until later Workstream 1 / Workstream 3 cuts complete.
- Linked follow-up Task Package(s):
  - `TP-2026-03-27-consultant-core-workstream1-owner-adjacent-shadow-cut-a922.md`
  - next TP TBD for runtime owner-precedence closeout
- Expiry/trigger to stop deferral:
  - if a canaried owner-backed turn still reads stale runtime state or execution semantic meta as primary meaning after this block, deferral expires immediately.

Next-block contract (mandatory):
- Next block objective:
  - remove remaining runtime/state-first owner-adjacent merge precedence so owner semantics outrank stale runtime state on all canaried reads.
- First deterministic check command:
  - `rg -n "_project_runtime_semantic_contract|_project_runtime_pending_question_contract|project_runtime_semantic_contract|project_runtime_pending_question_contract" truffles-api/app/core/consultant_runtime.py truffles-api/app/core/dialog_state_service.py`
- Blocked-by conditions:
  - owner-output singularity not yet established
  - consumer updates still depend on raw policy-shape payloads
- Owner role for closure:
  - Brain / Top Architect
