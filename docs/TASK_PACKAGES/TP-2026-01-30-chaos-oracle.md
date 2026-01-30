- Название/цель: TP-2026-01-30 — chaos-oracle для 5 сценариев + P0 фиксы (mixed OOD/in-domain, explicit-service > context, deterministic service_not_found, guest_policy animals, booking_interrupt) + tests/evidence.
- Canon refs: `STATE.md` (PLAN TP-2026-01-24-consult-quality-core-v1; OPEN chaos-sim OOD residuals), `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`; CA IDs: CA-04 (service matcher), CA-07 (OOD), CA-01/02 (payment policy), CA-05 (booking commit), CA-06 (consult).
- Invariant:
  - Hard-LAW/policy/pending remain pre-LLM and fail-closed.
  - decision_meta/decision_trace recorded on every user message and early return.
  - No orchestration added to entrypoints or `_legacy.py`; stage order snapshot preserved (hash updated only if order changes).
- Scope:
  - Oracle for 5 chaos scenarios (per-turn expected action/intent/trace).
  - Pack-gap fixes (lexicon/anchors) for guest_policy animals, in-domain anchors, service_request for not-offered.
  - Fix explicit service in text to override context-derived service.
  - Prevent early OOD when in-domain anchor exists in mixed messages.
  - Deterministic service_not_found for explicit unknown service query (not only RAG empty).
  - Ensure booking_interrupt returns slot prompt after info reply during active booking.
- Out of scope:
  - New providers, calendar/CRM changes, pack layering, tool registry, DB migrations.
  - Any orchestration changes in entrypoints or `_legacy.py`.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `truffles-api/app/knowledge/demo_salon/EVAL.yaml`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `truffles-api/tests/test_message_endpoint.py`
- Plan:
  1) Start session/worktree after this Task Package is recorded.
  2) Build oracle table for 5 scenarios (expected action/intent/trace per turn).
  3) Map pack-gaps vs oracle; update lexicon/anchors in packs.
  4) Fix explicit-service priority over context.
  5) Adjust OOD gate for mixed messages with in-domain anchors.
  6) Make service_not_found deterministic for explicit unknown service queries.
  7) Confirm booking_interrupt behavior for info interruptions.
  8) Add/adjust EVAL cases + tests; run targeted pytest; capture evidence.
- DoD:
  - Each scenario turn maps to expected action/intent/trace (oracle covered by EVAL/tests).
  - Mixed OOD+in-domain messages do not go OOD when in-domain anchor exists.
  - service_not_found triggers on explicit unknown service request (even without semantic match).
  - booking_interrupt answers info and returns slot question.
  - Tests pass; evidence recorded in `STATE.md` (Brain/Top Architect) before merge.
- Checks:
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py -k "SCN1 or SCN2 or SCN3 or SCN4 or SCN5"`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "out_of_domain or service_not_found or booking_interrupt"`
- Evidence:
  - Pytest outputs for checks above.
  - decision_meta/trace extracts for key scenario turns (livecheck only if required by CA matrix).
- Rollback:
  - `git revert HEAD`.
- No-go:
  - No DB edits for evidence.
  - No new orchestration in `_legacy.py` or entrypoints.
  - No stage order change without snapshot hash update.
- Риски/блокеры:
  - Domain anchors in runtime config may drift from pack data; verify before relying on pack-only signals.
  - Qdrant services_index drift can affect semantic match; ensure service_not_found remains deterministic.
- Branch/worktree:
  - Branch: `feat/2026-01-30-chaos-oracle-a1`
  - Worktree: `/home/zhan/worktrees/2026-01-30-chaos-oracle-a1`
  - Base ref: `origin/main`
  - Merge policy: PR + CI (merge-only)
  - Cleanup: Brain after merge
