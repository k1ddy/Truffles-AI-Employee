Title/Goal
- Close the single truthful-runtime blocker family surfaced by `a922-l2-proof-seed7-20260325`: early booking/info entry turns degrade into `planner_degrade -> HANDOFF/pending` because the policy-core structured-output contract still carries a bloated legacy execution dialect that the validator then rejects or times out on.

Canon refs
- `STATE.md` — current NOW/GAP after `c42fd020`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-behavioral-proof-lock-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/intent.py`

Root cause (mandatory)
- Symptom
  - Truthful worktree runtime on `127.0.0.1:18190` degrades early booking/info turns into `planner_degrade -> HANDOFF/pending`.
- Minimal reproduction
  - Behavioral proof artifact: `/tmp/booking_quality/a922-l2-proof-seed7-20260325/summary.json`
  - Fresh direct policy-core probes from this worktree:
    - `Я хочу записаться на маникюр.` -> `route_llm_policy_core(...)` returned `invalid_json` with truncated universal `tool_args` payload.
    - `Как долго длится маникюр?` -> `route_llm_policy_core(...)` returned `timeout`.
    - `Какой адрес вашего салона?` with active booking question context -> `route_llm_policy_core(...)` returned `invalid_schema`; raw payload included `tool_action=catalog.location` and universal legacy `tool_args.service_query`, and validator returned `tool_args_unknown_field:service_query`.
- Evidence
  - `/tmp/booking_quality/a922-l2-proof-seed7-20260325/brief.md`
  - `/tmp/booking_quality/a922-l2-proof-seed7-20260325/failure_families.json`
  - `/tmp/booking_quality/a922-l2-proof-seed7-20260325/responses.jsonl`
  - Direct validation probe on `2026-03-26T07:15:54+05:00` showed:
    - raw payload for `catalog.location` still contains the legacy full `tool_args` object.
    - `validate_llm_policy_core_output(...)` returns `llm_policy_core_error:Value error, tool_args_unknown_field:service_query`.
- Five Whys
  1. Why does runtime hand off? `TurnPlanner.plan()` receives no valid policy payload and emits `planner_degrade`.
  2. Why is there no valid policy payload? `route_llm_policy_core()` returns `invalid_json`, `timeout`, or `invalid_schema` on truthful LLM calls.
  3. Why does policy-core emit invalid/truncated payloads? The prompt and structured-output schema still force a universal legacy execution carrier (`tool_args` with many irrelevant fields, dense `slots`, dense `referents`) even when the chosen action/tool only needs none or one field.
  4. Why does that break specifically on info/booking entry? Those turns should be semantically simple, but the forced legacy carrier inflates completion size and also conflicts with action-scoped validator rules (`catalog.location` does not allow `service_query`).
  5. Why does this family persist after earlier semantic work? The active runtime path was canonicalized downstream, but the model-facing structured-output seam still kept the old tool-dialect as part of required output shape.
- Root cause statement
  - The blocker family started at the policy-core structured-output boundary: the prompt and `response_format` still required a legacy universal `tool_args`/dense payload dialect that the canonical validator rejected for some tool actions and that bloated generation enough to cause truncation/timeouts on truthful runtime. Once that seam was reduced, the same family exposed two adjacent deterministic carryover seams on the active path: tool projection against the pre-resolved tool action, and stale pending-question carryover on handoff.
- Fix mechanism
  - Tighten the model-facing contract itself, not runtime fallback:
    - make policy-core structured output sparse and action-scoped;
    - remove the requirement to emit irrelevant legacy `tool_args` fields;
    - allow sparse canonical `slots`/`referents` in strict structured output;
    - keep deterministic validator as the same canonical owner boundary.
  - Then close the two adjacent deterministic seams in the same bounded family:
    - build execution projection against the final resolved tool action and sanitize against that action's validator contract;
    - clear stale `pending_question_contract` / `expected_reply_*` carryover when the runtime outcome is `HANDOFF`.

One web search (mandatory before implementation)
- Query
  - `OpenAI structured outputs JSON schema official docs`
- Date/time
  - `2026-03-26T07:15:54+05:00`
- Opened sources
  - OpenAI official docs: `https://developers.openai.com/api/docs/guides/structured-outputs`
- Source quality
  - Primary vendor documentation.
- What was found
  - Structured Outputs requires `additionalProperties: false` on objects.
  - All fields must be `required`.
  - `anyOf` is supported.
  - `if/then/else` is not supported.
- Reuse / integrate / build decision
  - `integrate`
- Reason
  - We need strict structured output to remain the model boundary owner, but we must encode sparse/action-scoped payloads without unsupported conditional schema logic. The supported path is nested `anyOf` variants, not runtime post-hoc repair.
- Rejected options
  - `if/then` action-conditioned JSON Schema: unsupported.
  - Switching this block to loose JSON mode: rejected because it weakens the existing strict model boundary instead of fixing it.

Invariant
- `policy-core` remains the only semantic owner.
- No new regex/phrase hardcode in runtime core.
- No new runtime semantic repair layer.
- No weakening of validator semantics to accept semantically conflicting tool carriers.

Scope
- Fix only the policy-core structured-output blocker family on the truthful runtime path.
- The slice must cover prompt + structured schema + validator + targeted tests + truthful seed replay.

Out of scope
- Pack/runtime cleanup outside this blocker family.
- Acceptance lock/full chain before the same truthful seed 7 is green.
- Transport/meta cosmetic cleanup.

