# TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922

## Goal
Delete or bypass the split public-entrypoint materialization authority across `/message`, `/decision/handle`, `/provider/inbound`, and legacy `truffles-api/app/webhook.py` by converging response-materialization rules into one narrow non-frozen router-boundary contract surface, while keeping `truffles-api/app/services/reasoning_core.py` as the shared runtime owner and reducing legacy `app/webhook.py` to a compatibility shim or unreachable path.

## Canon refs
- `STATE.md` NOW: consultant core `continuity_broader_collapse` targeted frozen-waiver implementation
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-message-preflight-compat-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the targeted public-entrypoint contract runtime lane plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:fastapi.tiangolo.com APIRouter shared dependency helper response model HTTPException tutorial`
- **Date/time (local):** `2026-03-18 16:20:12 +0500`
- **Sources opened (from this query):**
  - `https://fastapi.tiangolo.com/tutorial/handling-errors/`
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- **Source quality:**
  - high-signal primary vendor documentation from FastAPI
- **Found ready-made solutions:**
  - `Handling Errors`: boundary code should raise explicit `HTTPException(status_code=..., detail=...)` for known API error outcomes instead of letting contract mismatches leak as opaque internal failures
  - `Bigger Applications`: shared router-boundary behavior should live in a dedicated reusable module/router surface instead of being re-implemented separately in each public endpoint
- **Decision:** `reuse + integrate`
  - reuse `truffles-api/app/services/reasoning_core.py` as the shared runtime owner for `WebhookResponse`
  - reuse the existing active `/webhook` adapter in `truffles-api/app/routers/webhook/http.py` as the canonical inbound runtime bridge
  - converge public response-materialization rules into one narrow shared router-boundary contract surface instead of scattering one-off helpers across entrypoints
- **Rejected options:**
  - push entrypoint-specific HTTP/materialization rules into `truffles-api/app/services/reasoning_core.py`: rejected because runtime ownership should stay transport-agnostic
  - leave `_require_materialized_message_response(...)` local to `/message` and add more per-entrypoint helpers: rejected because that preserves split public-entrypoint authority
  - keep legacy `truffles-api/app/webhook.py` as a separate materializing runtime path: rejected because that preserves the old conversation-creation hotspot
  - move public-entrypoint compatibility into `state_service.py` or frozen router files: rejected because this family is ingress/boundary compatibility, not continuity or semantic ownership

## Root cause (mandatory)
- **Symptom:** public entrypoints do not share one explicit contract for when a `WebhookResponse` must already be materialized with `conversation_id` and when a non-materialized response is acceptable.
- **Minimal reproduction:**
  - `rg -n "_require_materialized_message_response|handle_decision\(|handle_provider_inbound\(|handle_webhook\(|get_or_create_conversation\(" truffles-api/app/routers/message.py truffles-api/app/routers/decision_core.py truffles-api/app/routers/provider_gateway.py truffles-api/app/routers/webhook/http.py truffles-api/app/webhook.py`
- **Evidence:**
  - `truffles-api/app/routers/message.py:17` already owns a local `_require_materialized_message_response(...)` guard and translates missing-`conversation_id` outcomes into HTTP errors
  - `truffles-api/app/routers/decision_core.py:41` returns raw `WebhookResponse` from `reasoning_core.handle_webhook_payload(...)` with no explicit entrypoint contract for non-materialized outcomes
  - `truffles-api/app/routers/provider_gateway.py:53` does the same for `/provider/inbound` after translation/validation
  - `truffles-api/app/routers/webhook/http.py:640` and `truffles-api/app/routers/webhook/http.py:659` already act as the active shared webhook adapters and do not pre-materialize conversations before `reasoning_core`
  - legacy `truffles-api/app/webhook.py:580` still eagerly calls `get_or_create_conversation(...)` and keeps a separate old materializing runtime path alive
- **Five Whys:**
  1. Why is public entrypoint compatibility still partial? Because each public caller applies a different implicit rule about response materialization.
  2. Why is that a problem now? Because bounded new-core lanes can legally return `WebhookResponse` without `conversation_id`, so callers must either require materialization explicitly or allow non-materialized outcomes by contract.
  3. Why did `/message` drift first? Because it had to patch a local crash, but that fix stayed local instead of becoming a shared contract.
  4. Why does legacy `app/webhook.py` matter if newer routers exist? Because it still preserves the old eager conversation-materialization path and can keep the old authority seam alive until it is reduced to compatibility-only use.
  5. Why is one shared router-boundary contract surface the truthful destination? Because this family is about HTTP/public-ingress compatibility, while `reasoning_core` already owns runtime semantics and should not absorb caller-specific transport rules.
- **Root cause statement:** public-entrypoint materialization authority is split because `/message` hardens materialization locally, `/decision/handle` and `/provider/inbound` rely on implicit raw-`WebhookResponse` behavior, and legacy `app/webhook.py` still pre-materializes conversations inline before the shared runtime path; there is no single boundary owner that defines the contract per public surface.
- **Fix mechanism:**
  - introduce one shared non-frozen router-boundary contract surface for public entrypoint response handling
  - make `/message`, `/decision/handle`, and `/provider/inbound` consume that shared contract instead of encoding separate rules inline
  - reduce legacy `truffles-api/app/webhook.py` to a compatibility shim over the active shared path or make the old materializing seam unreachable

