# TP-2026-03-23 Consultant Core Demo Salon Seed19 R42 Weekend Booking Interrupt Pricing False Positive Runtime Implementation A922

## Title/goal
Repair the bounded runtime family where active booking continuity misroutes `Почему я не могу записаться на выходные?` into a pricing `catalog.service_query` reply because the price-signal resolver falsely matches `почем` inside `почему`.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-decision-a922.md`
- CA_ID `a922-go2f-seed19-r42-weekend-booking-interrupt-pricing-false-positive-family`

## One web search (mandatory before implementation)
- **Query (exact):** `Python re word boundary whole word match official documentation`
- **Date/time (local):** `2026-03-23 18:18 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3.9/howto/regex.html`
- **Found ready-made solutions:** Python's official regex HOWTO documents `\b` as a word-boundary assertion for matching complete words instead of substrings inside larger words.
- **Decision:** `reuse` the existing repo helper `_contains_word(...)` and build a bounded resolver/runtime fix.
- **Why:** the surfaced blocker is a local resolver bug, not a missing third-party capability.
- **Rejected options:** deleting replay gates, changing scenario expectations, frozen-router edits, pack-only hardcodes.

## Root cause (mandatory)
- **Symptom:** full-completion replay `r42` keeps one strict surviving failure family on dialog `4`, turn `9`, where a weekend reschedule message returns `Дизайн ногтей — от 300 ₸.` instead of handoff.
- **Minimal reproduction:** `LLM-QUAL-a922-go2f-seed19-r42-004-09-e29405` in `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`
  - `truffles-api/app/services/demo_salon_knowledge.py:1200`
  - `truffles-api/app/services/demo_salon_knowledge.py:1239`
  - `truffles-api/app/services/demo_salon_knowledge.py:1580`
  - `truffles-api/app/routers/webhook/info.py:238`
  - `truffles-api/app/routers/webhook/info.py:332`
  - `truffles-api/app/services/reasoning_core.py:10499`
  - `truffles-api/app/services/reasoning_core.py:10732`
- **Five Whys:**
  - Why does the strict row fail? The bot replies with a pricing fact instead of handoff.
  - Why does it reply with pricing? The active booking interrupt path selects `pricing` and finalizes `catalog.service_query`.
  - Why is `pricing` selected? `_detect_info_class_intents(...)` marks the text as `pricing` and `hours`, and runtime prioritizes `pricing`.
  - Why is `pricing` marked on that text? `_has_price_signal(...)` returns true because substring matching makes `почем` match inside `почему`.
  - Why is this the next admissible family? `r42` completed truthfully and no earlier proof/tooling blocker replaced this row.
- **Root cause statement:** unsafe substring matching in the shared price-signal resolver creates a false `pricing` interrupt on `почему`, which sends active booking continuity into a pricing tool reply path.
- **Fix mechanism:** replace unsafe substring price-keyword matching with whole-word-aware matching for single-token lexemes while preserving valid multi-word price phrases, then prove the runtime no longer routes the weekend reschedule message through `catalog.service_query`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_contains_word(...)` in `truffles-api/app/services/demo_salon_knowledge.py`
  - existing info-interrupt contract tests in `truffles-api/tests/test_booking_info_interrupt_contract.py`
  - existing booking prompt owner tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - `https://docs.python.org/3.9/howto/regex.html`
- **Why not reinvent the wheel:** the repo already has a safe word-boundary primitive; the work is to route price-signal matching through it and add contract coverage.

## Invariant
Do not weaken replay/proof gates, do not touch frozen routers, and do not normalize the failing weekend reschedule row as acceptable pricing behavior.

## Scope
- bounded non-frozen resolver/runtime repair for the surfaced weekend booking interrupt pricing false positive
- deterministic regression coverage for the surfaced family

## Out of scope
- proof/oracle threshold changes
- production-floor repair
- duplicate-def cleanup beyond what is necessary to keep this path executable
- acceptance `lock/full`

## Touch-list
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-implementation-a922.md`

## Plan (1..N)
1. Replace unsafe substring price-keyword matching with whole-word-aware matching for single-token price keywords while preserving legitimate multi-word phrases.
2. Mirror the same bounded fix in the shared neutral adapter so pack-neutral runtime does not keep the same false positive.
3. Add deterministic signal-level coverage proving `почему я не могу записаться на выходные?` is not a pricing query.
4. Add a targeted reasoning-core regression proving active booking continuity on that text no longer routes through the pricing service-query interrupt.
5. Run focused deterministic suites; if green, publish the implementation report and queue the next fresh replay closure block.

## DoD
- no surfaced path classifies `Почему я не могу записаться на выходные?` as a pricing query
- active booking continuity no longer emits `catalog.service_query` on the surfaced row contract
- focused deterministic suites are green
- next move is a fresh replay closure, not another runtime patch by default

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this implementation block.
- **Max replay runs:** `0` here; closure replay is the next block after deterministic proof.
- **Stop condition:** if the fix cannot be isolated to non-frozen resolver/runtime files, stop and reopen scope before editing more code.

## Checks
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py -k "weekend or price_signal"`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pricing_interrupt or weekend_booking_followup or direct_service_query_fact_defers_active_booking_interrupt"`

## Evidence
- code diff for touched non-frozen files
- pytest output for the focused suites above
- updated report artifact for this implementation block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime behavior repair; no production rollout in this block.
- **Go/no-go signals:** focused deterministic suites are green and no frozen file is touched.
- **Rollback:** revert only this bounded resolver/runtime diff.
- **Post-release monitoring window:** not applicable; no production release.

## Rollback
- revert the bounded resolver/runtime patch if the focused suites regress or if the path still emits the pricing interrupt for the surfaced row.

## No-go
- no frozen-router edits
- no proof/oracle gate relaxation
- no pack-specific hardcoded exception for `почему`
- no widening into unrelated prod-floor repairs inside this block

## Risks/blockers
- `truffles-api/app/services/reasoning_core.py` still carries duplicate booking-prompt owner defs, so the implementation must avoid touching unreachable earlier copies unless execution evidence forces a duplicate-cleanup follow-up.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt owner defs remain; stale simulation-id contamination remains in replay control-plane; prod outbox/embedding floor remains degraded.
- **Why not in this block:** this block repairs one surfaced runtime family only.
- **Risk if deferred:** other lanes can still suffer from duplicate-authority confusion or replay noise even after this family is repaired.
- **Linked follow-up Task Package(s):** fresh closure replay for this family; later control-plane and authority-reduction streams.
- **Expiry/trigger to stop deferral:** immediate after this family is repaired; if the executable path still cannot be isolated, open duplicate-cleanup as the next block.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh replay closure on the locked scenarios to prove the weekend booking-interrupt pricing false positive is no longer the first blocker.
- **First deterministic check command:** `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --allowlist-jids 77015705555@s.whatsapp.net,77785890765@s.whatsapp.net,77000000001@s.whatsapp.net,77000000002@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text ок --tool-hooks auto --tool-confirm-text да --tool-cancel-text отмена --tool-calendar-text проверь запись --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r43 --run-id a922-go2f-seed19-r43 --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --history-max 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --max-failures 1`
- **Blocked-by conditions:** fresh local runtime parity must be preserved; if deterministic tests fail, do not run replay.
- **Owner role for closure:** Brain / Top Architect
