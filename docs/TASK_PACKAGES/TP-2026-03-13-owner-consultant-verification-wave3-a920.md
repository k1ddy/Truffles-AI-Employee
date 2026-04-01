# TP-2026-03-13-owner-consultant-verification-wave3-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE3-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE2-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE4-A920`

## Название/цель
Построить owner-facing chat workspace поверх simulation kernel: владелец бизнеса должен писать «как клиент» или «как скептик», видеть ответы консультанта, простой вердикт по каждому turn, откуда взят ответ, и честное объяснение, если системе не хватает данных или если handoff — это правильный исход.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave2-a920.md`
- `CA_ID`: `UX-39`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/ChatInterface.tsx`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/services/console_consultant_verification.py`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && sed -n '1,220p' console-web/src/components/ChatInterface.tsx`
  - `cd /home/zhan/truffles-main && sed -n '1,220p' console-web/src/app/business/page.tsx`
  - `cd /home/zhan/truffles-main && rg -n 'business-status-card|business-today-plan|data-trust|team-performance' console-web/src/app/business console-web/e2e/owner-admin-business.spec.ts`
  - `cd /home/zhan/truffles-main && rg -n 'FACT|COLLECT|HANDOFF|expected_reply|info_sections' truffles-api/app contracts -g '*.py' -g '*.yaml'`
- `FACT findings`:
  - There is no current owner-facing chat UI that talks to a business API instead of manager conversation endpoints.
  - Existing `ChatInterface` is optimized for manager outbound to real conversations; owner verification needs a different send/retry/query model.
  - Consultant runtime already produces the semantic outcomes we need (`FACT/COLLECT/HANDOFF`), but they are not translated into business-readable verdict copy.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:microsoft.com/en-us/haxtoolkit ai guidelines explain system limitations expectations`
- **Date/time (local):** `2026-03-13 18:13, Asia/Almaty`
- **Why this query is precise:** Wave3 is the owner trust surface; explanations and limitations must be understandable, honest, and confidence-building.
- **Sources opened (from this query):**
  - `Guidelines for Human-AI Interaction — Microsoft HAX Toolkit` — `https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/`
  - `Explain why the system did what it did` guidance inside HAX Toolkit — same official source above
- **Existing solutions found:** successful human-AI systems set expectations, explain outcomes, and disclose limitations without offloading raw internals onto the user.
- **Decision:** `integrate` — create business verdicts and explanation panels with plain-language statuses, explicit limitation copy, and optional advanced details hidden behind disclosure.
- **Rejected options:** raw trace-first UI; generic green/red badges without explanation; marketing-only copy that hides missing data.
- **Open questions:** whether advanced details should live in the same page or a drawer; decide based on layout proof in this wave.

## Root cause (mandatory)
- **Symptom:** Even with a safe simulation kernel, owners still would not trust the feature unless the UI explains what happened in business language.
- **Minimal reproduction:**
  1. Compare manager `ChatInterface` with owner needs.
  2. Observe the current component assumes a real conversation and manager actions.
  3. Observe there is no business verdict mapping for `FACT/COLLECT/HANDOFF` and no owner-readable explanation panel.
- **Evidence to capture:** current `ChatInterface` API assumptions, route shell, semantic outcome fields, copy guidelines.
- **Five Whys (or equivalent):**
  1. Why would a bare transcript be insufficient? Because owners are not validating transport; they are validating trustworthiness.
  2. Why is trust lost easily? Because hard/ambiguous cases feel like bugs unless the product explains them honestly.
  3. Why can’t we just show internal trace? Because it is technical noise for owner/admin users.
  4. Why do we need two modes (`как клиент` vs `найти слабые места`)? Because owners arrive with both curiosity and skepticism.
  5. Why is this a separate wave? Because explanation language and verdict UX can regress trust even if runtime behavior is correct.
- **Root cause statement:** the missing layer is not execution, but product translation: consultant outcomes are not yet mapped into owner-readable verdicts, explanations, and safe skepticism modes.
- **Fix mechanism:** add a dedicated owner chat workspace that reuses the simulation kernel but translates each turn into simple verdicts, explanation panels, and mode-aware UX.

## Reuse-first plan (mandatory)
- **Internal reuse:** `ChatInterface` layout patterns only, owner/admin card styles from business pages, simulation session API from Wave2, semantic outcomes from consultant runtime.
- **External reuse:** Microsoft HAX guidance for expectation-setting and explanation style.
- **Why not reinvent the wheel:** the layout can reuse existing chat/card primitives, but the message contract and explanation surface must be custom to owner validation.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `7`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** Wave3 is product UX + thin API extension, not a backend-heavy rewrite.

## Invariant
- Default owner view stays business-readable; raw trace/meta never becomes the primary surface.
- Handoff is shown as correct behavior when policy/law demands it.
- Missing data is displayed honestly and specifically.
- The owner cannot trigger real manager/bot actions from this page.

## Scope
- Build the main page chat workspace with two entry modes: `Проверить как клиент` and `Найти слабые места`.
- Add turn verdict chips and explanation side panel.
- Add source summary (`из данных бизнеса`, `нужно уточнение`, `передадим человеку`, `найден слабый сценарий`) and optional advanced details disclosure.
- Add retry/new session/reset controls.

## Out of scope
- Scenario library presets beyond a minimal empty state.
- Persistent weak-spot tracking statuses.
- Draft/live compare visual diff.

## Touch-list
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/*` (new)
- `console-web/src/app/business/consultant-verification/_lib/*` (new)
- `console-web/src/components/ChatInterface.tsx` (only if a small generic extraction is justified)
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `STATE.md`

