# TP-2026-03-13-owner-consultant-verification-wave1-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE1-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE2-A920`

## Название/цель
Создать owner/admin entrypoint для `Проверка консультанта` в `Business` и зафиксировать foundation contract: бизнес-язык, route shell, overview endpoint, feature gate и extraction boundary, чтобы дальнейшие волны не росли как ad hoc feature внутри `console.py` и случайных page-компонентов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `CA_ID`: `UX-39`, `UX-43`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/app/business/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_owner_admin.py`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && ls console-web/src/app/business`
  - `cd /home/zhan/truffles-main && rg -n 'nav-business|nav-data-trust|nav-team-performance' console-web/src/components/ConsoleShell.tsx console-web/e2e/owner-admin-business.spec.ts`
  - `cd /home/zhan/truffles-main && rg -n 'getSummary|getIncidents|getDataTrustSummary|getTeamPerformanceSummary' console-web/src/lib/api-client.ts`
  - `cd /home/zhan/truffles-main && rg -n '"/business/summary"|"/business/incidents"|"/business/data-trust"|"/business/team-performance"' truffles-api/app/routers/console.py contracts/console_api/openapi.v1.yaml`
- `FACT findings`:
  - Current business route inventory has no consultant verification page.
  - Owner/admin navigation is already business-first and therefore is the correct placement for a trust/proof surface.
  - Backend owner/admin endpoints already live under `/business/*`; adding the new slice here preserves IA consistency.
  - `UX-20` remains open; new business logic must move toward extracted services, not `console.py` accumulation.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:microsoft.com/en-us/haxtoolkit "make clear why the system did what it did"`
- **Date/time (local):** `2026-03-13 18:05, Asia/Almaty`
- **Why this query is precise:** Wave1 is about expectations and trust framing, not runtime yet. The owner-facing copy must explain behavior and limitations in plain language.
- **Sources opened (from this query):**
  - `Guidelines for Human-AI Interaction — Microsoft HAX Toolkit` — `https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/`
  - `How do I use these guidelines? — Microsoft HAX Toolkit` — `https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/`
- **Existing solutions found:** expectation-setting, explanation, and limitation disclosure must be first-class UX elements rather than hidden technical details.
- **Decision:** `integrate` — use these principles to shape overview cards, language, and route framing; do not expose trace jargon on the first screen.
- **Rejected options:** calling the page `playground`; routing owners into `Knowledge` as a substitute; deferring copy/IA until after backend implementation.
- **Open questions:** whether the nav label should be `Проверка консультанта` or `Как отвечает консультант`; decision should be taken during copy review in this wave.

## Root cause (mandatory)
- **Symptom:** Owner/admin has no business-readable entrypoint to validate consultant behavior from inside Console.
- **Minimal reproduction:**
  1. Open `Business` navigation.
  2. Observe only summary/data-trust/team-performance/subscription/settings paths.
  3. Search owner/admin API slice and find no consultant verification overview endpoint.
- **Evidence to capture:** nav inventory, route inventory, API client surface, business router surface, owner/admin e2e smoke.
- **Five Whys (or equivalent):**
  1. Why is there no owner trust surface? Because owner/admin work focused on health/settings/metrics, not direct conversational proof.
  2. Why is this a product gap? Because owners evaluate the system by trying to break actual answers, not by reading KPI cards.
  3. Why can’t we jump directly to runtime implementation? Because without clear entrypoint/copy/feature gate, the feature will either confuse owners or overgrow ad hoc.
  4. Why is maintainability part of Wave1? Because the owner/admin router slice is already under decomposition pressure (`UX-20`).
  5. Why does this need a distinct wave? Because every later wave depends on a stable IA, schema boundary, and rollout gate.
- **Root cause statement:** there is no bounded owner/admin contract for consultant verification, so the product lacks a trustworthy starting point and the codebase lacks a safe place to grow the feature.
- **Fix mechanism:** add a dedicated business route, a thin overview endpoint, a clear feature/role gate, and a service-boundary rule that future waves extend extracted helpers instead of inlining business logic into `console.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:** `ConsoleShell` nav patterns, `business/page.tsx` card patterns, `businessApi`, `console_owner_admin.py`, owner-admin Playwright lane.
- **External reuse:** Microsoft HAX interaction guidelines for copy/expectation principles.
- **Why not reinvent the wheel:** Wave1 is foundation; we only need a bounded route and language contract, not a new IA system.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** Wave1 must ship a real route and contract surface, but remain narrow enough that later waves can layer runtime capabilities safely.