Touch-list
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py` if a runtime contract assertion needs extension
- `STATE.md` if the block lands
- this TP

Plan
1. Replace the policy-core prompt examples/rules so `tool_args` is action-scoped and sparse instead of universal.
2. Replace the strict `response_format` tool-arg shape with supported nested `anyOf` variants, and shrink other dense carriers where feasible without changing downstream canonical payloads.
3. Keep `validate_llm_policy_core_output()` as canonical validation; only normalize sparse/canonical forms, not conflicting semantics.
4. Add targeted tests for:
   - sparse `tool_args` acceptance for `catalog.location` and booking collect;
   - strict response-format shape using supported `anyOf` strategy;
   - no validator dependency on universal legacy `tool_args` carrier.
5. Run deterministic suites, then rerun truthful seed 7 first. Only if seed 7 is green, proceed to the next proof block.

Implementation status (2026-03-26)
- Fix 1 landed: sparse/action-scoped policy-core structured output.
  - `prompts/llm_policy_core.md` now instructs sparse `tool_args`, sparse `slots`, and sparse `referents`, and it explicitly keeps initial booking prompts on canonical `ask_about_requested_slot(time)` semantics plus reschedule-without-reference escalation semantics.
  - `truffles-api/app/services/intent_service.py` now encodes the strict response format with supported nested `anyOf` sparse tool-arg variants instead of the universal dense carrier.
  - Direct truthful probes after this fix stopped reproducing the original `invalid_json` / `invalid_schema` failures for the surfaced turns.
- Fix 2 landed: tool execution projection now uses the final resolved tool action.
  - `truffles-api/app/core/turn_executor.py` now resolves the fact tool action first, then projects and sanitizes args against that final action.
  - This removed the next surfaced seam from partial truthful replay `/tmp/booking_quality/a922-l2-proof-seed7-devfix8-20260326`, where `catalog.location` still inherited invalid projected `service_query`.
- Fix 3 landed: handoff now clears stale active-question projections.
  - `truffles-api/app/core/dialog_state_service.py` now clears `expected_reply_type`, `expected_reply_reason`, `current_goal`, and the runtime `pending_question_contract` carryover when the outcome is `HANDOFF`.
  - This closed the next surfaced seam from partial truthful replay `/tmp/booking_quality/a922-l2-proof-seed7-devfix9-20260326`, where turn `Я хочу изменить время записи.` already resolved to `handoff` but still leaked `expected_reply_type='time'`.
- Current proof status
  - Deterministic suites for this family are green.
  - The freshest truthful rerun `/tmp/booking_quality/a922-l2-proof-seed7-devfix10-20260326` is not closure evidence because it was interrupted (`stop_reason=signal_2`) and therefore fails run integrity with `run_completion_gap`.
  - The next admissible proof step is a fresh truthful seed-7 replay on a fingerprintable committed HEAD.

DoD
- Direct truthful `route_llm_policy_core(...)` probes for the surfaced family stop returning `invalid_schema` from universal legacy `tool_args` payload shape.
- The same truthful seed `a922-l2-proof-seed7-20260325` replay turns green enough to remove this blocker family from the first gate, on a committed/fingerprintable runtime.
- No new semantic owner or runtime repair path is introduced.

Work mode (mandatory)
- implementation

Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_llm_policy_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_response_format or structured_output or sparse"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- Truthful direct probe from current worktree runtime for the reproduced turns.
- Truthful seed replay first: `a922-l2-proof-seed7-20260325` equivalent rerun on `127.0.0.1:18190`.

Evidence
- Updated TP with RCA and search.
- Deterministic test outputs.
- Truthful direct probe outputs.
- New seed-7 proof artifact directory under `/tmp/booking_quality/`.
- `STATE.md` update before merge with bounded facts about:
  - the first surfaced family,
  - the two adjacent deterministic seams uncovered after the first fix,
  - whether the fresh committed truthful replay is green or still blocked.

Rollback
- Revert the policy-core prompt/structured-schema/validator slice in one commit.

No-go
- No runtime fallback that silently rewrites invalid policy-core payloads into valid ones.
- No acceptance-chain reruns before seed 7 is green.
- No “just raise timeout” only fix.

Risks/blockers
- Strict structured-output subset limits conditional schemas, so sparse/action-scoped encoding must stay within supported `anyOf` patterns.
- If `gpt-4o-mini` still truncates after this payload reduction, the same family may require one more bounded contraction of model output size, not a generic timeout bump.
- Any truthful replay artifact produced from a dirty worktree remains weak proof because `/admin/version.git_commit` only fingerprints committed `HEAD`.

Residual architecture debt (mandatory)
- Current residuals accepted in this block
  - Legacy projection fields still exist on compatibility surfaces outside this family.
- Why not in this block
  - This block is only for the surfaced truthful policy-core runtime blocker.
- Risk if deferred
  - Low for this blocker once the structured-output seam is fixed; separate debt remains for transport cleanup.
- Linked follow-up Task Package(s)
  - `TP-2026-03-25-consultant-core-behavioral-proof-lock-a922.md`
- Expiry/trigger to stop deferral
  - If the next truthful seed still fails due compatibility readers rather than structured-output failure, open a new bounded family block instead of expanding this one.

Next-block contract (mandatory)
- Next block objective
  - Commit this bounded implementation family, restart the truthful runtime from that committed `HEAD`, rerun truthful seed 7, and only then decide whether the family is closed.
- First deterministic check command
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_llm_policy_core.py`
- Blocked-by conditions
  - Any remaining direct probe showing `invalid_schema` from universal legacy `tool_args` or partial/truncated policy-core JSON on the reproduced turns.
  - Any truthful rerun stopped before completion or lacking manual audit.
- Owner role for closure
  - Brain / Top Architect after truthful seed 7 evidence is green.
