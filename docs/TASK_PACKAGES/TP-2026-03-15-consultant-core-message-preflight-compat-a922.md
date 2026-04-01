# TP-2026-03-15-consultant-core-message-preflight-compat-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MESSAGE-PREFLIGHT-COMPAT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MEDIA-NORMALIZATION-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-media-normalization-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать `/message` совместимым с bounded new-core preflight lanes. После empty-message/media-normalization cutover `reasoning_core` законно может вернуть `WebhookResponse` без `conversation_id`; `message.py` не должен падать с внутренним `500`, а должен контрактно отклонять invalid text input на boundary и явно переводить no-conversation replies в deterministic HTTP errors.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-empty-message-planner-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-media-normalization-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/routers/message.py`
- `truffles-api/app/schemas/message.py`
- `truffles-api/app/services/reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/message.py`
  - `truffles-api/app/schemas/message.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,120p' truffles-api/app/routers/message.py`
  - `sed -n '1,120p' truffles-api/app/schemas/message.py`
  - `sed -n '330,420p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '430,560p' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - `reasoning_core.handle_webhook_payload(...)` now returns bounded preflight/degrade responses without `conversation_id` for valid new-core lanes such as empty-message reject and runtime exception degrade.
  - `truffles-api/app/routers/message.py` still assumes `conversation_id` is always present and raises `HTTPException(status_code=500, detail="Missing conversation_id")` when it is absent.
  - `MessageRequest.content` is plain `str`; whitespace-only text can pass request validation and reach the new-core empty-message preflight lane.
- `Detected drift (docs vs code)`: active new-core preflight ownership exists in `reasoning_core`, but `/message` still enforces the legacy assumption that every response materializes a conversation.

## One web search (mandatory before implementation)
- **Query (exact):** `site:fastapi.tiangolo.com FastAPI HTTPException status_code detail`
- **Date/time (local):** `2026-03-15 15:22 Asia/Almaty`
- **Why this query is precise:** this block needs one canonical reference for how `/message` should surface deterministic client/service errors once `reasoning_core` returns bounded no-conversation responses.
- **Sources opened (from this query):**
  - `FastAPI Tutorial — Handling Errors` — `https://fastapi.tiangolo.com/ko/tutorial/handling-errors/`
- **Source quality:** official FastAPI documentation.
- **Existing solutions found:** FastAPI expects application code to translate known failure modes into `HTTPException(status_code=..., detail=...)` rather than letting internal contract mismatches bubble into opaque 500s.
- **Decision:** `reuse + integrate` — keep the existing `/message` API shape, raise explicit `HTTPException` for missing-conversation cases, and avoid inventing a second response envelope.
- **Rejected options:**
  - making `MessageResponse.conversation_id` optional and silently returning success payloads without a conversation
  - leaving the internal `500 Missing conversation_id` behavior as-is
  - pushing a caller-specific empty-message branch into legacy webhook files
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** `/message` can now crash with an internal `500 Missing conversation_id` after the new-core preflight lanes were introduced in `reasoning_core`.
- **Minimal reproduction:**
  1. Send `/message` request with whitespace-only `content`, or mock `reasoning_core.handle_webhook_payload(...)` to return `WebhookResponse(success=False, message="Empty message", conversation_id=None)`.
  2. `message.py` calls `reasoning_core` successfully.
  3. Router checks `if not response.conversation_id` and raises `HTTPException(status_code=500, detail="Missing conversation_id")`.
- **Evidence to capture:**
  - request-boundary validation for empty/whitespace text
  - router-level translation of no-conversation responses into deterministic 4xx/5xx errors
  - targeted endpoint tests for both blocked and degraded no-conversation responses
- **Five Whys (or equivalent):**
  1. Why does `/message` 500? Because it still treats missing `conversation_id` as an unexpected invariant break.
  2. Why is that assumption now false? Because bounded new-core preflight and degrade lanes intentionally return `WebhookResponse` without materializing a conversation.
  3. Why does whitespace reach that path? Because `MessageRequest.content` does not strip/reject blank strings at the API boundary.
  4. Why is this a contract bug, not just a test gap? Because `/message` is a text-only API entrypoint and must reject invalid text input before it reaches shared runtime assumptions.
  5. Why does this increase future drift? Because each additional new-core slice would expose more legal no-conversation responses to a router that still encodes the legacy always-has-conversation contract.
