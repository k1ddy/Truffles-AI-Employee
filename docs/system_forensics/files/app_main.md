# File Analysis: `truffles-api/app/main.py`

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
- `FACT`: `app/main.py` is the mounted FastAPI composition root. It imports the modular router package from `app.routers` and mounts `webhook.router` on the live app alongside the other API routers: `truffles-api/app/main.py:23`, `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:101`, `truffles-api/app/main.py:104`.
- `FACT`: The file does not import `app.webhook`; the root-level legacy wrapper is absent from the mounted app path: `truffles-api/app/main.py:23`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.
- `INFERENCE`: This file is the clearest repo-backed proof that the active ingress surface already moved to the modular webhook package even though legacy wrapper/test residue remains elsewhere.

## 2. Why This File Exists
- `FACT`: The file constructs the main FastAPI app, configures CORS, exception handling, metrics middleware, and mounts the router set used by the deployed API: `truffles-api/app/main.py:43`, `truffles-api/app/main.py:52`, `truffles-api/app/main.py:61`, `truffles-api/app/main.py:83`, `truffles-api/app/main.py:101`.
- `INFERENCE`: For this forensic family, its main value is not business logic but authoritative route mounting evidence.

## 3. Active Callers And Entrypoints
- `FACT`: Test clients and app-level endpoint tests import `app.main.app` directly, including `test_message_endpoint.py`, provider gateway app tests, and other app-surface tests: `truffles-api/tests/test_message_endpoint.py:23`, `truffles-api/tests/test_provider_gateway_inbound.py:14`, `truffles-api/tests/test_provider_gateway_outbound.py:15`.
- `UNKNOWN`: The exact production ASGI bootstrap module outside the repo tree.

## 4. Control Path Owned By This File
- `FACT`: The mounted webhook path is `app.main -> app.routers.webhook.router`, not `app.webhook.router`: `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.
- `FACT`: The same file mounts the other public router families without any special fallback to the root-level webhook wrapper: `truffles-api/app/main.py:101`, `truffles-api/app/main.py:105`, `truffles-api/app/main.py:111`.
- `INFERENCE`: `app/main.py` owns the final proof that `app/webhook.py` is unmounted residue rather than a hidden live ingress.

## 5. Data Reads
- `FACT`: The file reads env-derived CORS and OTel settings and DB health dependencies, but no semantic runtime state: `truffles-api/app/main.py:47`, `truffles-api/app/main.py:50`, `truffles-api/app/main.py:117`, `truffles-api/app/main.py:132`.
- `INFERENCE`: For this forensic block, the meaningful read is router composition, not runtime data.

## 6. Data Writes And Side Effects
- `FACT`: The file mutates the FastAPI app by registering middleware, exception handlers, and routers: `truffles-api/app/main.py:52`, `truffles-api/app/main.py:61`, `truffles-api/app/main.py:83`, `truffles-api/app/main.py:101`.
- `FACT`: It also exposes `/health` and later admin/metrics behavior through mounted handlers: `truffles-api/app/main.py:114`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: `app/main.py` does not own semantic routing or continuity logic; its authority is mounting and composition only: `truffles-api/app/main.py:101`, `truffles-api/app/main.py:104`.
- `INFERENCE`: The file is still strategically important because route composition decides which webhook surface is truly active.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carriers are created or reconciled here; the file mounts routers only: `truffles-api/app/main.py:101`, `truffles-api/app/main.py:104`.

## 9. Violations Against The Target Canon
- `FACT`: None directly inside the file; the important finding is negative: the file already points at the modular webhook package and does not keep the root-level wrapper on the mounted path: `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.
- `INFERENCE`: The remaining violation is therefore not route mounting here but shadow contracts outside this file that still preserve legacy webhook surfaces in repo memory.

## 10. Salvageable Parts
- `FACT`: The mounted-router composition is already aligned with a single ingress package and is salvageable as-is: `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.

## 11. Demotion / Removal Candidates
- `FACT`: No direct demotion target inside `app/main.py` was surfaced by this pass.
- `INFERENCE`: Demotion pressure belongs on legacy wrapper/test surfaces that are not mounted here.

## 12. What This Analysis Changes In System Understanding
- `FACT`: This file closes the question of which webhook router is actually live: the live app mounts the modular package router, not `app/webhook.py`.
- `INFERENCE`: Any remaining legacy webhook authority after this point is repo-contract debt, not hidden route-mount debt in the composition root.

## 13. Open Questions
- `UNKNOWN`: Whether any deployment artifact outside the repo still imports a different app module or remounts the root-level wrapper.
