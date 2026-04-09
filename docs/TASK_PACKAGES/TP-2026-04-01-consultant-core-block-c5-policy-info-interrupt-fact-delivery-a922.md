# TP-2026-04-01-consultant-core-block-c5-policy-info-interrupt-fact-delivery-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> implementation -> closure`
- Block ID: `block-c5-policy-info-interrupt-fact-delivery`

## Название/цель
Закрыть только `Block C.5 — Policy-Info Interrupt Fact Delivery` в active worktree `a922`: canonical policy-owned info interrupts under active booking continuity must deliver the allowed fact reply and preserve the pending booking question, instead of falling through to `info_ref_unresolved` / `Я уточню это для вас.`.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c-continuity-carrier-collapse-a922.md`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/summary.json`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/responses.jsonl`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/family_registry.json`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/manual_audit.md`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/manual_audit.json`

## Invariant
- Do not reopen `Block C`: canonical `pending_question_contract` must remain the sole mutable continuity writer on the touched follow-up/resume path.
- Do not treat this as a promotions-only scenario patch; the mechanism is canonical policy-info interrupt delivery on the `catalog.service_query` fact path.
- Do not widen into `Block D` boundary meaning minting, `Block E` pack/runtime separation, or `Block F` legacy mesh drain.
- Do not add raw-text routing branches in core as business control logic.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries/reports until code + focused tests + one minimal replay proof exist for this block.

## Scope
- Canonical policy-info interrupt delivery on the touched `catalog.service_query` fact path.
- Execution/fallback law inside `TurnExecutor` when the owner already supplied policy info refs and continuity is preserved.
- Tool-registry execution only as needed to accept canonical allowed info sections instead of dropping to unresolved.
- Focused deterministic tests plus exactly one minimal replay on this interruption family.

## Out of scope
- semantic-owner arbitration already closed in `Block A`
- exact location/hours/parking scope already closed in `Block B`
- continuity-carrier authority already closed in `Block C`
- boundary purification outside this specific fact-delivery mechanism
- broad pack/runtime or legacy cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c5-policy-info-interrupt-fact-delivery-a922.md`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## One web search (mandatory before implementation)
- Query: `W3C SCXML history state preserve interrupted child state`
- Date/time: `2026-04-01 09:59:00 +05 (Asia/Almaty)`
- Sources opened:
  - `https://www.w3.org/TR/scxml/`
- Source quality:
  - W3C primary specification
- Found ready-made solutions:
  - no Truffles-specific implementation; the reusable rule is that an interrupt may temporarily leave the active state, but resume must target the previously stored state configuration rather than re-authoring a new one.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing canonical pending-question contract from `Block C`;
  - integrate canonical policy info refs into the existing executor/tool-registry delivery path;
  - build only the missing delivery/fallback law so a temporary info interrupt can answer and then resume, instead of dropping into unresolved.
- Rejected options:
  - more web searches
  - adding a second continuity writer
  - hardcoding promotions/pricing keyword branches in core runtime
  - widening the block into general boundary purification or pack/runtime redesign

## Input baseline (FACT)
1. Fresh replay evidence on the surfaced first-fail family:
- source: `/tmp/booking_quality/a922-block-c-replay-20260401ac/summary.json`
- result:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `manual_audit_status=done`
  - `human_semantic_valid=false`
  - first remaining failure summary: promotions interrupt during active booking falls through to `info_ref_unresolved` instead of delivering promo facts while preserving the pending time question.
2. Fresh replay turn evidence on the same family:
- `message_id`: `LLM-QUAL-a922-block-c-replay-20260401ac-001-02-62a155`
- user: `Какие у вас акции на маникюр?`
- result:
  - owner stayed canonical: `intent="pricing"`, `action="fact"`, `pack_refs=["promotions"]`, `capability="promotions"`, `active_question_relation="generic_info_interrupt"`, `expected_reply_type="time"`
  - fact contract allowed the reply: `fact_requested_refs=["pricing","promotions"]`, `fact_allowed_refs=["pricing","promotions"]`, `fact_allowed_sets=[["pricing","promotions"]]`
  - final runtime fell through to `tool_action="catalog.service_query"`, `tool_decision="info_ref_unresolved"`, `fact_fallback_reason="policy_info_unresolved"`