## Plan (1..N)
1. Define owner-visible verdict vocabulary and turn panel information architecture.
2. Add page-level query/mutation hooks for session create + send message.
3. Build chat workspace with two explicit modes and clear empty-state instructions.
4. Add explanation panel mapping runtime outcomes to owner language.
5. Add advanced-details disclosure with bounded technical context only.
6. Add targeted owner-admin Playwright path and doc sync.

## DoD
- Owner/admin can send messages through the consultant verification page.
- Every assistant turn shows a plain-language verdict.
- Explanation panel tells the owner why the answer happened and whether data is missing or handoff is correct.
- No raw technical internals are required to understand the result.
- Targeted owner-admin e2e proves the main route and message flow.

## Checks
- `cd console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification chat"`
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k consultant_verification`

## Evidence
- screenshots for default, `как клиент`, and `найти слабые места` modes
- owner-admin Playwright output
- sample transcript showing `FACT`, `COLLECT`, and `HANDOFF` rendered in owner language

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** targeted page build + one Playwright grep + one backend test subset only
- **Stop condition:** if owner-readable verdict language cannot be agreed after two iterations, stop and run copy review before more code churn
- **Escalation path:** Top Architect / Brain approve any expansion into larger business IA changes

## Release safety (mandatory for non-doc changes)
- **Strategy:** owner/admin-only feature flag with one-client canary
- **Go/no-go signals:** targeted e2e green, no unauthorized role access, no page crash on empty/new session, no technical jargon regression in primary cards
- **Rollback:** disable flag and keep Wave2 API internal-only
- **Post-release monitoring window:** 24h owner usage review + screenshot audit

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
- `Drift closeout rule`:
  - verdict vocabulary and route copy must be updated in docs in the same block

## Rollback
- Hide the page behind the feature gate and revert page/components.
- Keep Wave2 API but unlinked from UI if rollback is needed.

## No-go
- Showing raw trace as the default explanation.
- Presenting handoff as a product failure.
- Hiding missing-data situations behind vague “не могу ответить” copy.
- Coupling the page to manager message endpoints.

## Risks/Blockers
- Copy can drift toward sales language and reduce honesty.
- Generic chat component reuse can over-constrain the owner flow if not kept bounded.
- Layout can become overcrowded if explanation and advanced details are not well separated.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no scenario presets beyond manual typing; no persistent findings list; no compare/replay.
- `Why not in this block`: Wave3 is about the primary trust surface only.
- `Risk if deferred`: medium; owners can test manually, but still lack structured difficult-scenario execution and issue capture.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave4-a920.md`
- `Expiry/trigger to stop deferral`: if owners are expected to self-serve at scale, Wave4 must follow immediately.

## Next-block contract (mandatory)
- `Next block objective`: add scenario library, difficult-question presets, and session summary.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'reference-packs|capabilities|scenario|eval' truffles-api/app console-web/src docs/CONSOLE_GUIDE.md`
- `Blocked-by conditions`: Wave3 page and main send/verdict flow must be green.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `console-web/src/app/business/consultant-verification/page.tsx`
- `Do not touch`: underlying simulation no-side-effect guarantees without dedicated tests
- `Open risks`: verdict vocabulary quality, layout density, honest missing-data copy
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'Проверить как клиент|Найти слабые места|consultant verification' console-web/src`
