# File Analysis: `truffles-api/tests/test_webhook_dedup.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file mixes two different test contracts: stale package-surface pins through `from app.routers import webhook` and real extracted-module tests through `dedup_module`, `legacy_module`, and `guards_module`: `truffles-api/tests/test_webhook_dedup.py:7`, `truffles-api/tests/test_webhook_dedup.py:8`, `truffles-api/tests/test_webhook_dedup.py:9`, `truffles-api/tests/test_webhook_dedup.py:10`.
- `INFERENCE`: It is a precise repo-backed example of the package-surface split drifting out of sync with extracted webhook modules.

## 2. Why This File Exists
- `FACT`: Part of the file was written to preserve old package-level dedup helpers like `_buffer_user_message(...)`, `_drain_buffered_messages(...)`, and `is_duplicate_message_id(...)`: `truffles-api/tests/test_webhook_dedup.py:56`, `truffles-api/tests/test_webhook_dedup.py:81`, `truffles-api/tests/test_webhook_dedup.py:111`.
- `FACT`: Another part already targets the extracted modules directly, such as `dedup_module._handle_dedup_gate(...)`, `dedup_module._lookup_preexisting_duplicate_message(...)`, and `guards_module._handle_post_debounce_muted_state_gate(...)`: `truffles-api/tests/test_webhook_dedup.py:193`, `truffles-api/tests/test_webhook_dedup.py:227`, `truffles-api/tests/test_webhook_dedup.py:265`.
- `INFERENCE`: The file exists because the dedup family was only partially migrated at the repo-contract level.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only caller.
- `FACT`: The file targets `app.routers.webhook` package surface plus extracted `dedup.py` and `guards.py` modules: `truffles-api/tests/test_webhook_dedup.py:7`, `truffles-api/tests/test_webhook_dedup.py:9`, `truffles-api/tests/test_webhook_dedup.py:10`.

## 4. Control Path Owned By This File
- `FACT`: The file owns no product control path; it pins repo contracts around the dedup family.
- `INFERENCE`: The important split is that some tests already follow the extracted modules while others still assume the package exposes old helper names.

## 5. Data Reads
- `FACT`: The file reads package-level webhook helpers and extracted dedup/guard helpers: `truffles-api/tests/test_webhook_dedup.py:7`, `truffles-api/tests/test_webhook_dedup.py:9`, `truffles-api/tests/test_webhook_dedup.py:10`, `truffles-api/tests/test_webhook_dedup.py:56`, `truffles-api/tests/test_webhook_dedup.py:193`, `truffles-api/tests/test_webhook_dedup.py:265`.
- `FACT`: The narrowed package surface does not list those dedup helpers in `__all__`; it exports only `router` and `_process_outbox_rows`: `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:4`, `truffles-api/app/routers/webhook/__init__.py:6`.

## 6. Data Writes And Side Effects
- `FACT`: The file monkeypatches `dedup_module` and `legacy_module` helpers to exercise fallback behavior: `truffles-api/tests/test_webhook_dedup.py:121`, `truffles-api/tests/test_webhook_dedup.py:189`, `truffles-api/tests/test_webhook_dedup.py:248`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file itself has no runtime authority.
- `INFERENCE`: It has repo-contract authority because it keeps old package-helper names socially alive even though the extracted modules already provide the real implementations.

## 8. Truth Carriers Touched Here
- `FACT`: The file inspects dedup diagnostics and muted-state trace payloads only as test artifacts: `truffles-api/tests/test_webhook_dedup.py:118`, `truffles-api/tests/test_webhook_dedup.py:146`, `truffles-api/tests/test_webhook_dedup.py:208`, `truffles-api/tests/test_webhook_dedup.py:277`.

## 9. Violations Against The Target Canon
- `FACT`: The package contract and the test contract diverge: the package exports only `router` and `_process_outbox_rows`, while this file still expects package-level `_buffer_user_message(...)`, `_drain_buffered_messages(...)`, and `is_duplicate_message_id(...)`: `truffles-api/app/routers/webhook/__init__.py:6`, `truffles-api/tests/test_webhook_dedup.py:56`, `truffles-api/tests/test_webhook_dedup.py:81`, `truffles-api/tests/test_webhook_dedup.py:111`.
- `FACT`: The same file already proves the extracted-module path exists by directly testing `dedup_module` and `guards_module`: `truffles-api/tests/test_webhook_dedup.py:193`, `truffles-api/tests/test_webhook_dedup.py:227`, `truffles-api/tests/test_webhook_dedup.py:265`.
- `INFERENCE`: This is pure repo-contract drift, not missing extraction work inside the runtime package export.

## 10. Salvageable Parts
- `FACT`: The direct `dedup_module` and `guards_module` tests are salvageable because they target the extracted modules explicitly: `truffles-api/tests/test_webhook_dedup.py:193`, `truffles-api/tests/test_webhook_dedup.py:227`, `truffles-api/tests/test_webhook_dedup.py:265`.

## 11. Demotion / Removal Candidates
- `FACT`: The package-level helper tests are demotion/removal candidates because they pin an obsolete package surface instead of the extracted modules: `truffles-api/tests/test_webhook_dedup.py:56`, `truffles-api/tests/test_webhook_dedup.py:81`, `truffles-api/tests/test_webhook_dedup.py:111`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The dedup family is split at repo-contract level: extracted modules exist and are already tested directly, but stale package-surface tests still preserve old assumptions.
- `INFERENCE`: Future deletion or narrowing work must account for repo test drift, not just runtime callers.

## 13. Open Questions
- `UNKNOWN`: Whether the stale package-surface tests in this file are intentionally excluded from active deterministic suites or simply stale debt.
