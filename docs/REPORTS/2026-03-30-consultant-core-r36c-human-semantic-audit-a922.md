# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r36c`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r36c is human-semantic red because dialog 7 turn 1 drops the explicit photo/media consult cue into generic service collection, while dialog 9 turns 1-2 still miss the visible booking-manage follow-up contract.`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r36c`

## Scope
Full current-head human semantic audit after the root-first canary implementation sequence and final legacy-drain proof closure.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`, `manual_audit_status=done`, `product_quality_valid=false`
- comparison verdict: `comparison_blocked=true` because baseline `r35f` is itself `semantic_invalid`
- family verdict:
  - open product blocker: `consult/media cue continuity`
  - open visible follow-up blocker: `booking-manage temporal clue grounding / follow-up continuity`
  - secondary residue: `oracle contract / taxonomy alignment`
- conclusion:
  - the root-first implementation sequence is still materially complete repo-side on the touched canary envelope
  - the current-head practical truth is now `r36c`
  - no product/practical closure claim is admissible

## Replay And Audit Commands
- replay:
  - `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18187 --client-slug demo_salon --count 10 --scenarios-file /tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --skip-outbox --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-practical-proof-20260330-r36c --run-id a922-practical-proof-20260330-r36c --baseline-summary /tmp/booking_quality/a922-practical-proof-20260330-r35f/summary.json --history-max 20 --fail-on-thresholds --fail-on-regression --max-failures 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r36c --status done --strict-artifacts`

## Surfaced Turns
| Dialog | Turn | User | Bot | Human verdict | Mechanism |
|---|---:|---|---|---|---|
| 7 | 1 | `Я могу прислать фото своих ногтей.` | `На какую услугу хотите записаться?` | `fail` | `consult/media cue continuity` |
| 9 | 1 | `Проверьте мою запись на четверг.` | `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.` | `fail` | `booking-manage temporal clue grounding / follow-up continuity` |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.` | `fail` | `booking-manage temporal clue grounding / follow-up continuity` |
| 2 | 5 | `Алина` | `Готово, записал вас на маникюр на 31.03 15:00.` | `weak` | `oracle contract / taxonomy alignment` |

## Dialog Verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Visible price answer is acceptable. |
| 2 | Booking with info interrupts and completion | `weak` | Visible booking result is usable; tooling/judge taxonomy still disagrees on the completion turn. |
| 3 | Explicit human handoff | `pass` | Transparent handoff remains correct. |
| 4 | Hours fact | `pass` | Hours answer remains acceptable on the visible path. |
| 5 | Location fact | `pass` | Governed first-family location answer remains acceptable. |
| 6 | Parking fact | `pass` | Governed first-family parking answer remains acceptable. |
| 7 | Media prompt | `fail` | The explicit photo/media cue is dropped. |
| 8 | Second booking entry | `pass` | Booking entry remains acceptable. |
| 9 | Check and confirm sequence | `fail` | Temporal clue grounding/follow-up continuity remains visibly wrong. |
| 10 | Third booking entry | `pass` | Booking entry remains acceptable. |

## Family-Level Verdicts

### A. Open product blocker: consult/media cue continuity
- surfaced in:
  - `dialog 7 / turn 1`
- symptom:
  - the user explicitly offers a photo/reference for consult, but the visible reply collapses to generic service collection
- current evidence:
  - the trace still shows `reason=user_offers_photos_for_style_reference`, `capability=consultation`, `pack_refs=["style_reference"]`
  - final visible response still asks only for service
- required next move:
  - exact owner -> binding -> executor -> final-response RCA before any code

### B. Open visible blocker: booking-manage temporal clue grounding / follow-up continuity
- surfaced in:
  - `dialog 9 / turn 1`
  - `dialog 9 / turn 2`
- symptom:
  - the visible reply still asks again for approximate date/time even though the temporal clue is already present in the user turn
- note:
  - keep this as a separate mechanism after the media block; do not blend it into one local dialog patch

### C. Secondary oracle residue: oracle contract / taxonomy alignment
- surfaced in:
  - `dialog 2 / turn 5`
- symptom:
  - the visible booking confirmation is acceptable, but oracle/judge expectations remain stricter than the live contract for this turn
- status:
  - secondary

### D. Evaluator residue: judge conflict
- surfaced in:
  - `judge_conflicts.jsonl` count `1`
- status:
  - advisory until rubric refinement; not the next implementation unit

## Current Truth
1. Root-first implementation sequence `1..10` remains materially complete repo-side on the touched canary envelope.
2. Fresh current-head practical truth is `r36c`, not `r35f`.
3. `r36c` is red on both contract and human-semantic lanes.
4. The next admissible runtime-facing work is not a local bugfix; it is mechanism-first RCA on `consult/media cue continuity`.

## Next Actions
1. Sync canon/docs to `r36c`.
2. Open the next RCA-only Task Package for `consult/media cue continuity`.
3. Keep `booking-manage temporal clue grounding / follow-up continuity` queued as the next RCA block after media.
