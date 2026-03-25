# TP-2026-03-25 Consultant Core Public Entrypoint HTTP Contract And Message Endpoint Surface Reset A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-PUBLIC-ENTRYPOINT-HTTP-CONTRACT-AND-MESSAGE-ENDPOINT-SURFACE-RESET-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `449d5274`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `UNLOCKS`: rerun of the blocked guarded Phase E acceptance replay

## Название/цель
Guarded acceptance честно остановился на mandatory deterministic suite до replay. Цель блока — убрать один bounded blocker family: вернуть корректный public-entrypoint HTTP contract для preflight ошибок и сбросить stale `test_message_endpoint.py` imports/patch paths на текущий live runtime surface без возврата shadow runtime.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`

## One web search (mandatory before implementation)
- **Query (exact):** `FastAPI HTTPException raise re-raise official docs`
- **Date/time (local):** 2026-03-25 15:52, Asia/Almaty
- **Why this query is precise:** the surfaced blocker is specifically about whether preflight/auth failures should propagate as HTTP errors through the public entrypoint contract instead of being converted into a success fallback payload.
- **Sources opened (from this query):**
  - FastAPI docs: `Simple OAuth2 with Password and Bearer` — https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
- **Existing solutions found:** FastAPI expects `HTTPException` to be raised and propagated as an HTTP error response rather than converted into a success payload.
- **Decision:** reuse; propagate `HTTPException` through the consultant-runtime safety net instead of swallowing it into `WebhookResponse(success=True, message="Runtime fallback")`.
- **Rejected options:**
  - broad exception swallowing in the runtime safety net
  - widening `app.routers.webhook.__init__` back into a giant public compatibility surface
- **Open questions:** whether `test_message_endpoint.py` can fully reset onto `_legacy` plus current live entrypoint patches in one pass, or whether a smaller follow-up split will still be needed after the public-entrypoint fix.

## Root cause (mandatory)
- **Symptom:** acceptance preflight stopped before replay because `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py` failed with `377 failed`.
- **Minimal reproduction:** run `curl -fsS http://localhost:8000/admin/health`, then `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py` from the current worktree.
- **Evidence:**
  - `/message` tests patching `app.services.reasoning_core.handle_webhook_payload` now receive `Invalid tenant_context` because the live public entrypoint path is `app.routers.message -> app.routers.public_entrypoint_contract.handle_public_webhook_payload -> app.core.consultant_runtime.handle_webhook_payload`.
  - webhook auth tests expecting `401` currently get `200` while logs show `HTTPException: 401: Invalid webhook secret`, proving the runtime safety net is swallowing preflight HTTP exceptions.
  - many failures are `AttributeError` on `app.routers.webhook` because `truffles-api/app/routers/webhook/__init__.py` is intentionally minimal while `truffles-api/tests/test_message_endpoint.py` still imports the package as a giant legacy helper surface.
- **Five Whys:**
  1. Why did the deterministic suite fail before replay? Because `test_message_endpoint.py` is still anchored to stale ingress contracts and package exports.
  2. Why are `/message` and `/webhook` tests stale? Because live ingress now routes through `public_entrypoint_contract` and `consultant_runtime`, but the suite still patches `reasoning_core` and imports `app.routers.webhook` package-level helpers.
  3. Why do webhook auth tests return `200` instead of `401`? Because `consultant_runtime.handle_webhook_payload()` catches `HTTPException` inside its generic runtime safety net.
  4. Why is that dangerous beyond tests? Because invalid secret / invalid tenant context are hard preflight failures and must stay observable as HTTP errors, not be converted into success fallback payloads.
  5. Why did the package-import failures surface now? Because earlier demolition intentionally shrank `app.routers.webhook.__init__.py` to a thin ingress surface, but the deterministic suite was never reset to `_legacy` or direct live-module imports.
- **Root cause statement:** one blocker family combines a real public-entrypoint contract bug (`HTTPException` swallowed by consultant runtime) with stale deterministic-suite surface assumptions (`test_message_endpoint.py` still imports and patches deprecated ingress/package paths).
- **Fix mechanism:** propagate `HTTPException` through `consultant_runtime`, then reset `test_message_endpoint.py` to the current live ingress/test surface without re-expanding runtime package ownership.

