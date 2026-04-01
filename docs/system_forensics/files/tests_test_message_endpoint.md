# File Analysis: `truffles-api/tests/test_message_endpoint.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This is a 5686-line mixed contract warehouse that imports the mounted app, the root-level legacy webhook wrapper, `_legacy`, and multiple modular webhook files in one place: `truffles-api/tests/test_message_endpoint.py:15`, `truffles-api/tests/test_message_endpoint.py:23`, `truffles-api/tests/test_message_endpoint.py:26`, `truffles-api/tests/test_message_endpoint.py:27`, `truffles-api/tests/test_message_endpoint.py:28`, `truffles-api/tests/test_message_endpoint.py:29`, `truffles-api/tests/test_message_endpoint.py:37`, `truffles-api/tests/test_message_endpoint.py:40`.
- `INFERENCE`: The file is not one test family; it mixes active ingress contract tests with frozen helper-contract pins for `_legacy` and the root-level legacy wrapper.

## 2. Why This File Exists
- `FACT`: Part of the file tests the active mounted app surface through `TestClient(app)` and `/message` or `/webhook` requests: `truffles-api/tests/test_message_endpoint.py:23`, `truffles-api/tests/test_message_endpoint.py:94`, `truffles-api/tests/test_message_endpoint.py:485`, `truffles-api/tests/test_message_endpoint.py:669`, `truffles-api/tests/test_message_endpoint.py:728`.
- `FACT`: Another part explicitly preserves the legacy root-level wrapper contract via `legacy_webhook_module.handle_webhook(...)`: `truffles-api/tests/test_message_endpoint.py:15`, `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/tests/test_message_endpoint.py:747`, `truffles-api/tests/test_message_endpoint.py:750`.
- `FACT`: The file also pins `_legacy` export forwarding to `handover_owner_service` symbols: `truffles-api/tests/test_message_endpoint.py:5191`.
- `INFERENCE`: The file exists as a combined active-API test and compatibility-preservation warehouse.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only visible caller; this file is a repo contract artifact, not runtime code.
- `FACT`: The active mounted route contract covered here goes through `app.main.app` and patched `app.core.consultant_runtime.handle_webhook_payload`: `truffles-api/tests/test_message_endpoint.py:23`, `truffles-api/tests/test_message_endpoint.py:485`, `truffles-api/tests/test_message_endpoint.py:502`, `truffles-api/tests/test_message_endpoint.py:547`, `truffles-api/tests/test_message_endpoint.py:582`.
- `FACT`: The direct modular HTTP wrapper contract is also tested through `http_router.handle_webhook_direct(...)` and `handle_public_webhook_payload(...)`: `truffles-api/tests/test_message_endpoint.py:766`, `truffles-api/tests/test_message_endpoint.py:792`, `truffles-api/tests/test_message_endpoint.py:801`, `truffles-api/tests/test_message_endpoint.py:804`.

## 4. Control Path Owned By This File
- `FACT`: The file owns no product control path, but it pins three repo contracts at once: the mounted `/message` path, the modular `/webhook/direct` path, and the legacy `app.webhook.handle_webhook(...)` wrapper path: `truffles-api/tests/test_message_endpoint.py:485`, `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/tests/test_message_endpoint.py:766`.
- `INFERENCE`: Because those contracts live in one file, active and legacy surfaces remain mentally coupled even after route cutover.

## 5. Data Reads
- `FACT`: The file reads active app/router modules, `_legacy` helper surfaces, and multiple webhook submodules: `truffles-api/tests/test_message_endpoint.py:15`, `truffles-api/tests/test_message_endpoint.py:23`, `truffles-api/tests/test_message_endpoint.py:26`, `truffles-api/tests/test_message_endpoint.py:41`.
- `FACT`: It also reads continuity/state helper surfaces such as `_get_expected_reply_type(...)` and `_set_expected_reply_type(...)` from `context_manager.py`: `truffles-api/tests/test_message_endpoint.py:30`, `truffles-api/tests/test_message_endpoint.py:32`, `truffles-api/tests/test_message_endpoint.py:35`, `truffles-api/tests/test_message_endpoint.py:2498`, `truffles-api/tests/test_message_endpoint.py:2501`, `truffles-api/tests/test_message_endpoint.py:2515`.