- **Root cause statement:** `/message` still encodes the legacy assumption that every reasoning-core call yields a persisted conversation, while the new-core runtime now has bounded legal outcomes that intentionally return no `conversation_id`; the API boundary also fails to reject whitespace-only text before entering that path.
- **Fix mechanism:**
  - normalize and reject blank `MessageRequest.content` at schema validation
  - translate no-conversation `WebhookResponse` values in `message.py` into explicit `HTTPException` with deterministic status codes instead of internal 500 crashes

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/message.py`
  - `truffles-api/app/schemas/message.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official FastAPI error-handling docs for `HTTPException`
- **Why not reinvent the wheel:** the runtime already returns typed `WebhookResponse`; the smallest correct fix is to validate request text earlier and translate known no-conversation outcomes at the router boundary.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded compatibility block around one API entrypoint; no semantic expansion in legacy runtime.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- `/message` success path with a materialized conversation must remain unchanged.
- Shared `reasoning_core` planner slices must remain the semantic owner for preflight/degrade decisions.

## Scope
- Reject whitespace-only `/message` text at schema validation.
- Convert no-conversation `WebhookResponse` outcomes into deterministic HTTP errors in `message.py`.
- Add targeted endpoint tests for blocked and degraded no-conversation responses.
- Sync source-of-truth/state/session docs.

## Out of scope
- Any richer semantic planner slice cutover.
- Any change in `reasoning_core` semantic routing or legacy webhook router semantics.
- Making `/message` accept media payloads.
- Multi-pack acceptance or proof-path changes.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-message-preflight-compat-a922.md`
- `truffles-api/app/routers/message.py`
- `truffles-api/app/schemas/message.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this bounded `/message` preflight-compat TP with RCA and one web search.
2. Harden `MessageRequest` so blank text is rejected at the API boundary.
3. Translate no-conversation `WebhookResponse` outcomes in `message.py` into explicit HTTP errors.
4. Add targeted tests for whitespace reject, blocked no-conversation, and degraded no-conversation cases.
5. Re-run endpoint/architecture/packet checks and sync state/session docs.

## DoD
- Whitespace-only `/message` requests fail validation before reaching `reasoning_core`.
- `message.py` no longer raises opaque `500 Missing conversation_id` for known no-conversation outcomes.
- Successful `/message` responses with a real `conversation_id` remain unchanged.
- No legacy webhook semantic files are modified.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'message_request_validation or message_with_invalid_uuid or message_rejects_blank_content_before_reasoning_core or message_routes_through_webhook_pipeline or message_returns_422_for_blocked_no_conversation_response or message_returns_503_for_success_without_conversation_id or message_request_valid or message_request_trims_content or message_response_valid'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/routers/message.py truffles-api/app/schemas/message.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- request-schema validation for whitespace-only text
- deterministic `/message` tests for blocked/degraded no-conversation responses
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the fix requires changing `reasoning_core` semantics or widening `/message` into media support, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded boundary-hardening only on `/message`
- **Go/no-go signals:** endpoint tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** next block can resume richer planner-slice cutover once `/message` no longer crashes on legal no-conversation outcomes

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual compatibility block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No optional `conversation_id` in the successful `/message` response contract.
- No silent swallowing of no-conversation runtime outcomes.
- No caller-specific semantic duplication in `/message`.

## Risks/Blockers
- Validation must not reject valid non-empty text after trimming.
- Router translation must preserve the existing success contract for normal message flows.
- Full `truffles-api/tests/test_message_endpoint.py` still contains unrelated red LLM-policy-core/provider tests in this worktree environment; this block closes with the bounded `/message` selector plus shared consultant-core deterministic checks only.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only the `/message` boundary is hardened; richer semantic planning still lives in the legacy runtime and other callers may need similar compatibility work if they assume every runtime outcome materializes a conversation.
- `Why not in this block`: this block is intentionally limited to one API caller compatibility seam.
- `Risk if deferred`: future planner slices could surface more legal no-conversation outcomes into routers that still encode the legacy assumption.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any next planner slice that can return bounded no-conversation outcomes to another public entrypoint.

## Next-block contract (mandatory)
- `Next block objective`: cut one richer semantic planner slice from `reasoning_core` into the new core after `/message` caller compatibility is restored.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_message_endpoint.py -k 'message_request_validation or message_with_invalid_uuid or message_rejects_blank_content_before_reasoning_core or message_routes_through_webhook_pipeline or message_returns_422_for_blocked_no_conversation_response or message_returns_503_for_success_without_conversation_id or message_request_valid or message_request_trims_content or message_response_valid' && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: `/message` still crashes on no-conversation responses; whitespace text is not rejected at the boundary; source-of-truth is not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: legacy router semantic branches in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: over-broad validation, accidental response-contract widening, hidden no-conversation assumptions in other callers
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py`
