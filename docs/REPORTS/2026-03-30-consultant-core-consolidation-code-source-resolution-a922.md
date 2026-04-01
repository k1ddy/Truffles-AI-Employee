# Consultant-Core Consolidation Code Source Resolution

## Goal

Collapse the remaining code/test conflict set into one coherent continuation line quickly, without blind merging incompatible dirty worktrees.

## Source-of-Truth Rule Used

- Consultant-core runtime/code/test continuation line: `governance-lock`
- Practical quality workflow tooling and practical-only quality tests: `practical-closure`
- `truffles-main`: forensic residue only, not a continuation source

## Applied Source Picks

### Practical-closure picks
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_master_info_flow.py`

### Governance-lock picks
- all remaining consultant-core runtime/router/service/test conflict files from the freeze inventory, including:
  - `prompts/llm_policy_core.md`
  - `truffles-api/app/routers/webhook/{booking.py,decision.py,info.py,...}`
  - `truffles-api/app/services/{intent_service.py,tool_registry_service.py,...}`
  - governance-side contract/runtime tests

## Why this is the fast safe resolution

- `governance-lock` is the only checkout carrying the consultant-core implementation line (`W1-W8` code artifacts).
- `practical-closure` code line is not a descendant of that implementation line. Blind code merge would be slower and less reliable than authoritative source selection.
- practical behavioral work is still preserved through:
  - freeze bundles
  - practical reports/TPs already imported into the consolidation worktree
  - practical quality workflow tooling/tests retained from `practical-closure`

## Validation

- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/services/intent_service.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_intent.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "human_semantic or product_quality"` -> `4 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "context_manager_expected_reply_getters_prefer_conversation_projection_over_canonical_question_contract or policy_has_style_reference_hint_from_intent_or_reason"` -> `2 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py::TestPolicyCoreOverride::test_route_llm_policy_core_no_longer_contains_override_short_circuit truffles-api/tests/test_intent.py::TestPolicyCoreTimeoutRetry::test_timeout_retry_uses_fallback_model_when_primary_times_out` -> `2 passed`
- `git diff --check` -> `pass`

## Residual

This step resolves the file-level conflict source selection. It does not prove that every practical product fix from `practical-closure` has been semantically reimplemented on the consultant-core governance line. Those practical behavior families remain preserved in imported reports/TPs and must be replayed family-by-family on this single continuation line.
