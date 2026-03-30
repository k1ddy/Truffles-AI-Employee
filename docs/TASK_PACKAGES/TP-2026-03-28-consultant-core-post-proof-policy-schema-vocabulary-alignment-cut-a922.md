# TP-2026-03-28-consultant-core-post-proof-policy-schema-vocabulary-alignment-cut-a922

## Title / Goal
Fix the confirmed post-proof practical-proof residual family end-to-end: remove the remaining core phrase-branching debt from `info.py`, align llm-quality oracle/judge logic with the governed handoff + booking-lookup-reference contracts, and rerun practical proof on current-head runtime.

## Canon Refs
- `STATE.md` — current worktree truth
- `AGENTS.md` — one-web-search / root-cause / local-first realism / no-hardcode gates
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — target architecture still requires governed semantic ownership to hold in practice
- practical run evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260328-r8/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.json,scenarios.json}`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r11/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.json,scenarios.json}`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.json,scenarios.json}`

## One Web Search (mandatory before implementation)
- Query: `OpenAI evals official docs contract-based grader traces`
- Date/time: `2026-03-29T00:36:00+05:00`
- Opened sources:
  - `https://platform.openai.com/docs/guides/evals`
- High-signal source quality:
  - Official OpenAI evaluation guidance.
- Found reusable idea:
  - Graders/evals should judge against explicit machine-readable contracts and observable intermediate artifacts, not against hidden assumptions about text-only behavior.
- Reuse / integrate / build decision:
  - `integrate + build`
- Why:
  - The repo already owns contract-first replay artifacts (`decision_meta`, `trace_bundle`, `runtime_trace_contract`); the correct fix is to align the judge/oracle with those governed artifacts rather than weakening replay gates or adding scenario-specific waivers.
- Rejected options:
  - Weaken `judge_fail` / `expected_reply` globally: rejected because it would hide real regressions instead of fixing the contract mismatch.
  - Special-case surfaced turns by scenario ID: rejected because the residual is a family-level oracle/hardcode defect, not a one-off turn bug.

## Root Cause (mandatory)
### Symptom
The practical current-head replay `/tmp/booking_quality/a922-practical-proof-20260328-r8` still failed semantic validity after the broader governance work. The remaining live family is no longer a runtime-owner drift family; it is a bounded practical-proof family:
- stale oracle semantics for explicit handoff replies (`expected_reply=false` treated as "no bot reply"),
- stale oracle/judge semantics for booking-lookup reference prompts after `check_booking`,
- and live `hardcode_core_gate` phrase branching in `truffles-api/app/routers/webhook/info.py`.

### Minimal Reproduction
1. Run the practical replay against current-head runtime:
   - `python3 ops/diagnose.py llm-quality ... --run-id a922-practical-proof-20260328-r8 ...`
2. Inspect the remaining failing turns:
   - `LLM-QUAL-a922-practical-proof-20260328-r8-003-01-550d3d`
   - `LLM-QUAL-a922-practical-proof-20260328-r8-009-02-a770d4`
3. Inspect the hardcode gate violations:
   - `python3 - <<'PY'\nimport json\nfrom pathlib import Path\nsummary = json.loads(Path('/tmp/booking_quality/a922-practical-proof-20260328-r8/summary.json').read_text())\nprint(summary['hardcode_core_gate'])\nPY`
4. Inspect the evaluator / scenario / judge paths:
   - `ops/diagnose.py`
   - `truffles-api/app/services/llm_quality_contracts.py`
   - `scripts/booking_dialog_scenarios.py`
   - `truffles-api/app/routers/webhook/info.py`

