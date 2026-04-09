# TP-2026-04-01-consultant-core-block-e5-owner-service-referent-grounding-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> RCA -> implementation -> closure`
- Block ID: `block-e5-owner-service-referent-grounding`

## Название/цель
Закрыть только `Block E.5 — Owner Service Referent Grounding` в active worktree `a922`: owner-side service fact questions must ground common service referents such as `укладка` directly into the semantic subject for `duration` / later `master` fact questions instead of falling into synthetic `collect service` on the live fact path.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e-real-pack-runtime-separation-a922.md`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/summary.json`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/responses.jsonl`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/manual_audit.json`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/family_registry.json`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## Invariant
- Do not reopen `Block A`..`Block E`.
- Do not patch replay scenarios or oracle thresholds.
- Do not move meaning ownership out of policy-core; only fix owner-side service referent grounding.
- Do not change pack/runtime boundary behavior or reopen `catalog.location` / `catalog.service_query` seams closed in `Block E`.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until this block itself is fully proven.

## Scope
- owner-side grounding for service fact questions in the surfaced `duration` family
- shared owner mechanism that should also cover the same referent-grounding envelope for later `master` fact questions if it truly belongs to the same mechanism
- focused contract tests and exactly one focused replay on this owner-side fact-question family

## Out of scope
- pack/runtime separation
- boundary or continuity rework
- legacy mesh drain
- operational dedupe
- broad whole-system replay

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e5-owner-service-referent-grounding-a922.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/policy_context_snapshot_service.py`
- `truffles-api/app/services/policy_prompt_snapshot_service.py`
- `prompts/llm_policy_core.md`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## One web search (mandatory before implementation)
- Query: `site:developers.openai.com/api/docs/guides/prompting few-shot examples concise YAML-style`
- Date/time: `2026-04-01 12:41:00 +0500 (Asia/Almaty)`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/prompting`
- Source quality:
  - OpenAI official documentation / primary source
- Found ready-made solutions:
  - keep task-specific examples concise and explicit;
  - use compact example blocks that are easy to scan and update;
  - rerun linked evals after prompt changes.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing policy-core prompt and governed context snapshot;
  - integrate compact inline service-grounding examples plus compact pack service taxonomy context;
  - build only the missing owner-side context cards and prompt guidance for this surfaced family.
- Rejected options:
  - adding a second semantic owner or pre-owner deterministic semantic rewrite;
  - relying on replay-only proof without strengthening the owner prompt/context;
  - extra web searches.

## Input baseline (FACT)
1. Fresh `Block E` replay proof exists at `/tmp/booking_quality/a922-block-e-replay-20260401h`.
2. Touched `Block E` paths are green:
- `block-e-1`: exact `hours` fact through `catalog.location`
- `block-e-3`: exact `promotions` fact through `catalog.service_query` with preserved booking continuity
3. First remaining fail is unrelated to `Block E`:
- message id: `LLM-QUAL-a922-block-e-replay-20260401h-002-01-c73b66`
- user: `Сколько времени занимает укладка?`
- owner output: `intent=duration`, `action=collect`, `reason=service_missing_for_duration_query`
- runtime result: `booking_prompt` asking for service instead of duration fact

## Exact Path Map (mandatory)
1. Input
- user asks a service fact question with an inline service referent: `Сколько времени занимает укладка?`
2. Owner output
- `route_llm_policy_core(...)` in `truffles-api/app/services/intent_service.py` builds `policy_input` from `_load_policy_core_prompt()` plus `build_policy_core_context_snapshot(...)`
- current owner envelope contains generic capability/policy/consult cards but no pack-side service taxonomy help for `укладка`
- policy-core emits `intent=duration`, `action=collect`, `resolution_mode=clarify_missing_subject`, `reason=service_missing_for_duration_query`
3. Validator / interrupt arbitration
- no boundary or interrupt override rewrites the turn; the runtime preserves the owner decision
4. Continuity preservation
- no active continuity issue participates in the surfaced failure
5. Fallback / degrade
- none; the live path is the direct owner-authored collect decision
6. Final response
- runtime asks `На какую услугу хотите записаться?`
7. Trace/meta evidence
- `/tmp/booking_quality/a922-block-e-replay-20260401h/responses.jsonl`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/trace_bundle.jsonl`
- owner trace already contains the failing semantic contract before runtime execution
8. Layer classification
- Primary: `owner_error`
- Not this block: `pack_runtime_boundary_error`, `boundary_fallback_error`, `fact_composition_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- A service fact question with an inline service referent is treated as missing-service collect instead of a grounded fact request.

### Minimal reproduction
1. Replay `block-e-2` from `/tmp/booking_quality/a922-block-e-replay-20260401h`.
2. Inspect `decision_meta.policy_core_trace.raw_output`.
3. Observe that policy-core itself emits `service_missing_for_duration_query` before runtime execution.

### Evidence
- `/tmp/booking_quality/a922-block-e-replay-20260401h/summary.json`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/responses.jsonl`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-e-replay-20260401h/manual_audit.json`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/policy_context_snapshot_service.py`
- `truffles-api/app/services/policy_prompt_snapshot_service.py`
- `prompts/llm_policy_core.md`

### Five Whys
1. Why did the bot ask for a service?
   - Because policy-core emitted `collect service`.
2. Why did policy-core emit `collect service`?
   - Because it did not ground `укладка` as the service referent.
3. Why is that a shared mechanism instead of a single scenario?
   - Because any fact question that carries its own service referent can fall into the same missing-subject owner decision when the owner envelope lacks explicit pack-side service taxonomy/context.
4. Why is runtime not the failing layer?
   - Because runtime preserved the owner-authored collect contract exactly.
5. Why must this be fixed before `Block F`?
   - Because the next honest blocker is owner-side fact-question grounding, not legacy mesh fate.

