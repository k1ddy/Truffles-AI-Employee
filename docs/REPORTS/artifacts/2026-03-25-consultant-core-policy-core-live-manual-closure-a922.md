# Consultant Core Policy Core Live Manual Closure A922

## Result
- Manual product closure is green on the live runtime rebuilt from the current worktree.
- The closure proof is local-first and allowlist-safe: outbound transport stayed blocked by `transport_send_mode=allowlist`, while runtime state, traces, and DB side effects were verified directly.

## Scope
- verify post-rebuild runtime health after `c2b065af`
- exercise the exact product dialogs required by the recovery plan
- confirm outcome contracts on the live runtime instead of legacy wrappers

## Checks
- `curl -fsS http://localhost:8000/admin/health` -> `200`
- targeted live dialogs via `POST /webhook/demo_salon` on fresh JIDs
- direct inspection of runtime logs and persisted handoff/appointment side effects

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | Runtime health is green on the current worktree lane: `eval_mode=livecheck`, `transport_send_mode=allowlist`, `outbox_worker_mode=off`, `danger_flags=[]`. | `curl -fsS http://localhost:8000/admin/health` on 2026-03-25 |
| FACT | `ask_about_requested_slot` is now schema-valid, so pending booking reentry stays on the canonical collect contract instead of degrading. | `truffles-api/app/schemas/intent.py`, `truffles-api/tests/test_intent.py` |
| FACT | Mid-booking factual interrupts now route through the real tool surface (`catalog.service_query`) and preserve booking continuity instead of bypassing the tool registry. | `truffles-api/app/core/turn_executor.py`, `truffles-api/tests/test_consultant_core_runtime_contracts.py` |
| FACT | Generic promo queries are now grounded through the demo salon pack instead of falling through a missing-signal hole. | `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`, `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/tests/test_booking_appointments.py` |
| FACT | Policy-core timeout fallback is now a real fast fallback path: GPT-5 fallback uses `temperature=1.0`, `reasoning_effort=minimal`, and `max_completion_tokens>=400`, instead of retrying the same failing primary path. | `truffles-api/app/services/intent_service.py`, `truffles-api/app/services/llm/base.py`, `truffles-api/app/services/llm/openai_provider.py`, `truffles-api/tests/test_intent.py` |
| FACT | Manual dialog `Сколько стоит маникюр?` returned a grounded FACT reply with manicure pricing on the live runtime. | local live dialog evidence from 2026-03-25 on JID `77099000601@s.whatsapp.net` |
| FACT | Manual dialog `Хочу записаться на маникюр` followed by `На какое время лучше записаться?` stayed on the booking collect path and did not hand off. | local live dialog evidence from 2026-03-25 on JID `77099000601@s.whatsapp.net` |
| FACT | Manual dialog family `Хочу записаться на маникюр -> Есть ли акции? -> Какая цена? -> Завтра в 15:00 -> Айгерим` produced the expected sequence `COLLECT -> FACT -> FACT -> COLLECT(name) -> booking_confirm`, and the appointment row was created. | local live dialog evidence from 2026-03-25 on JID `77099000602@s.whatsapp.net`, `truffles-api` logs (`Created appointment`) |
| FACT | Manual dialog `Хочу поговорить с человеком` produced `HANDOFF` and created a pending handoff row/topic on the live runtime. | local live dialog evidence from 2026-03-25 on JID `77099000603@s.whatsapp.net`, `truffles-api` logs (`Created topic 14383`) |
| INFERENCE | The live default owner path now holds the required product contracts for the critical booking/info/handoff flows without relying on the deleted legacy semantic substrate. | combined manual dialog results plus the Phase B/C structural changes already landed in the worktree |
| UNKNOWN | Acceptance/quality closure on the guarded replay lane is still open until a fresh acceptance artifact is produced from the current runtime fingerprint. | no Phase E artifact exists yet |

## Exact manual dialogs
1. `Сколько стоит маникюр?` -> FACT with manicure pricing
2. `Хочу записаться на маникюр` -> collect prompt for date/time
3. `На какое время лучше записаться?` -> stays on collect prompt for date/time
4. `Есть ли акции?` (mid-booking) -> FACT, no handoff
5. `Какая цена?` (mid-booking) -> FACT, no handoff
6. `Завтра в 15:00` -> collect prompt for name
7. `Айгерим` -> booking confirmation; appointment created
8. `Хочу поговорить с человеком` -> HANDOFF; pending handoff created

## Closure decision
- Phase D manual product closure is accepted locally.
- The next honest move is Phase E only: run the guarded acceptance replay/full workflow from the same runtime fingerprint and publish the artifact.

## Evidence
- `c2b065af`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/llm/base.py`
- `truffles-api/app/services/llm/openai_provider.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_booking_appointments.py`