## 6. Data Writes And Side Effects
- `FACT`: The file monkeypatches or patches active and legacy router functions across `_legacy`, `decision.py`, `booking.py`, `info.py`, `policy.py`, `response.py`, and `http.py`: `truffles-api/tests/test_message_endpoint.py:159`, `truffles-api/tests/test_message_endpoint.py:167`, `truffles-api/tests/test_message_endpoint.py:179`, `truffles-api/tests/test_message_endpoint.py:238`, `truffles-api/tests/test_message_endpoint.py:256`, `truffles-api/tests/test_message_endpoint.py:301`, `truffles-api/tests/test_message_endpoint.py:678`, `truffles-api/tests/test_message_endpoint.py:702`.
- `INFERENCE`: The file acts as a repository-level compatibility harness for many private surfaces, not just a black-box API test.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file itself has no runtime semantic authority.
- `FACT`: It does preserve repo-contract authority for `_legacy` helper names and root-level wrapper behavior by asserting them directly: `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/tests/test_message_endpoint.py:750`, `truffles-api/tests/test_message_endpoint.py:919`, `truffles-api/tests/test_message_endpoint.py:5191`.
- `INFERENCE`: This file is one of the main reasons frozen helper surfaces stay socially "alive" in the repo after cutover.

## 8. Truth Carriers Touched Here
- `FACT`: The file asserts continuity carriers like `expected_reply_type`, `ConversationState`, booking snapshots, and canonical-dialog-state sync behavior, but only as test assertions: `truffles-api/tests/test_message_endpoint.py:1182`, `truffles-api/tests/test_message_endpoint.py:2498`, `truffles-api/tests/test_message_endpoint.py:3231`, `truffles-api/tests/test_message_endpoint.py:5494`, `truffles-api/tests/test_message_endpoint.py:5570`.
- `INFERENCE`: This is contract-pin evidence, not live truth ownership.

## 9. Violations Against The Target Canon
- `FACT`: Active ingress contracts and legacy compatibility contracts are still mixed in one giant test file: mounted `/message` path tests sit beside root-level legacy wrapper tests and `_legacy` export tests: `truffles-api/tests/test_message_endpoint.py:485`, `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/tests/test_message_endpoint.py:5191`.
- `FACT`: The file explicitly pins the root-level `app.webhook.handle_webhook(...)` wrapper even though `app/main.py` does not mount `app.webhook`: `truffles-api/tests/test_message_endpoint.py:15`, `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.
- `INFERENCE`: This file is a major repo-level blocker for honest deletion/demotion of legacy wrapper and frozen helper surfaces.

## 10. Salvageable Parts
- `FACT`: The mounted `/message` path tests and direct modular `/webhook/direct` preflight tests are salvageable because they cover live entrypoints: `truffles-api/tests/test_message_endpoint.py:485`, `truffles-api/tests/test_message_endpoint.py:669`, `truffles-api/tests/test_message_endpoint.py:728`, `truffles-api/tests/test_message_endpoint.py:766`.
- `INFERENCE`: The active-contract subset should survive, but it should eventually be split away from frozen helper compatibility tests.

## 11. Demotion / Removal Candidates
- `FACT`: The root-level `legacy_webhook_module.handle_webhook(...)` compatibility test is a demotion/removal candidate once the repo intentionally breaks or replaces that wrapper contract: `truffles-api/tests/test_message_endpoint.py:739`, `truffles-api/tests/test_message_endpoint.py:750`.
- `FACT`: The `_legacy` symbol-forwarding assertion is another demotion candidate because it pins ambient export compatibility rather than active runtime behavior: `truffles-api/tests/test_message_endpoint.py:5191`.
- `INFERENCE`: The biggest immediate demotion target is not the entire file but the mixed legacy-compatibility slices inside it.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The repo still preserves legacy webhook-wrapper and `_legacy` export contracts inside its largest endpoint test file even though the mounted app path already moved to the modular package.
- `INFERENCE`: The package/wrapper cutover is incomplete not because `app.main` still mounts the old wrapper, but because test memory still preserves the old contracts inside a giant mixed file.

## 13. Open Questions
- `UNKNOWN`: Which subset of this file is still required as intentional compatibility coverage versus accidental frozen contract debt.
