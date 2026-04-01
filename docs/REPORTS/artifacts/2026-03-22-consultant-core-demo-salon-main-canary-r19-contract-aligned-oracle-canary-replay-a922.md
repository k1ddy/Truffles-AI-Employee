# 2026-03-22 — Consultant Core Demo Salon Main Canary R19 Contract-Aligned Oracle Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local runtime on `127.0.0.1:18186`, ran one guarded comparable replay, strict-audited `/tmp/booking_quality/a922-check-booking-proof-r20`, and then stopped the local listener.
- `r20` is now truthful green on the locked demo-salon canary surface:
  - `infra_valid=true`
  - `semantic_valid=true`
  - `turns_strict_failed=0`
  - `blocking_reasons={}`
- The bounded `ops/diagnose.py` oracle-parity family is closed on fresh evidence.
- The remaining judge conflicts on turns `6`, `9`, `11`, and `12` stay advisory-only under manual audit (`winner=contract`, `conflict_count=4`); they no longer block semantic validity.

## Replay result
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r20`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r20 --status done --strict-artifacts`
- Locked scenario: `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
- Runtime preflight:
  - `http://127.0.0.1:18186/admin/health` → `200`
  - `http://127.0.0.1:18186/admin/version` → `200`
- Summary facts:
  - `dialogs=1`
  - `turns=14`
  - `turns_strict_passed=14`
  - `suppressed_missed_question_count=4`
  - `judge_fail_advisory_turns=0`

## Surfaced turns
- `turn 6`
  - user: `Кто из мастеров лучше делает маникюр?`
  - strict verdict: green
  - judge conflict remains advisory only; semantic validity stays green
- `turn 9`
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - strict verdict: green
  - HQ1 no longer emits `handoff_miss`
- `turn 11`
  - user: `Подтвердите, пожалуйста, запись на маникюр.`
  - strict verdict: green
  - judge conflict remains advisory only
- `turn 12`
  - user: `Можно на 19:00?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - strict verdict: green
  - HQ1 no longer emits `handoff_miss`
- `turn 14`
  - user: `Можно связаться с менеджером?`
  - bot: explicit handoff reply
  - `conversation_state=pending`
  - strict verdict: green

## Closure verdict
- No honest demo-salon main-canary runtime blocker survives.
- No honest demo-salon main-canary oracle blocker survives either; the family is now advisory-only under manual audit.
- The next blocker is no longer inside this canary family. It returns to final acceptance evidence / multi-pack closure.

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py` → `pass`
- `pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"` → `15 passed, 111 deselected`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-check-booking-proof-r20 ...` → fresh replay artifact produced
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r20 --status done --strict-artifacts` → `semantic_valid=true`, `winner=contract`, `conflict_count=4`

## Residual debt
- final program acceptance evidence is still open; this replay is dev-lane evidence, not the full canonical acceptance bundle
- duplicate top-level defs remain deferred in `truffles-api/app/services/reasoning_core.py`
- multi-pack/open-world closure remains open

## Next move
- `implement_consultant_core_final_ingress_coordinator_terminal_closure_acceptance_evidence_bundle`