## Reuse-first plan (mandatory)
- **Internal reuse:** `app.routers.webhook._legacy` for legacy helper exports inside tests, `app.routers.public_entrypoint_contract.handle_public_webhook_payload`, existing live modules under `app.routers.webhook.decision` / `booking`.
- **External reuse:** none beyond the FastAPI docs above.
- **Why not reinvent the wheel:** the helper/export surfaces already exist; the bug is incorrect contract wiring, not missing infrastructure.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `2000`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded runtime/test contract repair on a long-lived implementation branch.

## Invariant
- Do not reintroduce semantic owner branching or phrase logic into runtime core.
- Do not widen `app.routers.webhook.__init__` into a new runtime shadow surface.
- Do not run the guarded acceptance replay again until `test_message_endpoint.py` is green.

## Scope
- propagate hard preflight `HTTPException` correctly through public entrypoints
- reset `test_message_endpoint.py` imports/patch paths to the current live ingress/test surface
- rerun bounded deterministic checks for this family

## Out of scope
- booking/runtime semantic behavior changes
- replay/acceptance reruns in this block
- open-world/general-pack work

## Touch-list
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_message_endpoint.py`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`

## Plan (1..N)
1. Fix the consultant-runtime safety net so `HTTPException` preflight failures propagate unchanged.
2. Reset `test_message_endpoint.py` to `_legacy` / current live ingress patch points instead of stale package and reasoning-core paths.
3. Run bounded deterministic checks for this family only.
4. Publish the blocker-closure evidence and reopen acceptance as the next block.

## DoD
- invalid secret / invalid tenant context public-entrypoint tests observe HTTP errors again
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py` is green
- no runtime semantic owner widening is introduced
- acceptance remains deferred, not rerun, in this block

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k 'message_returns_422_for_blocked_no_conversation_response or message_returns_503_for_success_without_conversation_id or TestWebhookAuth'`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0 expensive acceptance runs in this block
- **Fail-fast / scenario lock:** stop on the first deterministic blocker that remains after the bounded fix
- **Stop condition:** if `truffles-api/tests/test_message_endpoint.py` is still red after the bounded contract reset, stop and publish the next blocker instead of widening scope
- **Escalation path:** Brain / Top Architect decide any additional split if another distinct failure family remains

## Release safety (mandatory for non-doc changes)
- **Strategy:** local bounded runtime/test contract repair only; no rollout or deploy changes in this block
- **Go/no-go signals:** public-entrypoint HTTP errors propagate correctly again, `truffles-api/tests/test_message_endpoint.py` is green, and architecture/session guards stay green
- **Rollback:** revert the bounded runtime/test contract changes if they widen the runtime surface or break the deterministic suite further
- **Post-release monitoring window:** not applicable; acceptance remains blocked until the next block

## Evidence
- green deterministic output for `truffles-api/tests/test_message_endpoint.py`
- updated canon docs with blocker closure
- no acceptance replay artifact in this block

## No-go
- no replay/acceptance run in this block
- no semantic hardcode in runtime core
- no re-expansion of `app.routers.webhook.__init__` into the old mega-surface

## Risks/Blockers
- `test_message_endpoint.py` may still contain more than one stale contract family after the first reset
- public-entrypoint error propagation may affect a few old tests that asserted the swallowed-fallback behavior

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: guarded Phase E acceptance replay remains open; generic pack minimum-data-contract debt remains open.
- `Why not in this block`: this block only repairs the surfaced deterministic blocker family that stopped acceptance before replay.
- `Risk if deferred`: acceptance stays blocked and public-entrypoint error handling remains dishonest.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `Expiry/trigger to stop deferral`: once `test_message_endpoint.py` is green, reopen acceptance immediately.

## Next-block contract (mandatory)
- `Next block objective`: reopen the guarded Phase E acceptance replay after the green public-entrypoint/message-endpoint deterministic reset.
- `First deterministic check command`: `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `Blocked-by conditions`: this block stays open if public-entrypoint HTTP errors are still swallowed or the deterministic suite is still red.
- `Owner role for closure`: Brain / Top Architect