## Invariant
- `truffles-api/app/services/reasoning_core.py` remains the shared runtime owner and must not absorb entrypoint-specific HTTP/materialization semantics.
- No new mixed hotspot in `truffles-api/app/webhook.py`, `truffles-api/app/routers/message.py`, or `truffles-api/app/routers/webhook/http.py`.
- `state_service.py` must not grow.
- No wrapper forest or one-helper-per-entrypoint pattern counts as progress.
- If truthful convergence requires keeping legacy `app/webhook.py` as a second live runtime owner, stop and publish `GAP`.

## Scope
- Introduce one package-level implementation plan for the remaining `public_entrypoint_materialization_contract` family
- Converge entrypoint response-materialization ownership to one narrow shared router-boundary surface plus the existing `reasoning_core.handle_webhook_payload(...)` runtime owner
- Delete or bypass the old eager materialization seam in legacy `truffles-api/app/webhook.py`
- Update only directly impacted tests/docs/contracts for this family

## Out of scope
- `debounce_buffer_owner_convergence`
- `proof_black_box_completion`
- `multi_pack_acceptance`
- semantic-owner or continuity-owner runtime changes
- frozen `truffles-api/app/routers/webhook/decision.py`
- frozen `truffles-api/app/routers/webhook/booking.py`
- frozen `truffles-api/app/routers/webhook/pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922.md`
- `STATE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STRUCTURE.md`
- `truffles-api/app/routers/public_entrypoint_contract.py`
- `truffles-api/app/routers/message.py`
- `truffles-api/app/routers/decision_core.py`
- `truffles-api/app/routers/provider_gateway.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/webhook.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_decision_core_app.py`
- `truffles-api/tests/test_provider_gateway_inbound.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- any directly impacted public-entrypoint tests/docs only if required

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py` as the shared runtime owner returning `WebhookResponse`
  - `truffles-api/app/routers/message.py` existing `_require_materialized_message_response(...)` boundary logic as the seed for the shared contract
  - `truffles-api/app/routers/webhook/http.py` as the active webhook adapter that already delegates directly to `reasoning_core`
  - `truffles-api/tests/test_message_endpoint.py`, `truffles-api/tests/test_decision_core_app.py`, and `truffles-api/tests/test_provider_gateway_inbound.py`
- **External reuse:**
  - FastAPI official `Handling Errors` and `Bigger Applications - Multiple Files` guidance from the single mandatory query above
- **Why this reuse mix is truthful:**
  - the runtime return type is already shared
  - the split lives in router-boundary callers, so the owner surface should also stay at the router boundary
  - one narrow shared contract module is smaller and more truthful than growing `reasoning_core` or repeating helper code in every entrypoint

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. Define the exact public-entrypoint policy modes: materialized response required vs raw `WebhookResponse` allowed by contract.
3. Implement one shared router-boundary contract surface for those policy modes.
4. Migrate `/message`, `/decision/handle`, and `/provider/inbound` to that shared owner surface.
5. Reduce legacy `truffles-api/app/webhook.py` to a compatibility shim over the active shared path or make its eager materialization seam unreachable.
6. Add or tighten targeted public-entrypoint regression coverage.
7. Run the targeted public-entrypoint lane and required guards.
8. Record evidence in `STATE.md` only if the old split public-entrypoint materialization seam is actually deleted or unreachable.

## DoD
- `/message`, `/decision/handle`, and `/provider/inbound` no longer own separate ad-hoc response-materialization rules inline
- one shared non-frozen router-boundary surface owns the public entrypoint contract
- legacy `truffles-api/app/webhook.py` no longer owns live eager conversation materialization as a public runtime authority seam
- `truffles-api/app/services/reasoning_core.py` remains the shared runtime owner
- targeted public-entrypoint tests pass
- required architecture/session guards pass
- `STATE.md` records the deleted/unreachable old public-entrypoint seam with evidence