3. Local exact reproduction proved the sharper mechanism before code:
- canonical owner-backed reproduction on the active worktree still built `requested_fact_refs=["pricing","promotions"]` and `allowed_emitted_sets=[["pricing","promotions"]]`
- direct truth fallback already resolved `promotions`, but the exact `promotions` reply was discarded downstream as out-of-scope
- therefore the real shared mechanism was mixed coarse+exact fact planning, not missing promo truth and not a tool incapability

## Exact Path Map (mandatory)
1. Input
- Active booking continuity exists after turn 1: pending booking datetime collect.
- Turn 2 asks a factual promo question during that continuity: `Какие у вас акции на маникюр?`
2. Owner output
- Replay evidence in `/tmp/booking_quality/a922-block-c-replay-20260401ac/responses.jsonl` shows canonical owner output:
  - `intent="pricing"`
  - `action="fact"`
  - `pack_refs=["promotions"]`
  - `capability="promotions"`
  - `reason="user_asked_promotions_during_booking_continuity"`
  - `active_question_relation="generic_info_interrupt"`
  - `expected_reply_type="time"`
- This means the owner already asked for grounded fact delivery while preserving booking continuity.
3. Validator / binding / continuity preservation
- before the fix, `truffles-api/app/core/fact_plane.py:348-520` built a fact request/plan with `requested_fact_refs=["pricing","promotions"]` and `allowed_emitted_sets=[["pricing","promotions"]]`.
- after the fix, the same owner shape now collapses to `requested_fact_refs=["promotions"]` and `allowed_emitted_sets=[["promotions"]]` through the manifest-driven service-query exact-section companion group.
- Replay trace confirms continuity is preserved: `pending_question_contract.expected_reply_type="time"` and the next turn returns to booking.
4. Fallback / degrade path
- `truffles-api/app/core/turn_executor.py:580-581` merges policy info refs with the fact request.
- `truffles-api/app/core/turn_executor.py:624-669` executes `catalog.service_query` if the tool is executable.
- the downstream scope validator accepts the exact emitted `promotions` reply once the fact plan no longer forces the mixed `["pricing","promotions"]` set.
5. Final response
- the proving replay now returns the grounded promotions reply on the interrupt turn and still resumes booking continuity on the next user answer.
6. Trace/meta evidence
- replay turn: `/tmp/booking_quality/a922-block-c-replay-20260401ac/responses.jsonl`
- replay trace: `/tmp/booking_quality/a922-block-c-replay-20260401ac/trace_bundle.jsonl`
- proving replay: `/tmp/booking_quality/a922-block-c5-replay-20260401b/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,family_registry.json}`
- fact-plane exactness code: `truffles-api/app/core/fact_plane.py:165-280`, `truffles-api/app/core/fact_plane.py:348-420`
- focused deterministic proof: `truffles-api/tests/test_consultant_core_runtime_contracts.py`
7. Layer classification
- Primary: `fact_composition_error`
- Secondary: `boundary_fallback_error` only as a downstream consequence of the mixed fact plan
- Not this block: `owner_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- A canonical promo/info interrupt under active booking continuity preserves the pending booking question but fails to deliver the requested fact and falls through to `info_ref_unresolved`.

### Minimal reproduction
1. Start from active booking continuity with `expected_reply_type=time` and a carried service referent.
2. Feed a canonical owner fact decision shaped like the replay turn:
   - `intent=pricing`
   - `pack_refs=["promotions"]`
   - `capability="promotions"`
   - `active_question_relation="generic_info_interrupt"`
   - `tool_action="catalog.service_query"`
3. Let `fact_plane` build the allowed fact contract.
4. Observe that `TurnExecutor` can still emit `policy_info_unresolved` / `info_ref_unresolved` instead of a promo fact reply, even though continuity remained canonical and the allowed fact scope includes `promotions`.

### Evidence
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/summary.json`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/responses.jsonl`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-c-replay-20260401ac/manual_audit.md`
- `truffles-api/app/core/turn_executor.py:580-797`
- `truffles-api/app/core/turn_executor.py:1361-1487`
- `truffles-api/app/services/tool_registry_service.py:2296-2475`
- `truffles-api/app/core/fact_plane.py:348-520`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py:3748-3794`
- local canonical reproductions recorded in the session log before implementation showed:
  - `FactRequest/FactPlan -> requested_fact_refs=["pricing","promotions"]`
  - direct truth fallback resolved `("promotions", "<valid promo reply>")`
  - final runtime still fell to `info_ref_unresolved`

### Five Whys
1. Why does the user get `Я уточню это для вас.` instead of promotions info? Because runtime falls into `policy_info_unresolved` / `info_ref_unresolved` after the canonical fact path fails to deliver a response.
2. Why can that unresolved fallback still happen when the owner already supplied `promotions` and continuity is preserved? Because fact planning co-mingles the coarse `pricing` alias with the exact `promotions` owner ref and forces `allowed_emitted_sets=[["pricing","promotions"]]`.
3. Why does that matter when direct truth fallback already has a valid `promotions` reply? Because a response that emits only `["promotions"]` is then treated as out-of-scope and discarded downstream.
4. Why does that become a shared mechanism instead of one promo scenario? Because any canonical policy-info interrupt on the `catalog.service_query` fact path can mix coarse and exact refs and therefore reject an exact in-scope reply the owner actually asked for.
5. Why is this the right block boundary? Because continuity ownership was already correct after `Block C`; the remaining defect lived in exact fact planning and in-scope reply acceptance on the touched interruption path.

### Broken invariant
- When owner output already supplies exact fact refs through `pack_refs/fact_refs/tool_args`, the fact plane must not widen the requested/emitted contract with coarse sibling aliases that make the exact in-scope reply look out-of-scope.

### Shared mechanism
- Fact planning still mixed coarse service-query aliases (`intent` / `capability`) with exact owner refs (`pack_refs` / `fact_refs` / `tool_args`) on the canonical policy-info interrupt path, which forced combined allowed sets like `["pricing","promotions"]`.

### Why the surfaced family belongs to that mechanism
- Replay evidence, local reproduction, and direct-truth instrumentation all showed the same shape: continuity stayed canonical, the exact promo reply existed, but the mixed allowed set rejected it downstream. That is shared mechanism evidence, not a one-off scenario symptom.

### Open-world envelope expected to improve
- promotions interrupts during active booking continuity
- pricing interrupts during active booking continuity
- other canonical policy-info interrupts that resolve onto `catalog.service_query`
- any touched service-query fact path where owner exact refs and coarse aliases previously co-existed in the same request

### Root cause statement
- Canonical policy-info interrupts on the service-query fact path still co-mingled coarse aliases with exact owner refs during fact planning. That produced mixed `requested_fact_refs` / `allowed_emitted_sets`, so exact in-scope replies like `promotions` were discarded as out-of-scope even though the owner had already selected them.

### Fix mechanism
- Reuse the existing manifest/group-priority mechanism instead of adding a new executor branch:
- define one service-query exact-section companion group in `truffles-api/app/core/fact_plane.py`
- assign `pricing`, `promotions`, `duration`, `services_overview`, and `guest_policy` to that group with self-only emitted policies
- let the existing priority rule prefer explicit owner refs over lower-priority coarse siblings on the same fact path
- codify the result with focused tests and one focused replay proving exact promo delivery plus preserved booking continuity

## Plan
1. Keep this TP as the only active block after `Block C` closeout.
2. Rebuild the RCA from the live replay artifacts and local canonical reproduction before editing code.
3. Implement the bounded exact-section fix in the fact-plane manifest/group law.
4. Add focused deterministic tests for fact-plan exactness and canonical owner-backed promo interrupt delivery.
5. Run exactly one minimal replay on the same interruption family and audit it turn-by-turn.

## DoD
- The touched active-booking promo/info interrupt no longer falls to `info_ref_unresolved`.
- The response delivers an allowed fact reply (`info_sections` grounded to the requested policy-info family).
- Booking continuity remains canonical (`expected_reply_type=time` on the interrupt turn and progression back to booking afterwards).
- No new raw-text scenario branch is added in core runtime.
- Focused deterministic tests pass.
- One minimal focused replay proves the block and truthfully records the next surfaced family, if any.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_plan_prefers_owner_exact_service_query_ref_over_coarse_pricing_alias or routes_owner_backed_promotions_interrupt_through_catalog_tool_registry or accepts_owner_backed_promotions_direct_truth_fallback or projects_policy_info_refs_into_catalog_execution or uses_policy_owned_info_truth_fallback_without_echo or routes_booking_info_interrupts_through_catalog_tool_registry"`
- `git diff --check`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18189 --client-slug demo_salon --count 2 --scenarios-file /tmp/booking_quality/a922-block-c-replay-20260401ac/scenarios.json --mode llm --min-turns 10 --max-turns 15 --media-mode text --media-kind photo --scenario-coverage interrupt,handoff --batch-size 2 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-block-c5-replay-20260401b --run-id a922-block-c5-replay-20260401b --history-max 20 --max-failures 2 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate warn --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-block-c5-replay-20260401b --status done --human-semantic-valid true ...`

## Evidence
- Deterministic test output from the focused pytest selections above
- One focused replay directory under `/tmp/booking_quality/`
- Replay artifacts:
  - `summary.json`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `manual_audit.md`
  - `manual_audit.json`
  - `family_registry.json`
- Proving replay result:
  - `/tmp/booking_quality/a922-block-c5-replay-20260401b/summary.json` -> `infra_valid=true`, `semantic_valid=true`
  - `/tmp/booking_quality/a922-block-c5-replay-20260401b/manual_audit.json` -> `human_semantic.valid=true`
  - `/tmp/booking_quality/a922-block-c5-replay-20260401b/family_registry.json` -> zero product/oracle/infra families
- `STATE.md` update only after code + focused tests + replay proof

## Rollback
- Revert only the touched `Block C.5` files in the active worktree.
- If the new delivery law regresses other policy-info interrupts, revert the touched executor/tool-registry changes; do not reintroduce scenario-specific special cases.

## No-go
- No additional web search
- No docs sync before proof
- No promotions-only keyword hack in core runtime
- No widening into `Block D+`
- No broad refactor of unrelated message-endpoint logic

## Риски/блокеры
- `catalog.service_query` already contains multiple promo/price/duration subpaths; any future widening beyond exact-section prioritization would need a new RCA block.
- `Block D` still remains open, so boundary or stale compatibility meaning can still surface outside this touched fact-plane envelope.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- full boundary purification remains open
- pack/runtime separation remains partial
- legacy mesh fate remains partial
- operational dedupe remains partial

### Why not in this block
- those belong to `Block D`, `Block E`, `Block F`, and `Block G`; widening this block would break the one-hard-block rule

### Risk if deferred
- even after this fact-delivery fix, other non-canonical boundary or legacy mechanisms can still mutate meaning or execution outside the touched policy-info interrupt envelope

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-d-boundary-purification-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e-real-pack-runtime-separation-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922.md` (`planned`)

### Expiry/trigger to stop deferral
- if two iterations fail to produce new evidence or the replay shows continuity authority split again, stop and return to RCA before touching `Block D`

## Next-block contract (mandatory)
### Next block objective
- `Block D — Boundary Purification`

### First deterministic check command
- `rg -n "BoundaryOverride|boundary_override|expected_reply_type|pending_question_contract|degrade|restore" truffles-api/app/services/owner_resolver.py truffles-api/app/core/response_realizer.py truffles-api/app/services/state_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py`

### Blocked-by conditions
- exact path map + focused RCA + one focused web search must be recorded before any `Block D` code
- `Block D` must stay bounded to boundary meaning / preserve-or-degrade law; no widening into pack/runtime or legacy fate work

### Owner role for closure
- `Top Architect` or `Brain`

## Branch + Worktree path + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: active worktree `HEAD` only; `/home/zhan/truffles-main` may be used only as canon/baseline/env helper
- Merge policy: no merge/closure claim in this block without code + focused tests + minimal replay proof
- Cleanup: keep replay artifacts under `/tmp/booking_quality/`; no cleanup until proof handoff is complete
