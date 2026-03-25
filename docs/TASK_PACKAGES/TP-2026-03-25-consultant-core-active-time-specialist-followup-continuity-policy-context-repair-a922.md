# TP-2026-03-25 Consultant Core Active-Time Specialist Followup Continuity + Policy Context Repair A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-ACTIVE-TIME-SPECIALIST-FOLLOWUP-CONTINUITY-POLICY-CONTEXT-REPAIR-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `f6017fc5`, `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5`
- `UNLOCKS`: fresh guarded acceptance `lock` only after the surfaced family is closed on current runtime

## Название/цель
Закрыть surfaced runtime family без нового semantic owner и без phrase/regex костылей: active booking `time` collect теряет named specialist follow-up semantics, потому что единственный continuity writer и policy-core input contract сжимают состояние до `expected_reply_type/name` и не передают policy-core typed referents/interaction state.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5/summary.json`
- `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5/responses.jsonl`
- `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5/trace_bundle.jsonl`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `prompts/llm_policy_core.md`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/services/intent_service.py`
  - targeted tests under `truffles-api/tests/`
- `Baseline commands`:
  - `git status --short --branch`
  - `git log --oneline -3`
  - `python3 - <<'PY' ... responses.jsonl inspection ... PY`
- `FACT findings`:
  - surfaced run `a922-l2-dev-seed7-20260325-r5` is on the current runtime fingerprint, not stale containers
  - `dialog_index=1`, `turn_index=4`, user specialist preference under active booking collect returned `tool_decision=name` / `expected_reply_type=name`
  - current runtime trace before that turn had only generic `expected_reply_type=time`; specialist referent / target / relation were not preserved into policy-core input
- `Detected drift (docs vs code)`:
  - `prompts/llm_policy_core.md` instructs policy-core to use `memory.profile.current_referents` and `memory.profile.pending_question_contract`, but `ConsultantRuntime._plan_turn()` does not serialize the active `DialogState` into that input
  - `DialogStateService.write_runtime_payload()` rebuilds runtime dialog state from scratch and drops active `pending_question_target`, `active_question_relation`, and grounded referents during booking FACT interrupts

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI structured outputs JSON schema official docs`
- **Date/time (local):** 2026-03-25 17:07, Asia/Almaty
- **Sources opened (from this query):**
  - OpenAI, `Introducing Structured Outputs in the API` — https://openai.com/index/introducing-structured-outputs-in-the-api/
- **Existing solutions found:** strict structured outputs are reliable for enforcing richer JSON contracts, but they do not prevent semantic value mistakes inside the schema.
- **Decision:** reuse the existing structured-output path and strengthen the semantic contract/context we pass to policy-core; do not add another deterministic semantic layer.
- **Rejected options:**
  - runtime semantic gate that reclassifies specialist vs customer outside policy-core
  - scenario-specific phrase handling for specialist names
- **Source quality:** official OpenAI primary source

## Root cause (mandatory)
- **Symptom:** active booking `time` collect loses named specialist follow-up semantics; policy-core asks for customer name instead of preserving `pending_question_target=specialist` / `active_question_relation=referent_followup` under the active `time` collect.
- **Minimal reproduction:** run the seeded dev artifact `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5` and inspect `dialog_index=1`, `turn_index=4`.
- **Evidence:**
  - `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r5/responses.jsonl`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/intent_service.py`
- **Five Whys (or equivalent):**
  1. Why did policy-core choose `name`? Because on that turn it did not receive the typed active interaction contract it needs to disambiguate specialist preference vs customer name.
  2. Why did it not receive that contract? Because `_plan_turn()` only forwarded a minimal memory profile, and most of it was stripped again by `_normalize_policy_core_memory_profile()`.
  3. Why was the richer contract unavailable in runtime state? Because `write_runtime_payload()` rebuilt `DialogState` from generic booking slots and expected reply type, dropping `pending_question_target`, `active_question_relation`, and grounded referents across interrupts.
  4. Why did this survive earlier architecture cleanup? Because cleanup removed multi-owner semantic rewrite, but continuity/state compression remained lossy.
  5. Why does this create open-world fragility? Because the system compresses business roles into generic slot progression instead of preserving typed referents and active interaction state for the single semantic owner.
