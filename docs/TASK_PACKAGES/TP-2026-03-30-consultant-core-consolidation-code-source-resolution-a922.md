# TP-2026-03-30-consultant-core-consolidation-code-source-resolution-a922

- Title/Goal: Collapse the remaining code/test conflict set into one coherent continuation line by authoritative source selection instead of blind merge.
- Canon refs: `STATE.md`; `STRUCTURE.md`; `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922.md`; `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- Invariant: One continuation worktree only; no blind merge from dirty sources; preserve all prior work via freeze bundles and imported reports/TPs.
- Scope:
  - resolve remaining code/test conflicts by source-of-truth selection
  - keep governance-lock as consultant-core code line
  - keep practical-closure quality workflow tooling/tests where governance line does not exist or where process quality is newer
- Out of scope:
  - no new behavioral implementation families
  - no replay closure claims
- Touch-list:
  - remaining non-doc true-conflict files in the consolidation worktree
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-source-resolution-a922.md`
- Plan:
  1. Use the conflict shortlist to choose authoritative source per remaining file.
  2. Copy source-picked versions into the consolidation worktree.
  3. Run targeted compile/tests to verify the line is coherent enough to continue.
  4. Record residual behavioral reimplementation debt explicitly.
- Work mode: implementation
- DoD:
  - remaining code/test conflict files are source-picked into the single worktree
  - targeted compile/tests pass
  - residual behavioral debt is documented explicitly
- Checks:
  - `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/services/intent_service.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_intent.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "human_semantic or product_quality"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "context_manager_expected_reply_getters_prefer_conversation_projection_over_canonical_question_contract or policy_has_style_reference_hint_from_intent_or_reason"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py::TestPolicyCoreOverride::test_route_llm_policy_core_no_longer_contains_override_short_circuit truffles-api/tests/test_intent.py::TestPolicyCoreTimeoutRetry::test_timeout_retry_uses_fallback_model_when_primary_times_out`
- Evidence:
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-source-resolution-a922.md`
- Rollback:
  - revert the source-pick commit in the consolidation worktree
- No-go:
  - no wholesale branch merge
  - no continuation work in `truffles-main` or the old fragmented worktrees
- Risks/blockers:
  - source-pick coherence does not equal full behavioral closure; practical behavior families still need family-level replay and audit on this line
- Residual architecture debt (mandatory):
  - Current residuals accepted in this block: practical product fixes from the old practical-closure line are preserved, but not all are semantically replayed yet on the single governance continuation line.
  - Why not in this block: this block is only about conflict collapse and coherent continuation base recovery.
  - Risk if deferred: later engineers may assume imported docs imply imported behavior.
  - Linked follow-up Task Package(s): next family-level replay/reimplementation block on the single consolidation line.
  - Expiry/trigger to stop deferral: before any product-quality closure claim.
- Next-block contract (mandatory):
  - Next block objective: reopen consultant-core practical family work only on this single consolidation line, starting from the top blocker family in the imported practical reports.
  - First deterministic check command: `git -C /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922 status --short`
  - Blocked-by conditions: source-pick line not clean or targeted import checks red.
  - Owner role for closure: Brain / Top Architect.