### Evidence
- `/tmp/booking_quality/a922-practical-proof-20260328-r8/summary.json`
- `/tmp/booking_quality/a922-practical-proof-20260328-r8/responses.jsonl`
- `/tmp/booking_quality/a922-practical-proof-20260328-r8/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-practical-proof-20260328-r8/scenarios.json`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`

### Five Whys
1. Why did the practical replay still fail after the broader governance cutover?
   - Because the remaining blockers moved out of owner/runtime logic and into oracle/judge semantics plus one live core hardcode seam.
2. Why did the explicit handoff turn fail?
   - Because llm-quality still interpreted `expected_reply=false` as "the bot must stay silent", even when the scenario explicitly expected a handoff transition with a delivered handoff reply.
3. Why did the booking-lookup turn fail?
   - Because the scenario/judge still expected the older `time` follow-up semantics for `confirm/check_booking`, while the current governed runtime correctly used `calendar.get_booking` and asked for missing booking reference (`name` / booking reference follow-up).
4. Why did the judge overrule the runtime on that turn?
   - Because the judge prompt still encoded stale assumptions (`pending reply => fail`, `expected_reply=false + bot reply => fail`) and did not state the valid booking-lookup-reference contract explicitly.
5. Why did proof still fail even when only two turns remained?
   - Because the proof block was still mixing evaluator/scenario defects with a hardcode gate residue. In the current worktree the `info.py` phrase-branching seam is already removed, so the remaining implementation target is the llm-quality oracle/judge + scenario-repair layer.

### Root Cause Statement
The remaining practical failure family is no longer owner-contract drift. It is now a proof-layer mismatch: llm-quality oracle/judge logic still carries stale assumptions about handoff replies and booking-lookup reference prompts, and generated scenario repair still emits stale `confirm -> time` expectations after active `check_booking`.

### Follow-up Runtime Family Discovered During Practical Replay
After the oracle/judge family was fixed and replayed, the next live family surfaced on the active runtime path:
- logical `info` owner outputs without governed concrete info refs could fall through `_execute_fact(...)`
- the unresolved logical-info path could return the inbound user text as the final fact fallback
- this produced a real product/runtime defect on booking info interrupts (`"Есть ли акции?"` -> echoed user text) and was not an oracle-only issue

That follow-up family was fixed in the same bounded block by:
- routing unresolved logical `info` turns through governed concrete info tool candidates from `tool_registry_snapshot_service`
- removing echo-as-fallback behavior from unresolved fact execution
- aligning `hardcode_core_gate` with current worktree content so deleted phrase branches no longer survive as stale `base_diff` violations

### Fix Mechanism
1. Keep the `info.py` surface lexicon/pack-driven and close the remaining services-overview data gap through governed lexicon data, not raw phrase branching.
2. Align llm-quality evaluator so `expected_reply=false` does not falsely penalize explicit handoff replies, and booking-lookup reference prompts do not falsely register stale meta mismatches.
3. Align scenario repair for `check_booking -> confirm` follow-up turns so future generated dialogs reflect the governed booking-reference contract instead of stale `time` expectations.
4. Align the judge prompt with contract semantics so handoff replies and booking-lookup reference prompts are judged against machine-readable contract evidence.
5. Re-run practical replay on the same current-head runtime and read the new family boundary from artifacts, not assumptions.

## Invariant
- No scenario-specific hardcodes or evaluator waivers by dialog ID / surfaced turn ID.
- Semantic ownership stays in policy-core; planner/runtime may only validate, degrade, and trace contractually.
- Hardcode removal must move semantics toward lexicon/pack/runtime owners, not delete behavior.

## Scope
- proof-layer alignment for the remaining handoff + booking-lookup family
- governed lexicon alignment for the remaining services-overview phrase gap
- bounded llm-quality oracle alignment for explicit handoff replies and booking-lookup reference prompts
- scenario repair alignment for generated `check_booking -> confirm` follow-up turns
- judge prompt alignment for the same governed contracts
- deterministic + practical proof rerun on the same family

## Out of Scope
- broad owner/runtime semantic changes
- acceptance-lane baseline promotion
- unrelated legacy mesh cleanup
- generic judge-rubric redesign beyond this bounded handoff + booking-lookup family

## Touch-list
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-post-proof-policy-schema-vocabulary-alignment-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Save the confirmed RCA in this TP and use it as the only implementation family for this block.
2. Close the remaining services-overview lexicon gap without reintroducing phrase hardcodes.
3. Align llm-quality evaluator with the explicit handoff and booking-lookup reference contracts.
4. Align generated-scenario repair for `check_booking -> confirm` follow-up turns.
5. Align judge prompt/suppression with the same governed contracts.
6. Run focused deterministic checks.
7. Re-run a practical llm-quality replay on current-head runtime and audit the result truthfully.
8. Update repo truth only after the practical rerun outcome is known.

## DoD
- llm-quality no longer flags stale `expected_reply_mismatch` for explicit handoff replies.
- llm-quality no longer flags stale `expected_meta_mismatch` / `judge_fail` for the canonical booking-lookup reference prompt family.
- generated `check_booking -> confirm` follow-up turns no longer force stale `time` expectations.
- `hardcode_core_gate` remains green for the current `info.py` surface.
- Focused deterministic checks are green.
- A new practical replay is executed and audited on current-head runtime.
- `STATE.md` reflects the real result, pass or fail.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/app/services/llm_quality_contracts.py scripts/booking_dialog_scenarios.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_dialog_scenarios_script.py truffles-api/tests/test_booking_quality_judge_suppression.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "booking_lookup_reference or expected_reply_false or handoff_reply"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k "check_booking_confirm or check_booking_followup"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py -k "check_booking or booking_lookup"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py -k "services_overview or promotions"`
- practical replay on current-head runtime with post-run audit
- `git diff --check`

## Evidence
- Updated TP with confirmed RCA
- deterministic test output
- practical replay artifacts:
  - `/tmp/booking_quality/a922-practical-proof-20260328-r11/`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/`
- updated `STATE.md`

## Release Safety
- Local worktree only
- No deploy / no production rollout in this block
- Current-head proof runtime remains isolated from shared `:8000`

## Rollback
- Revert touched files in this worktree.

## No-go
- No scenario-specific phrase hardcodes.
- No disabling of structured output to hide the bug.
- No weakening of semantic validation or quality gates.
- No baseline update from a dev-lane replay.

## Risks / Blockers
- The real semantic family may require widening governed vocabulary in more than one place.
- One runtime fallback family is still not fully traced; if it is independent, it may stay as residual after this block.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- There may still be a separate runtime fallback family after this oracle/hardcode fix.
- Judge-oracle conflicts outside the bounded handoff + booking-lookup family are not the main target of this block.

### Why not in this block
- This block is scoped to the confirmed proof-layer mismatch family plus the minimum hardcode removal needed to reopen practical proof truthfully.

### Risk if deferred
- Practical proof may still surface a different runtime family after this block once oracle/hardcode blockers are removed.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-post-proof-runtime-fallback-causal-trace-closeout-a922.md` (planned if needed)

### Expiry / trigger to stop deferral
- Stop deferral immediately if the new practical replay still contains a separate runtime-fallback family after this bounded owner-contract family is fixed.

## Next-block Contract (mandatory)
### Next block objective
If this family is fixed, open the next bounded practical family from the new replay result, most likely runtime fallback or remaining judge-only conflicts.

### First deterministic check command
`python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/<new-run-id> --status done --strict-artifacts`

### Blocked-by conditions
- This family must first rerun practical proof on current-head runtime.

### Owner role for closure
- Brain / Top Architect
