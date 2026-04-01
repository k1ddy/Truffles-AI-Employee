# File Analysis: `truffles-api/tests/test_webhook_booking.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file mixes stale package-surface booking helper tests with a smaller extracted-module check against `booking.py`: `truffles-api/tests/test_webhook_booking.py:3`, `truffles-api/tests/test_webhook_booking.py:4`.

## 2. Why This File Exists
- `FACT`: Most of the file preserves old package-level booking/expected-reply helpers such as `_get_expected_reply_type(...)`, `_set_expected_reply_type(...)`, `_validate_name_slot(...)`, `_match_expected_reply(...)`, `_should_block_expected_reply_by_info(...)`, and `_is_booking_slot_signal(...)`: `truffles-api/tests/test_webhook_booking.py:7`, `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_webhook_booking.py:15`, `truffles-api/tests/test_webhook_booking.py:31`, `truffles-api/tests/test_webhook_booking.py:51`, `truffles-api/tests/test_webhook_booking.py:61`, `truffles-api/tests/test_webhook_booking.py:72`, `truffles-api/tests/test_webhook_booking.py:83`, `truffles-api/tests/test_webhook_booking.py:124`.
- `FACT`: A smaller subset already tests extracted `booking.py` behavior directly through `booking_router._should_defer_booking_confirmation_for_info(...)` and `booking_router._should_defer_booking_flow_for_info_interrupt(...)`: `truffles-api/tests/test_webhook_booking.py:93`, `truffles-api/tests/test_webhook_booking.py:104`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only caller.
- `FACT`: The file targets both the package object and the extracted booking module: `truffles-api/tests/test_webhook_booking.py:3`, `truffles-api/tests/test_webhook_booking.py:4`.

## 4. Control Path Owned By This File
- `FACT`: None; it is repo contract evidence only.
- `INFERENCE`: The file shows that booking-family repo contracts are still split between old package helper expectations and extracted module expectations.

## 5. Data Reads
- `FACT`: The file reads package-level booking helpers that are not listed in the narrowed package export surface: `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_webhook_booking.py:31`, `truffles-api/tests/test_webhook_booking.py:61`, `truffles-api/tests/test_webhook_booking.py:124`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `FACT`: It also reads extracted `booking.py` helpers directly: `truffles-api/tests/test_webhook_booking.py:93`, `truffles-api/tests/test_webhook_booking.py:104`.

## 6. Data Writes And Side Effects
- `FACT`: The file uses pure helper calls and no persistent writes.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No runtime authority.
- `INFERENCE`: Strong repo-contract authority for stale booking helper names on the package object.

## 8. Truth Carriers Touched Here
- `FACT`: The file asserts booking-related continuity carriers like `expected_reply_type` only in local test contexts: `truffles-api/tests/test_webhook_booking.py:9`, `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_webhook_booking.py:15`, `truffles-api/tests/test_webhook_booking.py:19`.

## 9. Violations Against The Target Canon
- `FACT`: The file preserves package-level booking helper expectations even though the narrowed package contract exposes only `router` and `_process_outbox_rows`: `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_webhook_booking.py:31`, `truffles-api/tests/test_webhook_booking.py:61`, `truffles-api/tests/test_webhook_booking.py:124`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `FACT`: The same file already proves the extracted booking module is the cleaner target surface for at least some cases: `truffles-api/tests/test_webhook_booking.py:93`, `truffles-api/tests/test_webhook_booking.py:104`.

## 10. Salvageable Parts
- `FACT`: The direct `booking_router` tests are salvageable: `truffles-api/tests/test_webhook_booking.py:93`, `truffles-api/tests/test_webhook_booking.py:104`.

## 11. Demotion / Removal Candidates
- `FACT`: The package-level booking helper tests are demotion candidates because they pin obsolete package assumptions instead of extracted-module surfaces: `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_webhook_booking.py:31`, `truffles-api/tests/test_webhook_booking.py:61`, `truffles-api/tests/test_webhook_booking.py:124`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The booking family repeats the same split seen in dedup and response: extracted-module tests exist, but stale package-helper tests still preserve older repo contracts.

## 13. Open Questions
- `UNKNOWN`: Whether these package-level booking helper tests are intentionally retained or just stale residue.
