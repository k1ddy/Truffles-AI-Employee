Title/Goal
- Freeze `r12` as the clean nano practical reference, then run one controlled `nano -> mini` comparison on the exact same frozen scenario set so the remaining quality delta can be attributed to model behavior rather than system/runtime defects.

Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-post-proof-policy-schema-vocabulary-alignment-cut-a922.md`
- Practical reference artifacts:
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/summary.json`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/brief.md`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260328-r12/manual_audit.json`

Invariant
- Do not change runtime code or scenario content during the comparison.
- Compare only one variable: semantic-owner model (`gpt-5.4-nano-2026-03-17` vs verified mini model).
- Keep judge settings, frozen scenarios, runtime image/code, tool hooks, and gates identical.

Scope
- Save `r12` as the current clean nano reference.
- Verify the exact mini model identifier against the real OpenAI model list using the repo-resolved key.
- Run one mini replay against the exact same frozen scenario file and runtime code.
- Strict-audit the mini run and compare it with `r12`.

Out of scope
- Any new runtime bugfix.
- Any prompt rewrite.
- Any scenario/oracle/judge rule change.
- Any production rollout decision beyond the model-routing recommendation.

Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-practical-model-ab-comparison-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `/tmp/booking_quality/a922-practical-proof-20260328-r12/*`
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/*`
- proof runtime container configuration for the mini replay

Work mode (mandatory)
- `closure`

One web search (mandatory before implementation)
- Not applicable: this block is a bounded local practical-proof comparison and does not introduce a new implementation family.

Root cause (mandatory)
- Symptom:
  - remaining uncertainty whether the residual quality floor is now dominated by the `nano` model or by system/runtime defects.
- Minimal reproduction:
  - replay the exact frozen `r12` scenario set on current-head runtime while changing only the semantic-owner model.
- Evidence:
  - `r12` is now clean on `nano` (`infra_valid=true`, `semantic_valid=true`, `failure_families=0`, `blocking_reasons=0`).
- Five Whys:
  1. Why is model contribution still uncertain? Because previous practical failures mixed system defects with owner behavior.
  2. Why did that happen? Because schema/vocabulary/runtime/hardcode defects were still present during earlier replays.
  3. Why is that no longer enough? Because those bounded system defects are now closed and `r12` is green.
  4. Why compare on frozen scenarios? To isolate model quality from scenario drift and runtime drift.
  5. Why compare `nano` with `mini` now? To decide whether any remaining residual should be solved by routing/escalation rather than new core changes.
- Root cause statement:
  - the open question is no longer architectural correctness but model-only quality contribution, which can only be measured by a controlled replay on identical inputs.
- Fix mechanism:
  - run one strict `mini` replay against the frozen `r12` scenario set, then compare the audited artifacts directly.

Plan
1. Record `r12` as the clean nano practical reference in canon.
2. Verify the exact mini model identifier via repo-resolved OpenAI key and model list.
3. Start a sibling proof runtime on the same code with `LLM_SEMANTIC_OWNER_MODEL=gpt-5.4-mini-2026-03-17`.
4. Replay the exact `r12` scenario set with unchanged llm-quality gates and judge settings.
5. Run strict post-audit on the mini replay.
6. Compare nano vs mini artifacts and summarize the model-only delta and routing decision.

DoD
- `r12` is explicitly recorded as the clean nano reference.
- Exact mini model identifier is verified from the real model list, not guessed.
- Mini replay uses the exact same `scenarios.json` as `r12`.
- Mini replay is strict-audited.
- Comparison summary is evidence-backed and distinguishes model delta from non-model defects.

Checks
- `python3 - <<'PY' ... /v1/models ... PY` to verify `gpt-5.4-mini-2026-03-17`
- `python3 ops/diagnose.py llm-quality ... --scenarios-file /tmp/booking_quality/a922-dev-reset-check-16/scenarios.json ... --llm-model gpt-5.4-mini-2026-03-17 --run-id a922-practical-proof-20260328-mini-r1`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260328-mini-r1 --status done --strict-artifacts`
- `git diff --check`

Evidence
- `r12` artifacts listed above
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/*` audit noting the first mini attempt was invalid for comparison because `LLM_POLICY_CORE_MODEL` still pointed at nano and the run stopped early
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/summary.json`
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/brief.md`
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/responses.jsonl`
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-practical-proof-20260328-mini-r1/manual_audit.json`

Rollback
- Stop and remove the mini proof runtime container.
- Keep `r12` as the canonical practical reference.
- Revert only doc updates if the comparison run is invalid.

No-go
- No runtime code edits during the comparison.
- No scenario regeneration.
- No judge-model change.
- No threshold weakening.
- No interpretation of invalid or non-audited runs as model evidence.

Risks/blockers
- Mini replay can be invalid if runtime container is not actually switched to the mini model.
- Judge conflict can remain as advisory noise; it must not be misread as runtime/model failure if arbitration keeps contract authoritative.

Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - no hybrid routing implementation yet; this block only measures the delta.
- Why not in this block:
  - routing changes would contaminate the measurement.
- Risk if deferred:
  - model cost/quality decision remains anecdotal.
- Linked follow-up Task Package(s):
  - next bounded routing-decision block after the comparison summary.
- Expiry/trigger to stop deferral:
- comparison summary completed and reviewed.

Next-block contract (mandatory)
- Next block objective:
  - decide whether semantic-owner routing should stay on `nano` everywhere or escalate selected families to `mini`.
- First deterministic check command:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260328-mini-r1 --status done --strict-artifacts`
- Blocked-by conditions:
  - mini replay invalid, non-audited, or not run on the exact frozen scenario set.
- Owner role for closure:
  - Brain / Top Architect

Execution result
- Verified via live OpenAI model list and preflight:
  - `gpt-5.4-mini-2026-03-17` exists and passes chat-completions preflight.
- `r12` remains the clean nano reference:
  - `infra_valid=true`
  - `semantic_valid=true`
  - `failure_families=0`
  - `blocking_reasons=0`
- `mini-r1` is non-canonical and superseded:
  - interrupted early
  - runtime still used nano because `LLM_POLICY_CORE_MODEL` was not switched yet
- `mini-r2` is the valid comparison run:
  - runtime policy-core traces show `model_name=gpt-5.4-mini-2026-03-17` on all 15 turns
  - `infra_valid=true`
  - `semantic_valid=true`
  - `failure_families=0`
  - `blocking_reasons=0`
  - `oracle_arbitration.judge_alignment=corroborated`
- Comparison outcome:
  - both models pass the frozen suite cleanly
  - mini is slower (`avg 4153.52 ms` vs `3572.34 ms`; `p90 5865.59 ms` vs `4268.3 ms`)
  - mini removes the lone r12 advisory judge conflict, but does not improve acceptance metrics because nano is already green on this suite
  - mini changes semantic envelopes on multiple turns; the most important difference is the consult-photo turn where mini produces a consult path that degrades through `policy_projection:tool_action_unknown:consult`, which remains contract-valid but shows consult-binding debt rather than a clean model win
- Practical routing recommendation:
  - keep `nano` as default
  - use future selective escalation to `mini` only if a broader frozen suite proves stable quality wins on specific families and after consult-binding debt is closed
