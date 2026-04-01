# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r36g`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `Consult/media cue continuity is improved on the practical path and no longer surfaces at dialog 7 turn 1; the remaining live blocker is booking-manage temporal clue grounding and follow-up continuity on dialog 9 turns 1-2, while dialog 2 retains secondary oracle/evaluator residue.`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r36g`

## Scope
Fresh current-head replay plus full human semantic audit after the bounded consult/media follow-up contract fix.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`, `manual_audit_status=done`, `product_quality_valid=false`
- comparison verdict: `comparison_blocked=true` because baseline `r35f` is itself `semantic_invalid`
- family verdict:
  - practical improvement proven: `consult/media cue continuity` no longer surfaces on the visible path
  - remaining live blocker: `booking-manage temporal clue grounding / follow-up continuity`
  - secondary residues: `oracle contract / taxonomy alignment`, `replay harness / evaluator isolation`
- conclusion:
  - the root-first implementation sequence remains materially complete repo-side on the touched canary envelope
  - the bounded consult/media fix is now proven improved on the practical path
  - the current-head practical truth is now `r36g`
  - no product/practical closure claim is admissible because the booking-manage family remains red

## Replay And Audit Commands
- replay:
  - `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r36g --allow-pending-previous --allow-repeat-fingerprint -- --base-url http://127.0.0.1:18187 --client-slug demo_salon --quality-lane dev --count 10 --scenarios-file /tmp/booking_quality/a922-practical-proof-20260330-r35f/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --skip-outbox --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text "ок" --tool-hooks auto --tool-confirm-text "да" --tool-cancel-text "отмена" --tool-calendar-text "проверь запись" --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --baseline-summary /tmp/booking_quality/a922-practical-proof-20260330-r35f/summary.json --history-max 20 --fail-on-thresholds --fail-on-regression --max-failures 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- audit:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r36g --status done --strict-artifacts --human-semantic-valid false --human-semantic-summary 'Consult/media cue continuity is improved on the practical path and no longer surfaces at dialog 7 turn 1; the remaining live blocker is booking-manage temporal clue grounding and follow-up continuity on dialog 9 turns 1-2, with dialog 2 turn 5 left as oracle/taxonomy residue.' --oracle-judge-alignment conflicted --oracle-winner mixed ...`
- trend:
  - `python3 ops/diagnose.py llm-quality-trends --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r36c --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r36g --output /tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.json --markdown-output /tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.md --pretty`

## Run Hygiene Notes
- `r36d` and `r36e` are retained as audited invalid-preflight artifacts only.
- They were created while switching from the old direct replay entrypoint to the current guarded replay entrypoint and while clearing the manual-audit gate.
- They are not admissible behavioral evidence and they do not change current practical truth.

## Surfaced Turns
| Dialog | Turn | User | Bot | Human verdict | Mechanism |
|---|---:|---|---|---|---|
| 9 | 1 | `Проверьте мою запись на четверг.` | `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.` | `fail` | `booking-manage temporal clue grounding / follow-up continuity` |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.` | `fail` | `booking-manage temporal clue grounding / follow-up continuity` |
| 2 | 4 | `Завтра в 15:00` | `Передаю диалог менеджеру, чтобы не потерять ваш запрос.` | `weak` | `oracle contract / taxonomy alignment` |
| 2 | 5 | `Алина` | `Маникюр классический — 2 500 ₸, аппаратный — 3 500 ₸, маникюр + гель-лак — 7 000 ₸.` | `weak/advisory` | `replay harness / evaluator isolation` |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | `Пришлите, пожалуйста, фото-пример желаемого результата.` | `pass` | `consult/media cue continuity` |

## Dialog Verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Visible price answer remains acceptable. |
| 2 | Booking with info interrupts and completion | `weak` | The practical blocker moved away from consult/media, but booking continuity still shows secondary oracle/evaluator residue around turns 4-5. |
| 3 | Explicit human handoff | `pass` | Transparent handoff remains correct. |
| 4 | Hours fact | `pass` | Hours answer remains acceptable on the visible path. |
| 5 | Location fact | `pass` | Governed first-family location answer remains acceptable. |
| 6 | Parking fact | `pass` | Governed first-family parking answer remains acceptable. |
| 7 | Media prompt | `pass` | The consult/media fix is visible on the practical path. |
| 8 | Second booking entry | `pass` | Booking entry remains acceptable. |
| 9 | Check and confirm sequence | `fail` | Temporal clue grounding/follow-up continuity remains visibly wrong. |
| 10 | Third booking entry | `pass` | Booking entry remains acceptable. |

## Family-Level Verdicts

### A. Practical improvement proven: consult/media cue continuity
- surfaced in `r36c`, no longer surfaced in `r36g`
- evidence:
  - `dialog 7 / turn 1` now returns `Пришлите, пожалуйста, фото-пример желаемого результата.`
  - trend artifact removes the product bucket family from the current run
- interpretation:
  - the bounded consult/media fix improved the practical path
  - this mechanism is no longer the first live blocker on current head

### B. Remaining live blocker: booking-manage temporal clue grounding / follow-up continuity
- surfaced in:
  - `dialog 9 / turn 1`
  - `dialog 9 / turn 2`
- symptom:
  - the user already grounds the temporal clue (`на четверг`), but the visible reply keeps asking generically for `дату и время или имя`
- required next move:
  - freeze exact owner -> binding -> fact-composition -> final-response path before any runtime code

### C. Secondary oracle residue: oracle contract / taxonomy alignment
- surfaced in:
  - `dialog 2 / turn 4`
- symptom:
  - the booking continuity path degrades to handoff where the scenario/oracle expected a narrower follow-up
- status:
  - secondary; not the first implementation unit after `r36g`

### D. Secondary evaluator residue: replay harness / evaluator isolation
- surfaced in:
  - `dialog 2 / turn 5`
  - `judge_conflicts.jsonl` count `2`
- status:
  - advisory until the runtime blocker above is isolated cleanly

## Trend Result (`r36c` -> `r36g`)
- artifact:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.md`
- truth:
  - `consult/media cue continuity` appears only in `r36c`, not in `r36g`
  - `booking-manage temporal clue grounding / follow-up continuity` remains in both runs
  - `oracle contract / taxonomy alignment` remains as secondary residue

## Current Truth
1. Root-first implementation sequence `1..10` remains materially complete repo-side on the touched canary envelope.
2. Fresh current-head practical truth is `r36g`, not `r36c`.
3. The bounded consult/media fix is now proven improved on the practical path.
4. `r36g` is still red on both contract and human-semantic lanes because the booking-manage continuity family remains live.
5. The next admissible runtime-facing work is mechanism-first RCA for `booking-manage temporal clue grounding / follow-up continuity`.

## Next Actions
1. Sync canon/docs to `r36g`.
2. Open the next RCA-only Task Package for `booking-manage temporal clue grounding / follow-up continuity`.
3. Keep `oracle contract / taxonomy alignment` and evaluator residue separate from the next implementation unit.
