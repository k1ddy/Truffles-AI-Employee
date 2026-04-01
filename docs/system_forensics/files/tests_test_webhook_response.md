# File Analysis: `truffles-api/tests/test_webhook_response.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file mixes stale package-surface response helper tests with direct tests of extracted `response.py` logic and `_legacy` helper behavior: `truffles-api/tests/test_webhook_response.py:4`, `truffles-api/tests/test_webhook_response.py:5`, `truffles-api/tests/test_webhook_response.py:6`.

## 2. Why This File Exists
- `FACT`: It preserves old package-level response helper expectations like `_maybe_append_booking_cta(...)`, `_apply_quiet_hours_notice(...)`, and `ConversationState` access through `app.routers.webhook`: `truffles-api/tests/test_webhook_response.py:12`, `truffles-api/tests/test_webhook_response.py:13`, `truffles-api/tests/test_webhook_response.py:23`, `truffles-api/tests/test_webhook_response.py:24`, `truffles-api/tests/test_webhook_response.py:34`, `truffles-api/tests/test_webhook_response.py:35`, `truffles-api/tests/test_webhook_response.py:54`, `truffles-api/tests/test_webhook_response.py:88`.
- `FACT`: It also directly covers extracted `response.py` behavior via `_finalize_bot_response(...)` and `_should_route_explicit_info_to_main_flow(...)`: `truffles-api/tests/test_webhook_response.py:6`, `truffles-api/tests/test_webhook_response.py:57`, `truffles-api/tests/test_webhook_response.py:91`, `truffles-api/tests/test_webhook_response.py:121`.
- `FACT`: The file additionally keeps one `_legacy` lexical helper test alive: `truffles-api/tests/test_webhook_response.py:113`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only caller.
- `FACT`: The file targets three surfaces at once: package `app.routers.webhook`, extracted `response.py`, and `_legacy`: `truffles-api/tests/test_webhook_response.py:4`, `truffles-api/tests/test_webhook_response.py:5`, `truffles-api/tests/test_webhook_response.py:6`.

## 4. Control Path Owned By This File
- `FACT`: None; it is a repo contract pin file.
- `INFERENCE`: The file shows response-family contract drift similar to the dedup family: extracted response helpers exist, but old package helper assumptions remain beside them.

## 5. Data Reads
- `FACT`: The file reads package-level helper names not exported by the narrowed package surface, which declares only `router` and `_process_outbox_rows`: `truffles-api/tests/test_webhook_response.py:13`, `truffles-api/tests/test_webhook_response.py:35`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `FACT`: It also reads extracted `response.py` helpers directly: `truffles-api/tests/test_webhook_response.py:6`, `truffles-api/tests/test_webhook_response.py:57`, `truffles-api/tests/test_webhook_response.py:121`.

## 6. Data Writes And Side Effects
- `FACT`: The file uses only in-memory objects and pure helper calls; no persistent side effects are asserted.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No runtime authority.
- `INFERENCE`: Strong repo-contract authority over stale response helper names on the package object.

## 8. Truth Carriers Touched Here
- `FACT`: Only test-local conversation/context carriers for `_finalize_bot_response(...)`: `truffles-api/tests/test_webhook_response.py:54`, `truffles-api/tests/test_webhook_response.py:88`.

## 9. Violations Against The Target Canon
- `FACT`: The file still expects package-level response helpers that are no longer part of the narrowed package contract: `truffles-api/tests/test_webhook_response.py:13`, `truffles-api/tests/test_webhook_response.py:24`, `truffles-api/tests/test_webhook_response.py:35`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `FACT`: The same file already uses extracted `response.py` directly for some cases, proving the more accurate target surface exists: `truffles-api/tests/test_webhook_response.py:6`, `truffles-api/tests/test_webhook_response.py:121`.

## 10. Salvageable Parts
- `FACT`: Direct tests of extracted `response.py` helpers are salvageable: `truffles-api/tests/test_webhook_response.py:57`, `truffles-api/tests/test_webhook_response.py:91`, `truffles-api/tests/test_webhook_response.py:121`.

## 11. Demotion / Removal Candidates
- `FACT`: Package-level helper tests for `_maybe_append_booking_cta(...)` and `_apply_quiet_hours_notice(...)` are demotion candidates because they preserve obsolete package expectations: `truffles-api/tests/test_webhook_response.py:13`, `truffles-api/tests/test_webhook_response.py:24`, `truffles-api/tests/test_webhook_response.py:35`, `truffles-api/tests/test_webhook_response.py:44`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The response family has the same repo-contract split pattern as dedup: direct extracted-module coverage already exists, but stale package-surface tests remain beside it.

## 13. Open Questions
- `UNKNOWN`: Whether these stale package-level response helper tests are still supposed to run in active deterministic suites.
