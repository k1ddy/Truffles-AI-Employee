# TP-2026-03-13-owner-consultant-verification-wave2-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE2-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE1-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE3-A920`

## Название/цель
Построить simulation kernel для owner/admin consultant verification: Console должен запускать реальный consultant runtime в безопасном режиме без outbound/send/booking/handover side effects, с сохранением turn-level evidence и versioned session contract.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave1-a920.md`
- `CA_ID`: `UX-40`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/adapters/chatflow.py`
  - `truffles-api/app/services/ai_service.py`
  - `truffles-api/app/schemas/webhook.py`
  - `truffles-api/app/schemas/outbox_payload.py`
  - `truffles-api/app/routers/console.py`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'simulation_mode|simulation_id|simulation_llm|simulation_time' truffles-api/app/services/state_service.py truffles-api/app/schemas/webhook.py truffles-api/app/schemas/outbox_payload.py`
  - `cd /home/zhan/truffles-main && rg -n 'simulation' truffles-api/app/routers/webhook/outbox.py truffles-api/app/adapters/chatflow.py truffles-api/app/services/manager_message_service.py`
  - `cd /home/zhan/truffles-main && rg -n 'metrics_daily_service' truffles-api/app/services/metrics_daily_service.py`
  - `cd /home/zhan/truffles-main && rg -n 'consultant-verification' truffles-api/app/routers/console.py contracts/console_api/openapi.v1.yaml`
- `FACT findings`:
  - Simulation markers already exist in webhook/runtime contracts and are explicitly excluded from normal metrics accounting.
  - Handover and outbound paths already contain simulation-safe branches, but they are triggered only through lower-level message metadata and allowlists.
  - There is no owner/admin session model, transcript ledger, or Console endpoint for sending inbound test turns.
  - There is no durable contract for `source_mode` (`live` vs `draft`) or `challenge_mode` (`as_client` vs `stress`) at the Console API boundary.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:cloud.google.com/dialogflow/cx/docs concept test case environment versions`
- **Date/time (local):** `2026-03-13 18:09, Asia/Almaty`
- **Why this query is precise:** Wave2 needs the runtime/session contract for simulated turns and later compare/replay across current vs draft sources.
- **Sources opened (from this query):**
  - `Dialogflow CX test cases` — `https://cloud.google.com/dialogflow/cx/docs/concept/test-case`
  - `Dialogflow CX environments` — `https://cloud.google.com/dialogflow/cx/docs/concept/environment`
- **Existing solutions found:** simulation sessions need durable transcripts and a clear environment/version envelope so later replay/compare does not become ambiguous.
- **Decision:** `integrate` — create explicit consultant verification sessions/turns and `source_mode` contract while keeping Truffles runtime as the single semantic owner.
- **Rejected options:** ephemeral in-browser only chats; reusing real customer conversations; mock runtime responses disconnected from policy/tools/packs.
- **Open questions:** whether session persistence should be normalized DB tables or a bounded JSON ledger in an existing console operations table; choose the option with clearer audit/replay semantics.

## Root cause (mandatory)
- **Symptom:** Truffles can simulate runtime behavior internally, but owner/admin cannot safely use it from Console.
- **Minimal reproduction:**
  1. Inspect runtime code and find simulation-safe hooks.
  2. Inspect Console API and find no endpoints that create or run consultant verification sessions.
  3. Observe there is no durable transcript/evidence model for owner/admin testing.
- **Evidence to capture:** simulation hook code refs, missing endpoint search, metrics exclusion code, no-side-effect proof tests.
- **Five Whys (or equivalent):**
  1. Why can’t owners run safe tests? Because simulation is not promoted to a first-class Console API.
  2. Why is that dangerous? Because ad hoc testing could leak real outbox, bookings, or handovers.
  3. Why isn’t UI-only storage enough? Because later waves need replay, compare, and remediation evidence.
  4. Why can’t we just duplicate runtime logic? Because LLM-first semantic ownership must remain single-owner; duplicate logic will drift.
  5. Why must Wave2 be backend-heavy? Because every later owner-facing promise depends on safe execution semantics and durable evidence.
- **Root cause statement:** simulation exists as a lower-level runtime capability but lacks a Console-owned session/turn contract that safely exposes it to owner/admin users.
- **Fix mechanism:** add explicit consultant verification session/turn storage and endpoints that invoke the existing runtime in `simulation_mode`, persist outcome evidence, and fail closed on any side-effect path.

## Reuse-first plan (mandatory)
- **Internal reuse:** `state_service.py` simulation context, webhook/outbox simulation suppression, simulation-aware chatflow adapter, metrics exclusions, existing decision meta/trace contracts.
- **External reuse:** Dialogflow CX test-case/environment pattern for durable session + source-mode envelope.
- **Why not reinvent the wheel:** the runtime already knows how to simulate; the missing piece is a safe Console contract and ledger, not another execution engine.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** Wave2 is almost entirely backend contract + tests; docs are secondary and must follow the implementation.

