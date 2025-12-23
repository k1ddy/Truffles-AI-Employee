# Demo salon pack (v2)

Это набор канонических артефактов для demo_салон «Мира»:
- POLICY.md — запреты/эскалация/тон
- SALON_TRUTH.yaml — структурная “истина” (из demo_salon/*.md)
- INTENTS_PHRASES_DEMO_SALON.yaml — фразы/вариации для быстрых матчей
- EVAL.yaml — тест-кейсы (reply vs escalate + must_not)
- SYSTEM_PROMPT_DEMO_SALON.md — системный промпт для генерации
- CODEX_TASK_DEMO_SALON.md — ТЗ для Codex

Примечание: EVAL синтетический (реальных диалогов пока нет), но покрывает основные риски и рутину.


## Repo paths (your setup)
- Qdrant sync source for demo salon: `ops/demo_salon_docs/` (used by `ops/sync_all_clients.py` and `ops/manual_sync_demo.py`).
- Default sync looks for `knowledge/<client_slug>` in `ops/sync_client.py`, but that folder doesn't exist in the repo right now.

## Note on contacts
The salon FAQ in the repo does not include an admin phone number, so `SALON_TRUTH.yaml` intentionally does not contain one.
