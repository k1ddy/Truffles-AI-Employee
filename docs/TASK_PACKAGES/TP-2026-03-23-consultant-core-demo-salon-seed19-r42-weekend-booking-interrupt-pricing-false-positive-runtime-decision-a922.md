# TP-2026-03-23 Consultant Core Demo Salon Seed19 R42 Weekend Booking Interrupt Pricing False Positive Runtime Decision A922

## Title/goal
Classify the first surviving blocker after the truthful `r42` completion replay and lock the next bounded runtime family for the weekend booking-interrupt pricing false positive.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r42-weekend-booking-interrupt-pricing-false-positive-family`

## One web search (mandatory before implementation)
- **Query (exact):** `Python re word boundary whole word match official documentation`
- **Date/time (local):** `2026-03-23 18:18 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3.9/howto/regex.html`
- **Found ready-made solutions:** Python's official regex HOWTO documents `\b` as a word-boundary assertion that matches complete words and does not match substrings inside larger words.
- **Decision:** `reuse` the repo's existing whole-word helper and build a bounded resolver/runtime fix.
- **Why:** the surfaced blocker is caused by local substring keyword matching inside the existing resolver path; a new dependency or framework is unnecessary.
- **Rejected options:** removing replay gates, oracle downgrades, frozen-router edits, pack-specific hardcodes.

## Root cause (mandatory)
- **Symptom:** the truthful `r42` completion replay stays infra-valid and reaches all 10 dialogs, but dialog `4`, turn `9` still answers with a pricing fact instead of the expected handoff on `Почему я не могу записаться на выходные?`.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r42-004-09-e29405` in `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`; the row shows `decision_meta.action='reply'`, `tool_action='catalog.service_query'`, `booking_prompt_interrupt_recovery='active_time_pricing_interrupt'`, and `turn_outcome.meta.reason_code='booking_interrupt'`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r42/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r42/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r42/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`
  - `truffles-api/app/services/demo_salon_knowledge.py:1200`
  - `truffles-api/app/services/demo_salon_knowledge.py:1239`
  - `truffles-api/app/services/demo_salon_knowledge.py:1580`
  - `truffles-api/app/routers/webhook/info.py:231`
  - `truffles-api/app/routers/webhook/info.py:238`
  - `truffles-api/app/routers/webhook/info.py:332`
  - `truffles-api/app/routers/webhook/info.py:369`
  - `truffles-api/app/services/reasoning_core.py:10477`
  - `truffles-api/app/services/reasoning_core.py:10499`
  - `truffles-api/app/services/reasoning_core.py:10732`
  - `truffles-api/app/services/reasoning_core.py:10843`
  - `truffles-api/app/services/reasoning_core.py:10912`
- **Five Whys:**
  - Why does the locked scenario fail? The live runtime emits a pricing fact reply where the scenario contract expects handoff.
  - Why does runtime emit a pricing fact? The active booking interrupt path selects `pricing` and finalizes a `catalog.service_query` tool reply.
  - Why does it select `pricing` on `Почему я не могу записаться на выходные?`? `_detect_info_class_intents(...)` returns both `hours` and `pricing`, and `reasoning_core.py` prioritizes `pricing` before `hours`.
  - Why does pricing appear at all on that text? `_has_price_signal(...)` returns `True` because `price_keywords` contains `почем`, and `_contains_any(...)` does raw substring matching, so `почем` matches inside `почему`.
  - Why is this a truthful runtime blocker and not replay noise? `r42` is full-completion (`143/143` turns, dialogs `1..10` present, `infra_valid=true`, `run_integrity_valid=true`), and `failure_families.json` isolates the surviving strict failure family to `stage=booking_interrupt` on that row.
- **Root cause statement:** a substring-based price-signal resolver falsely matches `почем` inside `почему`, injects a false `pricing` interrupt into active booking continuity, and the booking-prompt interrupt path then finalizes a pricing tool reply instead of staying on the weekend/handoff route.
- **Fix mechanism:** change price-signal detection from unsafe substring matching to word-boundary-aware matching for keyword tokens, preserve legitimate multi-word price phrases, and add deterministic coverage so the active booking weekend interrupt cannot re-enter `catalog.service_query` through this false-positive path.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing helper `_contains_word(...)` in `truffles-api/app/services/demo_salon_knowledge.py`
  - existing completion artifact `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
  - existing runtime tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - `https://docs.python.org/3.9/howto/regex.html`
- **Why not reinvent the wheel:** the repo already contains whole-word matching and the official Python regex guidance; the work is to route existing signal detection through the correct primitive.

## Invariant
Do not weaken replay/proof gates, do not touch frozen routers, and do not normalize the bad row as acceptable pricing behavior.

## Scope
Truthful runtime-family classification only.

## Out of scope
- implementation changes before the family boundary is locked
- proof/oracle threshold changes
- production-floor repair
- acceptance `lock/full` work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r42/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r42/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`

## Plan (1..N)
1. Confirm that `r42` is a truthful completion replay and not another incomplete artifact.
2. Isolate the first surviving strict failure family from `failure_families.json` and the failing row.
3. Trace the row into the live resolver and booking interrupt owner chain.
4. Lock the next admissible implementation family only if the same runtime path remains the blocker on full-completion evidence.

## DoD
- `r42` completion truth is recorded with exact file evidence
- the first surviving blocker is classified as runtime/model, not proof drift
- the next admissible move is a bounded implementation family with a deterministic first check

## Work mode (mandatory)
`closure`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` already consumed by `r42` in this decision block.
- **Max replay runs:** `0` additional.
- **Stop condition:** if `r42` were incomplete or infra-invalid, stop and classify the new blocker instead of proposing code.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r42 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r42/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r42/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`

## Release safety (mandatory for non-doc changes)
- **Strategy:** no production rollout in this decision block; classify only.
- **Go/no-go signals:** `r42` completed; strict failure family is isolated; no code changes are made in this block.
- **Rollback:** not applicable; docs/evidence only.
- **Post-release monitoring window:** not applicable.

## Rollback
Rollback: not applicable; no implementation changes are made in this block.

## No-go
- no runtime patch before family classification
- no proof/oracle threshold edits
- no frozen-router edits

## Risks/blockers
- current `manual_audit.json` still reports broad `judge_oracle_alignment_gap`, so implementation must stay anchored to the single strict runtime family and not overfit the advisory handoff-miss rows.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt owner defs remain unresolved; replay still logs stale simulation ids in timing context; prod floor remains degraded.
- **Why not in this block:** this block only classifies the first surviving runtime family.
- **Risk if deferred:** the same resolver bug can keep surfacing false info interrupts in other packs and continuity lanes.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-implementation-a922.md`
- **Expiry/trigger to stop deferral:** immediate; the next code block must repair the resolver/runtime family or open a wider shared-signal extraction block.

## Next-block contract (mandatory)
- **Next block objective:** repair the bounded weekend booking-interrupt pricing false positive so `Почему я не могу записаться на выходные?` no longer routes through `catalog.service_query` on active booking continuity.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py -k "weekend or price_signal"`
- **Blocked-by conditions:** if the fix requires frozen-router edits or cannot be isolated to non-frozen signal/resolver/runtime files, stop and reopen the family scope.
- **Owner role for closure:** Brain / Top Architect