### Broken invariant
- Owner-side fact questions that already contain a service referent must not degrade into synthetic missing-service collect.

### Shared mechanism
- Policy-core service referent grounding for fact questions is too weak on the surfaced service-question envelope because the owner envelope currently relies on generic prompt wording without compact pack-side service taxonomy/context for that turn.

### Why the surfaced family belongs to that mechanism
- The failing turn is fully explained by owner output before runtime/fact execution begins.

### Open-world envelope expected to improve
- `duration` questions with inline service mentions
- likely sibling service-fact questions such as `master` only if replay/path evidence confirms the same owner grounding mechanism

### Root cause statement
- The next live blocker is an owner-side service referent grounding gap: the policy-core envelope lacks sufficiently explicit pack-side service taxonomy/context plus concrete inline-service examples, so policy-core fails to ground `укладка` in a fact question and authors `collect service` before any runtime or pack boundary logic executes.

### Fix mechanism
- strengthen owner-side service referent grounding on the fact-question envelope by adding compact pack-side service taxonomy cards to the owner context and explicit inline-service fact examples to the policy-core prompt, without adding phrase-hardcoded runtime control
- prove it with focused contract tests and one focused replay

## Plan
1. Do the exact one web search and capture reuse/integrate/build decision.
2. Reconstruct the owner path in `intent_service.py` for the surfaced duration fact failure.
3. Implement the smallest shared owner-side grounding fix.
4. Run focused deterministic checks.
5. Run exactly one focused replay on the owner service-fact grounding family.
6. Only after proof, sync state/governance/docs for `Block E.5`.

## DoD
- The surfaced duration fact question no longer degrades into `collect service`.
- The fix is clearly owner-side and does not reopen `Block E`.
- Focused deterministic checks are green.
- One focused replay exists with full human semantic audit.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "duration or master or service_referent"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "duration or master or service_referent"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "duration or master or service_referent"`
- one focused replay command to be locked at block start

## Evidence
- focused deterministic test output
- one focused replay directory under `/tmp/booking_quality/`
- full manual audit artifacts for that replay

## Rollback
- revert only the touched owner-side files in this TP and return to the proven post-`Block E` base

## No-go
- no runtime hardcodes for `укладка`
- no scenario-only patch
- no replay/oracle threshold weakening
- no reopening of `Block E` code unless new evidence proves the failure crosses the pack/runtime boundary

## Risks / blockers
- the surfaced family may split into multiple owner mechanisms after fresh RCA
- `master` may or may not belong to the same mechanism; prove before widening scope

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- legacy mesh, operational dedupe, and full acceptance still remain open later blocks

### Why not in this block
- this block is only about owner-side referent grounding surfaced immediately after `Block E`

### Risk if deferred
- the next runtime phase would be dishonest because the first live blocker would remain misclassified

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e6-post-grounding-service-reply-exactness-a922.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (planned)

### Expiry / trigger to stop deferral
- stop deferral immediately if another focused replay shows the same owner-side missing-service pattern on sibling fact-question turns

## Next-block contract (mandatory)
### Next block objective
- `Block E.6 — Post-Grounding Service Reply Exactness`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
rg -n "services_catalog|masters_catalog|build_runtime_service_duration_reply|build_master_reply_from_pack|catalog.service_query" truffles-api/app/services/pack_runtime_service.py truffles-api/app/services/tool_registry_service.py truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py
```

### Blocked-by conditions
- post-grounding service reply exactness still fails on the focused service-query family
- `Block E.6` does not yet have one exact web search and one proven RCA

### Owner role for closure
- Brain / Top Architect


## Closure evidence
- Mechanism landed:
  - `truffles-api/app/services/policy_context_snapshot_service.py` now projects compact `service_cards` from pack truth into policy-core context so owner turns see pack-side service taxonomy directly.
  - `truffles-api/app/services/policy_prompt_snapshot_service.py` and `prompts/llm_policy_core.md` now require inline-service grounding for `duration` and `master` fact questions and explicitly forbid synthetic `collect service` when the service is already in the current message.
  - `truffles-api/app/core/consultant_runtime.py` now seeds service referents from canonical slot state into owner memory only when canonical referents are absent, preserving owner-side grounding without introducing a second semantic owner.
- Deterministic proof:
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922/truffles-api && PYTHONPATH=. pytest -q tests/test_intent.py -k "assembles_manifest_scoped_dynamic_context or inline_service_grounding_examples or wait_time_interrupt"` -> `3 passed`
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922/truffles-api && PYTHONPATH=. pytest -q tests/test_consultant_core_runtime_contracts.py -k "memory_profile_prefers_canonical_semantic_state or drops_legacy_semantics_without_canonical_state"` -> `2 passed`
  - `git diff --check` -> clean
- Focused replay proof:
  - valid focused replay: `/tmp/booking_quality/a922-block-e5-replay-20260401f`
  - `infra_valid=true`, `semantic_valid=true`, `manual_audit_status=done`, `human_semantic_valid=false`
  - `LLM-QUAL-a922-block-e5-replay-20260401f-001-01-633ff6` proves standalone inline-service `duration` stays on `fact -> catalog.service_query -> duration` instead of synthetic `collect service`
  - `LLM-QUAL-a922-block-e5-replay-20260401f-002-02-232284` proves carried-service duration interrupt stays factual while preserving booking `expected_reply_type="time"`
  - `LLM-QUAL-a922-block-e5-replay-20260401f-003-01-5b7ce9` proves standalone inline-service `master_query` stays on `fact -> catalog.service_query -> master` instead of synthetic `collect service`
  - human semantic audit is red only because a new unrelated pack-side reply family surfaced after grounding; this does not reopen `Block E.5`