## Invariant
- Real outbound sends must remain suppressed in simulation.
- Simulation turns must still produce `decision_meta` / `decision_trace` evidence.
- No real booking/handover mutation may be committed from owner verification sessions.
- Owner/admin verification must not contaminate production business metrics.
- Runtime semantic ownership stays in the existing consultant path; no shadow decision stack.

## Scope
- Add session/turn models and migration(s) for consultant verification.
- Add Console API endpoints for create session, append owner message, get session transcript, and list recent sessions.
- Add explicit request envelope for `source_mode`, `challenge_mode`, `simulation_id`, and actor scope.
- Persist turn verdict payload needed by Wave3 (`outcome`, `business_verdict`, `source_refs`, `would_handoff`, `would_book`, `gap_detected`).
- Add deterministic tests proving no real side effects.

## Out of scope
- Final owner UI/side panel design.
- Scenario library.
- Weak-spot capture lifecycle.
- Draft/live comparison UI.

## Touch-list
- `truffles-api/migrations/*consultant_verification*.sql` (new)
- `truffles-api/app/models/*` (new consultant verification session/turn models if required)
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/services/manager_message_service.py`
- `truffles-api/app/tests/test_console_consultant_verification_api.py` (new)
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_message_endpoint.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_GUIDE.md`
- `STATE.md`

## Plan (1..N)
1. Define durable session + turn schema and mutation boundaries.
2. Implement extracted service that invokes the existing consultant runtime with simulation metadata.
3. Add owner/admin API endpoints and OpenAPI schemas.
4. Persist turn evidence and explicit side-effect preview fields.
5. Add deterministic tests for `no outbound`, `no booking commit`, `no handover commit`, `metrics exclusion`, and `owner/admin gate`.
6. Sync generated types and docs.

## DoD
- Owner/admin can create a consultant verification session via Console API.
- Owner message produces a simulated consultant turn with persisted evidence.
- No real outbound/send/booking/handover side effect occurs.
- OpenAPI/types are synced.
- Deterministic tests prove fail-closed behavior across side-effect boundaries.

## Checks
- `cd truffles-api && pytest -q tests/test_console_consultant_verification_api.py`
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k consultant_verification`
- `cd truffles-api && pytest -q tests/test_message_endpoint.py -k simulation`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`

## Evidence
- migration + model/service code refs
- backend test outputs proving no-side-effect contract
- sample API transcript with `simulation=true`
- decision_meta/decision_trace bundle for one simulated turn

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** one deterministic backend suite per iteration; no long LLM quality lane until Wave3 UI contract is present
- **Stop condition:** any observed real side effect in simulation -> immediate stop-the-line and rollback to RCA
- **Escalation path:** Top Architect must approve any extra realism runs touching live-like connectors

## Release safety (mandatory for non-doc changes)
- **Strategy:** backend endpoints behind owner/admin RBAC plus feature flag; internal-client canary only
- **Go/no-go signals:** no-side-effect tests green; no simulation rows leaking into normal metrics; owner/admin auth gate green
- **Rollback:** disable flag and revert endpoints/migration usage (migration remains but routes disabled)
- **Post-release monitoring window:** 24h audit of simulation session volume and absence of unexpected outbox/handover rows

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `SPECS/SYSTEM_REFERENCE.md` (simulation-safe console path if contract changes)
  - `STATE.md`
- `Drift closeout rule`:
  - endpoint names and simulation guarantees must be documented in the same block

## Rollback
- Disable route/API feature gate.
- Revert service/router changes; keep data tables unused if rollback happens after migration.

## No-go
- Reusing real customer conversations as owner test sessions.
- Mocking consultant responses in the API layer.
- Allowing simulation messages to enter standard delivery pipelines.
- Skipping deterministic no-side-effect tests because “it works locally”.

## Risks/Blockers
- Existing simulation hooks may not cover every side-effect family (booking/handover/media/retry paths).
- Session persistence model may become too heavy if designed like full customer conversations instead of bounded verification sessions.
- Draft/live source envelope may force follow-up schema work earlier than planned.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no owner UI polish; no scenario library; no finding capture; no compare/replay UX.
- `Why not in this block`: Wave2 is the safety kernel only.
- `Risk if deferred`: medium; without Wave3 the API is not owner-usable yet, but the system becomes safely testable.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave3-a920.md`
- `Expiry/trigger to stop deferral`: do not expose the route broadly until Wave3 renders the session output in business-readable form.

## Next-block contract (mandatory)
- `Next block objective`: ship owner-readable chat workspace and verdict/explainability panels on top of the safe simulation kernel.
- `First deterministic check command`: `cd /home/zhan/truffles-main && sed -n '1,220p' console-web/src/components/ChatInterface.tsx`
- `Blocked-by conditions`: Wave2 backend endpoints and tests must be green.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py`
- `Do not touch`: production customer conversation persistence semantics without explicit reason; metrics contracts unless simulation exclusions are proven
- `Open risks`: no-side-effect completeness, data model shape, source_mode envelope
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'simulation_mode|simulation_id|consultant verification' truffles-api/app console-web/src/lib/api-client.ts`