## Invariant
- No owner/admin technical jargon on the first screen (`trace`, `decision_meta`, raw reason codes) as primary content.
- Do not implement real chat execution in this wave.
- Do not let new owner/admin logic sprawl inside `console.py`; service extraction is mandatory for any non-trivial overview builder.
- Route must be owner/admin only and safely hidden/disabled for other roles.

## Scope
- Add nav entry and page shell for `/business/consultant-verification`.
- Add backend overview endpoint for readiness/gap summary and explanatory copy support.
- Add feature gate / rollout guard (`role + flag/capability`) and empty-state contract.
- Add owner-admin e2e smoke for visibility and route load.

## Out of scope
- Running consultant turns.
- Session persistence or simulation runtime.
- Draft/live compare.
- Weak-spot capture.

## Touch-list
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/business/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_owner_admin.py`
- `truffles-api/app/services/console_consultant_verification.py` (new)
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`

## Plan (1..N)
1. Introduce backlog/open-item wording and route naming contract.
2. Add extracted service helper for consultant verification overview response and keep router thin.
3. Expose `GET /console/v1/business/consultant-verification/overview` with owner/admin RBAC.
4. Add `businessApi` client and page shell with readiness cards, trust copy, and next-step placeholders.
5. Add navigation entry and update owner-admin Playwright smoke.
6. Sync OpenAPI/types/docs.

## DoD
- Owner/admin can navigate to `/business/consultant-verification`.
- Route loads with business-readable overview, readiness/gap cards, and explicit promise of what the next waves will enable.
- Endpoint and OpenAPI/types exist and are role-gated.
- `console.py` contains only thin endpoint wiring; non-trivial overview logic is extracted.
- Owner-admin Playwright smoke covers route visibility.

## Checks
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k consultant_verification_overview`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/components/ConsoleShell.tsx --file src/app/business/consultant-verification/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification"`

## Evidence
- endpoint contract in OpenAPI + generated types
- screenshot of route shell at desktop width
- Playwright smoke output
- backend test output proving owner/admin gate and overview payload

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** use targeted backend test selection + one targeted Playwright grep; no broad owner-admin suite unless targeted lane passes
- **Stop condition:** two failed iterations without clearer route/service contract evidence -> stop and re-open Wave1 RCA
- **Escalation path:** Top Architect / Brain approve any expansion beyond route shell and overview contract

## Release safety (mandatory for non-doc changes)
- **Strategy:** owner/admin-only route + feature flag/capability gate; canary on one internal client first
- **Go/no-go signals:** route renders for owner/admin only; no unauthorized access; no console navigation regression; targeted tests green
- **Rollback:** disable feature flag/capability and revert route/nav entry
- **Post-release monitoring window:** 24h navigation/access log review + owner-admin smoke replay

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
- `Drift closeout rule`:
  - route label, endpoint path, and feature-gate wording must match docs in the same PR

## Rollback
- Remove nav entry + route + overview endpoint and disable flag.
- Revert extracted service helper with the same PR if shell is not accepted.

## No-go
- Shipping a route with placeholder lorem copy or technical jargon.
- Embedding large overview assembly directly into `console.py`.
- Exposing route to manager/support roles.
- Sneaking runtime conversation execution into this wave.

## Risks/Blockers
- Naming can drift (`consultant test`, `playground`, `preview`) and break trust positioning.
- Owner/admin route inflation may regress nav density if entrypoint is not grouped correctly.
- Wave1 may be under-scoped if overview cards do not already encode honest limitations and readiness gaps.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no real test sessions; no turn-level verdicts; no issue capture; no draft/live compare.
- `Why not in this block`: Wave1 is only the bounded entrypoint and contract foundation.
- `Risk if deferred`: low if Wave2 starts immediately; medium if the shell ships alone for long because owners will click into a surface that cannot yet prove behavior.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave2-a920.md`
- `Expiry/trigger to stop deferral`: do not merge Wave1 to production-visible route without Wave2 scheduled as the immediate next block.

## Next-block contract (mandatory)
- `Next block objective`: implement safe simulation sessions and message execution via the real runtime.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'simulation_mode|simulation_id|is_simulation_context' truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/adapters/chatflow.py`
- `Blocked-by conditions`: Wave1 route + overview endpoint must be green and accepted.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `console-web/src/app/business/consultant-verification/page.tsx`
- `Do not touch`: consultant runtime behavior outside safe simulation hooks; `Knowledge` publish flow
- `Open risks`: naming, owner trust copy quality, router extraction discipline
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'consultant-verification' console-web/src/components/ConsoleShell.tsx console-web/src/app/business truffles-api/app/routers/console.py`