- **Root cause statement:** the surfaced family is caused by lossy continuity persistence and lossy policy-core input shaping: the runtime keeps only generic slot progress while dropping typed referents and active interaction state, so the single semantic owner is forced to infer specialist-vs-customer from incomplete context.
- **Fix mechanism:** preserve typed `DialogState` continuity across turns, pass that continuity into policy-core input, and tighten the policy-core prompt contract so `slots.name` is customer-only while specialist preference travels via referents / interaction state.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.build_collect_owner_state()`
  - existing `DialogState` / `InteractionState` / `CurrentReferents` contract
  - existing policy-core structured output path in `intent_service.route_llm_policy_core()`
- **External reuse:** none beyond the single structured-output reference above.
- **Why not reinvent the wheel:** the system already has typed continuity objects; the bug is that the active runtime path compresses and drops them.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded core-behavior fix in the single active runtime path.

## Invariant
- Keep one semantic owner: no new semantic hardcode/regex/phrase branching in core.
- Do not add runtime semantic compensation outside policy-core.
- Do not resume guarded acceptance until this family is green on local realism and targeted replay evidence.

## Scope
- preserve richer booking continuity in the single continuity writer
- expose active interaction state/current referents to policy-core input
- tighten policy-core prompt contract around customer name vs specialist preference
- add targeted tests for this family
- rerun local realism checks plus one bounded dev replay for the surfaced family

## Out of scope
- acceptance `lock/replay/full`
- specialist booking execution / calendar specialist assignment
- multi-pack or multilingual proof beyond the surfaced family
- legacy substrate resurrection

## Touch-list
- `prompts/llm_policy_core.md`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_intent.py`

## Plan (1..N)
1. Capture the real continuity loss points in the active runtime path and implement preservation of typed referents/interaction state in `write_runtime_payload()`.
2. Pass the preserved continuity into policy-core input from `consultant_runtime._plan_turn()` and normalize it in `intent_service`.
3. Tighten the prompt contract so `slots.name` means customer name only and specialist preference must stay in referents/tool args/interaction state.
4. Add targeted tests for persistence + policy input shaping.
5. Run local deterministic checks and one bounded dev replay on the surfaced scenario family.

## DoD
- runtime state after booking collect and booking FACT interrupts preserves `pending_question_target`, `active_question_relation`, and grounded referents
- policy-core input receives the active continuity contract on subsequent turns
- prompt contract explicitly forbids collapsing specialist preference into `slots.name`
- targeted tests are green
- the surfaced family no longer fails on the bounded replay evidence

## Checks
- `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_planner.py truffles-api/app/services/intent_service.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k 'write_runtime_payload or current_referents or interaction_state'`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'question_contract_trace_entries or runtime'`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k 'policy_core'`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`
- bounded dev replay on current runtime using the surfaced scenarios file from `/tmp/booking_quality/a922-l2-dev-seed7-20260325-r4/scenarios.json`

## Evidence
- git diff / commit
- targeted test output
- required local realism suite outputs
- bounded replay artifacts under `/tmp/booking_quality/<new-run-id>`
- updated `STATE.md` entry before merge

## Token / run budget (mandatory for expensive suites)
- **Max expensive runs:** 1 bounded dev replay after deterministic checks pass
- **Fail-fast / scenario lock:** reuse the already surfaced scenarios file; stop after the first honest result
- **Stop condition:** if targeted tests fail or the replay surfaces a different first-fail family, stop and publish that evidence instead of looping
- **Escalation path:** Brain / Top Architect decide any second replay

## Release safety (mandatory for non-doc changes)
- **Strategy:** local runtime only, current worktree containers only
- **Go/no-go signals:** targeted tests green, required local realism suite green, bounded replay no longer fails on the surfaced family
- **Rollback:** revert the bounded code diff / commit if the replay regresses adjacent continuity families
- **Post-release monitoring window:** Phase E acceptance `lock` only after this block is green

## Rollback
- `git revert <commit>` for the bounded fix commit
- if bounded replay regresses adjacent continuity families, discard the runtime rebuild and return to RCA with the surfaced artifacts

## No-go
- no new phrase/regex semantic routing
- no scenario-specific runtime branching for `Айгерим` or any specific language surface
- no acceptance replay/lock/full in this block
- no weakening of oracles or trace/meta expectations

## Risks/Blockers
- existing tests may encode the old lossy runtime state shape
- preserving richer continuity can surface adjacent gaps in active-name followup or specialist-availability followup families
- bounded replay still depends on healthy local runtime + judge key

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: booking semantic model is still partially slot-centric (`service/datetime/name`) even after continuity preservation.
- `Why not in this block`: full domain-object remodeling would exceed one bounded implementation family.
- `Risk if deferred`: other business-role ambiguities can still surface even with correct continuity persistence.
- `Linked follow-up Task Package(s)`: next TP should harden booking semantic contract beyond generic slots if acceptance surfaces another role-ambiguity family.
- `Expiry/trigger to stop deferral`: before claiming open-world multilingual robustness for booking continuity.

## Next-block contract (mandatory)
- `Next block objective`: either reopen guarded acceptance `lock` from a green bounded replay or open the next bounded semantic-model TP from the next first-fail family.
- `First deterministic check command`: `python3 - <<'PY' ... inspect latest bounded replay for dialog 1 turn 4 ... PY`
- `Blocked-by conditions`: failed local realism suite, unhealthy runtime, or the surfaced family still failing on bounded replay
- `Owner role for closure`: Brain / Top Architect
