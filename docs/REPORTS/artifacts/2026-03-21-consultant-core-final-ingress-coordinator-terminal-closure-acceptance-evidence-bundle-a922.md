# 2026-03-21 — Consultant Core Final Ingress Coordinator Terminal Closure Acceptance Evidence Bundle A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-EVIDENCE-BUNDLE-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Classified surfaced family `a922-weekend-slot-constraint-dev-r79` as a proved `core contract bug`, not pack/readiness/oracle.
- Root cause: shared `_detect_info_class_intents(...)` returned no promo intent for `Есть ли у вас акции на маникюр?` even though existing promo policy detection already returned `True`.
- Fixed the shared info-class resolver so it now compiles `promotions` / `promotions_rules` into runtime intents and `info_signals`.
- Added deterministic regressions for the classifier and for the active booking interrupt path preserving `expected_reply_type=time` after a promotions reply.

## RCA evidence
- Before fix:
  - `_detect_info_class_intents('Есть ли у вас акции на маникюр?', ...) -> set()`
  - `looks_like_promotions_policy_message(...) -> True`
- Surfaced failing row remained:
  - `message_id=LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4`
  - `turn_text=Есть ли у вас акции на маникюр?`
  - `outbox_text=Понял, в субботу по услуге «Маникюр». Подскажите, пожалуйста, точное время.`
  - strict reasons: `expected_info_section_miss`, `info_section_miss`, `judge_fail`
- After fix:
  - `_detect_info_class_intents('Есть ли у вас акции на маникюр?', ...) -> {'promotions'}`
  - `_detect_info_class_intents('Акции и скидки суммируются?', ...) -> {'promotions_rules'}`

## Code changes
- `truffles-api/app/routers/webhook/info.py`
  - shared info-class intent resolver now emits `promotions` / `promotions_rules` via existing info-signal helpers
  - `info_signals` now expose promo booleans alongside other shared info intents
- `truffles-api/tests/test_master_info_flow.py`
  - added deterministic classifier coverage for `promotions` and `promotions_rules`
- `truffles-api/tests/test_reasoning_core.py`
  - added active-booking promo interrupt regression proving truth reply + preserved `expected_reply_type=time`
  - updated stale promo delegate bridge tests to current runtime truth: safe info owner handles promo / promo-rules directly without frozen delegate

## Checks + outcomes
- `pytest -q truffles-api/tests/test_master_info_flow.py -k 'promotions'` -> `4 passed, 31 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'turn_planner_safe_info_owner_handles_promotions_without_frozen_delegate or turn_planner_safe_info_owner_handles_promotions_rules_without_frozen_delegate or booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect'` -> `3 passed, 181 deselected`
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py` -> `7 passed`
- shared classifier probe after fix confirms `promotions` / `promotions_rules` intent emission

## Residual debt
- Guarded `demo_salon/main` canary replay is still pending; deterministic evidence alone does not close final acceptance.
- Multi-pack matrix / open-world closure remain open.

## Next move
- `reenter_consultant_core_demo_salon_main_canary_after_promo_interrupt_contract_closure`