## Checks
- `rg -n "_require_materialized_message_response|handle_decision\(|handle_provider_inbound\(|handle_webhook\(|get_or_create_conversation\(" truffles-api/app/routers/message.py truffles-api/app/routers/decision_core.py truffles-api/app/routers/provider_gateway.py truffles-api/app/routers/webhook/http.py truffles-api/app/webhook.py`
- `python3 -m py_compile truffles-api/app/routers/public_entrypoint_contract.py truffles-api/app/routers/message.py truffles-api/app/routers/decision_core.py truffles-api/app/routers/provider_gateway.py truffles-api/app/routers/webhook/http.py truffles-api/app/webhook.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_decision_core_app.py truffles-api/tests/test_provider_gateway_inbound.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'message_routes_through_webhook_pipeline or message_returns_422_for_blocked_no_conversation_response or message_returns_503_for_success_without_conversation_id or missing_secret_returns_401 or valid_secret_returns_200'`
- `pytest -q truffles-api/tests/test_decision_core_app.py`
- `pytest -q truffles-api/tests/test_provider_gateway_inbound.py -k 'provider_inbound_routes_to_webhook or provider_inbound_rejects_invalid_tenant_context_source or provider_inbound_rejects_invalid_channel'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` if `reasoning_core` ownership/contracts change materially
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the deleted or bypassed split public-entrypoint materialization seam and the surviving shared boundary owner surface
- green targeted public-entrypoint runtime lane plus required guards
- `STATE.md` entry that names the deleted/unreachable old public-entrypoint seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** hotspot grep plus `python3 -m py_compile`
- **Targeted lane next:** `message` / `decision_core` / `provider_gateway` deterministic app tests only
- **Contract lane after targeted pass:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` only if `reasoning_core` ownership/contracts changed materially
- **Stop condition:** if the implementation requires entrypoint-specific branches inside `reasoning_core`, or if legacy `app/webhook.py` cannot be reduced without keeping a second live runtime owner, stop and return to RCA instead of growing helpers
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only boundary/runtime compatibility validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - one shared public-entrypoint contract surface exists
  - legacy `app/webhook.py` no longer owns live eager conversation materialization
  - targeted public-entrypoint tests pass
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's changes to the touched public-entrypoint files plus synced docs
  - rerun the targeted public-entrypoint test lane and required guards
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'message_returns_422_for_blocked_no_conversation_response or message_returns_503_for_success_without_conversation_id or missing_secret_returns_401 or valid_secret_returns_200'`
  - `pytest -q truffles-api/tests/test_decision_core_app.py`
  - `pytest -q truffles-api/tests/test_provider_gateway_inbound.py -k 'provider_inbound_routes_to_webhook or provider_inbound_rejects_invalid_tenant_context_source or provider_inbound_rejects_invalid_channel'`
- **Post-release monitoring window:** first post-merge consultant-core block only; do not advance to debounce/proof work if the split public-entrypoint materialization family reappears

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted public-entrypoint/runtime checks.

## No-go
- Do not grow `reasoning_core.py` into a caller-specific HTTP/materialization switchboard.
- Do not keep one helper per entrypoint and count that as convergence.
- Do not leave legacy `truffles-api/app/webhook.py` as a second live materializing runtime path.
- Do not move this family into `state_service.py` or frozen webhook semantic files.
- Do not claim consultant correctness, full runtime retirement, or full ingress closure from this block.

## Risks / blockers
- `truffles-api/app/webhook.py` is a legacy compatibility module; if hidden external imports still rely on its full old behavior, the block must prove shim compatibility instead of assuming deletion.
- `/message` has a stricter materialized-response contract than `/decision/handle` and `/provider/inbound`; the shared owner must encode that difference without becoming a new mixed hotspot.
- `truffles-api/app/routers/webhook/http.py` is already the active webhook adapter; if the implementation duplicates its role elsewhere instead of reusing it, the block is invalid.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `debounce_buffer_owner_convergence`, `proof_black_box_completion`, and `multi_pack_acceptance` remain open after this package
- richer legacy `/webhook` runtime internals still remain behind `reasoning_core` / frozen `decision.py` even if public entrypoint contracts converge
- boundary-owner and proof-path long-range closure are still incomplete overall

### Why not in this block
- this package only deletes the split public-entrypoint materialization family
- collapsing debounce, proof observers, or broader legacy runtime retirement into the same block would blur owner boundaries again

### Risk if deferred
- new entrypoint-facing runtime lanes can keep reintroducing contradictory `conversation_id` / no-conversation assumptions
- legacy `app/webhook.py` remains available as a second public-ingress materialization hotspot

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-debounce-buffer-owner-convergence-package-a922` (to be authored only after this package either lands or truthfully blocks)
- `TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922` (ordered later)

### Expiry/trigger to stop deferral
- stop deferral if any new public entrypoint or boundary helper introduces another local materialization rule before this package lands

## Next-block contract (mandatory)
### Next block objective
- implement the `public_entrypoint_materialization_contract` runtime family convergence defined by this TP and delete or bypass the split public-entrypoint materialization seam

### First deterministic check command
- `rg -n "_require_materialized_message_response|handle_decision\(|handle_provider_inbound\(|handle_webhook\(|get_or_create_conversation\(" truffles-api/app/routers/message.py truffles-api/app/routers/decision_core.py truffles-api/app/routers/provider_gateway.py truffles-api/app/routers/webhook/http.py truffles-api/app/webhook.py`

### Blocked-by conditions
- inability to keep the shared contract owner at the router boundary without growing `reasoning_core.py`
- any implementation that leaves legacy `truffles-api/app/webhook.py` as a second live eager materialization owner
- any implementation that converges by adding one wrapper/helper per public entrypoint instead of one shared contract surface
- any implementation that requires frozen semantic files or `state_service.py` to absorb public-entrypoint compatibility

### Owner role for closure
- Brain / Top Architect
