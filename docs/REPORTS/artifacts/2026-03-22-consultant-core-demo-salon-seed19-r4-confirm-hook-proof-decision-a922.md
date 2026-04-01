# 2026-03-22 - Consultant Core Demo Salon Seed19 R4 Confirm Hook Proof Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-PROOF-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Promoted exact replay `r4` from replay evidence to one bounded proof/tool-evidence decision.
- Proved that `confirm_hook_missing` is not a new runtime blocker and not a transport/readiness failure.
- Proved that `r4` is infra-invalid because `ops/diagnose.py` counts `check_booking` as confirm evidence opportunity while the synthetic confirm-hook sender does not mirror that rule on `confirm`-tagged `check_booking` turns.
- Locked the next move to one contract-aligned proof implementation family inside `ops/diagnose.py` before any more runtime or acceptance work.

## Evidence chain
### 1. `r4` is infra-red before runtime reclassification
- Run: `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
- Audit: `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`
- Core facts:
  - `infra_valid=false`
  - `semantic_valid=false`
  - `quality_status.infra_reasons=['tool_evidence:confirm_hook_missing']`
  - `tool_evidence.valid=false`
  - `tool_evidence.reasons=['confirm_hook_missing']`
  - `tool_evidence.counts.confirm_tool_events=2`
  - `tool_evidence.counts.confirm_hook_events=0`
  - `tool_evidence.counts.confirm_opportunity_total=4`
- Verdict:
  - the first admissible blocker on `r4` is proof/tool-evidence, not runtime semantics

### 2. The confirm hooks were never attempted on the observed `r4` prefix
- Artifact: `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
- Observed confirm-required rows:
  - dialog `1`, turn `12`
  - dialog `2`, turn `7`
- Shared facts on both rows:
  - `turn_tags=['confirm']`
  - `tool_signals.confirm.required=true`
  - `tool_signals.calendar.intent='check_booking'`
  - `tool_hooks=['calendar']`
  - no `confirm` hook send attempt and no confirm-hook transport error are recorded
- Verdict:
  - this is not a delivery/readiness failure; the confirm hook was not sent in the first place

### 3. The parity drift is inside `ops/diagnose.py`
- Hook sender:
  - `ops/diagnose.py:5412-5430`
  - `_llm_quality_should_send_confirm_hook(...)` returns `True` for any non-`confirm` tagged turn, but on `confirm`-tagged turns it only sends the synthetic confirm hook when the normalized calendar intent is exactly `calendar.get_booking`
- Strict evidence counter:
  - `ops/diagnose.py:11676-11731`
  - `_llm_quality_build_tool_evidence_status(...)` counts `check_booking`, `check_record`, and `calendar.get_booking` as confirm candidates and raises `confirm_hook_missing` whenever strict confirm evidence is required but no confirm hook was observed
- Deterministic contract clue already codified in tests:
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` explicitly asserts that `check_booking` normalizes to `confirm.required=true`
- Verdict:
  - the sender and the counter are out of parity on `confirm`-tagged `check_booking` turns

### 4. Why the old blocker artifact stayed infra-valid
- Old blocker run: `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- Facts:
  - `infra_valid=true`
  - `tool_evidence.valid=true`
  - `confirm_hook_events=2`
- Supporting row evidence from `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`:
  - confirm hooks were observed later on untagged `check_booking` rows (dialogs `4` and `7`, turn `3`)
- Replay consequence:
  - fail-fast `r4` stopped after dialog `2`, so it never reached the later untagged rows that had previously satisfied the confirm-hook requirement
- Verdict:
  - the exact replay surfaced a hidden proof parity bug because the later masking rows were not reached

### 5. The downstream semantic row is still not admissible
- `r4` fail-fast row:
  - dialog `2`, turn `9`
  - strict reasons: `expected_meta_mismatch`, `expected_trace_miss`
  - runtime owner: `turn_planner_safe_explicit_handoff_owner`
- Decision:
  - do not reopen runtime work from this row yet; it remains downstream until `infra_valid=true`

## Admissible implementation lane
- Future implementation must stay bounded to:
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
  - any minimal companion proof test if the gate surface requires it
- It must align one of these, without touching runtime:
  - confirm-hook eligibility for `confirm`-tagged `check_booking` turns
  - or strict evidence counting so fail-fast prefixes do not require a confirm hook that the sender intentionally suppresses
- Explicitly not admissible:
  - runtime patching
  - threshold weakening
  - acceptance checklist work
  - scenario mutation before proof parity is fixed

## Residual debt
- downstream `r4` semantic mismatch remains unresolved debt until infra is repaired
- acceptance evidence-pack materialization and seed `42` remain deferred
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt

## Next move
- `implement_consultant_core_demo_salon_seed19_r4_contract_aligned_confirm_hook_proof_family`
