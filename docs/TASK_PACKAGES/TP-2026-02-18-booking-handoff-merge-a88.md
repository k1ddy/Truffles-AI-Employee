# TP-2026-02-18-booking-handoff-merge-a88

- Название/цель: Stabilize booking followups and handoff gating on top of current main without reopening wide branch conflicts.
- Canon refs: AGENTS.md; STATE.md NOW/GAP (booking quality regressions around redundant followups/escalations).
- Invariant: no extra manager escalation without explicit manager request; keep booking/info behavior deterministic.
- Scope: webhook decision gating + related tests.
- Out of scope: transport/provider infra incidents, telegram media host 404 path.
- Touch-list: `truffles-api/app/routers/webhook/decision.py`, `truffles-api/tests/test_message_endpoint.py`, `truffles-api/tests/test_demo_salon_eval.py`, session docs.
- Plan:
  1. Port minimal gating/followup fixes onto current `main`.
  2. Adjust/extend tests for explicit manager request and no redundant escalations.
  3. Run focused validation and prepare mergeable PR.
- DoD:
  - explicit-manager gate applied in degraded booking/handoff paths.
  - redundant followup prompts suppressed for `calendar.list_slots(ok|specialist_missing)` and `calendar.book_slot(conflict)`.
  - updated tests pass.
- Checks:
  - `python3 -m py_compile truffles-api/app/routers/webhook/decision.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_verification_reuses_active_handover_before_truth_gate or booking_verification_creates_handover_when_none_active or booking_reschedule_missing_slot_does_not_escalate_without_manager_request or llm_policy_core_get_booking_ok_does_not_force_handoff"`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- Evidence: commit diff + test output + PR URL.
- Rollback: revert PR commit.
- No-go: no broad refactor; no policy contract rewrite; no force-push to historical shared branch.
- Риски/блокеры: legacy long-eval instability outside this narrow scope.
