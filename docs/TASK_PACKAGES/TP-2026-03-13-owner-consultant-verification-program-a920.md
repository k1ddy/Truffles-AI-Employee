# TP-2026-03-13-owner-consultant-verification-program-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `PARENT_BLOCK_ID`: `none`
- `DEPENDS_ON`: `UX-20` remains open but not blocking program planning; execution waves must respect `UX-20` extraction direction
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE1-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE2-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE3-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE4-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE5-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE6-A920`, `CONSOLE-OWNER-CONSULTANT-VERIFICATION-CLOSEOUT-A920`

## Название/цель
Сформировать полную программу owner/admin-поверхности `Проверка консультанта` в `Console Plane`: владелец бизнеса должен уметь безопасно «играть роль клиента», пытаться сломать систему, видеть честный вердикт по каждому ответу и не терять реальные слабые места, если они обнаружены.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `CA_ID`: `UX-39`, `UX-40`, `UX-41`, `UX-42`, `UX-43`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/app/business/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/ChatInterface.tsx`
  - `console-web/e2e/owner-admin-business.spec.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_owner_admin.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && ls console-web/src/app/business`
  - `cd /home/zhan/truffles-main && rg -n '"/business/|/business/' truffles-api/app/routers/console.py contracts/console_api/openapi.v1.yaml`
  - `cd /home/zhan/truffles-main && rg -n 'consultant-test|consultant trust|проверка консультанта|red-team' console-web/src truffles-api/app docs`
  - `cd /home/zhan/truffles-main && rg -n 'simulation_mode|simulation_id|is_simulation_context' truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/adapters/chatflow.py`
  - `cd /home/zhan/truffles-main && rg -n 'knowledge_backlog|learning candidates|learning_candidate' truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - Business section currently exposes only `page.tsx`, `data-trust`, and `team-performance`; there is no dedicated owner-facing consultant verification surface.
  - `businessApi` exposes summary/incidents/data-trust/team-performance/owner-mode operations only; there are no consultant verification endpoints.
  - Runtime already contains simulation primitives (`simulation_mode`, `simulation_id`, simulation-safe handover/topic behavior, outbox suppression), but they are not exposed through Console as a first-class owner/admin workflow.
  - Learning/knowledge feedback infrastructure already exists (`knowledge_backlog`, `learning_candidates`), but owners cannot flag a bad consultant answer from a business-facing surface and follow its remediation state.
  - Existing owner/admin Playwright lane covers `Business`, `Data Trust`, `Team Performance`, `Subscription`, `Settings`, but does not cover a consultant verification surface.
- `Detected drift (docs vs code)`: `none` — current gap is absence of feature, not docs/code disagreement.

## One web search (mandatory before implementation)
- **Query (exact):** `site:cloud.google.com/dialogflow/cx/docs test case simulator save conversation`
- **Date/time (local):** `2026-03-13 18:01, Asia/Almaty`
- **Why this query is precise:** It targets the most relevant owner-facing pattern: simulate a conversational agent, save real conversations as reusable test cases, and replay them after changes.
- **Sources opened (from this query):**
  - `Dialogflow CX test cases documentation` — `https://cloud.google.com/dialogflow/cx/docs/concept/test-case`
  - `Dialogflow CX environments and versions` — `https://cloud.google.com/dialogflow/cx/docs/concept/environment`
- **Existing solutions found:** simulator -> save conversation -> replay against another environment/version is the strongest reference pattern for our owner-facing trust loop.
- **Decision:** `integrate` — reuse the pattern, but keep Truffles-specific contracts (`FACT/COLLECT/HANDOFF`, law/policy gates, simulation-safe side effects, owner-readable verdicts).
- **Rejected options:** developer-only playground without replay; canned demo with pre-written answers; shadow model path that differs from production runtime.
- **Open questions:** whether draft/live compare should block publish on day one or start as explicit preflight warning with fail-closed extension in Wave6.

## Root cause (mandatory)
- **Symptom:** After onboarding, an owner/admin still cannot directly challenge consultant behavior from Console and either trust it or prove that it is weak.
- **Minimal reproduction:**
  1. Log in as owner/admin and open `Business`.
  2. Observe there is no route to ask the consultant questions as if you were a client.
  3. Open `Knowledge` and `Settings`; they expose configuration and governance but not a safe conversational proof surface.
  4. Search backend routes for `/business/consultant-*` and find none.
- **Evidence to capture:** file inventory of business routes, OpenAPI business endpoints, simulation primitives in runtime, knowledge/learning artifacts, owner-admin e2e lane coverage.
- **Five Whys (or equivalent):**
  1. Why can the owner not validate consultant quality directly? Because no owner-facing conversational verification route exists in Console.
  2. Why is trust still weak after onboarding? Because current business surfaces explain health/settings but do not let the owner pressure-test actual answers.
  3. Why would a future ad hoc solution be risky? Because runtime simulation exists only as lower-level metadata; without a first-class contract, it is easy to build a route that leaks real side effects or fake behavior.
  4. Why would even a working chat still be insufficient? Because owners need verdicts, explanations, weak-spot capture, and before/after compare — not just raw replies.
  5. Why does this deserve a full program instead of one feature PR? Because the requirement spans IA, runtime safety, explainability, feedback capture, compare/replay, and rollout proof.
- **Root cause statement:** Truffles has runtime ingredients for safe simulation and internal quality loops, but lacks a business-first Console program that turns them into owner-facing, trust-building, failure-transparent product behavior.
- **Fix mechanism:** deliver a bounded multi-wave program: route/contract foundation, safe simulation kernel, owner-readable chat + verdicts, stress scenarios, weak-spot capture/remediation loop, draft/live compare, and a closeout lane with deterministic + visual proof.

## Reuse-first plan (mandatory)
- **Internal reuse:** `ConsoleShell` owner/admin navigation, `businessApi`, owner/admin business cards/patterns, `ChatInterface` composition patterns, runtime simulation context in `state_service.py`, outbox simulation suppression, `knowledge_backlog`, `learning_candidates`, `console_owner_admin.py` service extraction direction.
- **External reuse:** Dialogflow CX reference pattern for simulator/test-case/replay; Microsoft HAX guidance for explanation and expectation-setting; official eval and rollout references used in child waves.
- **Why not reinvent the wheel:** the difficult part is not rendering a chat box; it is keeping production-equivalent semantics, honest limitations, replayability, and no-side-effect guarantees without creating another brain.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `doc_only`
- **Doc touch budget (files):** `12`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** this block is the program contract. It should not ship code; it should lock sequence, invariants, and quality gates before implementation starts.

## Invariant
- Owner-facing verification must use the same consultant runtime semantics as production; no fake answers or alternate decision path.
- The product contract stays `FACT/COLLECT/HANDOFF`; simulation may preview outcomes but cannot bypass LAW/policy boundaries.
- Escalation remains first-class and is shown as correct behavior when appropriate, not as a failure.
- Any owner-detected weak spot must become durable product evidence, not a forgotten complaint.
- Owner/admin API growth must move toward extraction/service boundaries, not back into `console.py` sprawl.

## Scope
- Define the full initiative, its waves, sequencing, checks, evidence, and release discipline.
- Create child Task Packages for Waves 1-6 and a closeout block.
- Synchronize session and doc inventory so future agents can pick up any wave with zero context.

## Out of scope
- Implementing the route itself in this block.
- Rewriting consultant core or current owner/admin pages.
- Bypassing existing knowledge publish/preflight rules.
- Softening quality gates because the feature is business-facing.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave1-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave2-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave3-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave4-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave5-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave6-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-closeout-a920.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-13-owner-consultant-verification-program-a920.md`
- `STRUCTURE.md`
- `STATE.md`

## Program block map (atomic queue)

| Business block | Implementation block ID | Depends on | Expected outcome |
| --- | --- | --- | --- |
| B01 Owner trust entrypoint + IA foundation | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE1-A920` | this program TP | owner/admin can open a dedicated route and see bounded product expectations instead of technical setup pages |
| B02 Safe simulation session kernel | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE2-A920` | Wave1 | Console can create and run consultant test sessions through the real runtime with zero real side effects |
| B03 Owner-readable chat + verdict/explainability | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE3-A920` | Wave2 | owner can ask as a client or as a skeptic and understand what happened without trace jargon |
| B04 Stress scenarios + scenario library + summary | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE4-A920` | Wave3 | owner can quickly run difficult scenarios and get a summary instead of typing everything from scratch |
| B05 Weak-spot capture + remediation loop | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE5-A920` | Wave4 | bad answers become tracked findings with statuses and links into knowledge/learning remediation |
| B06 Draft/live compare + readiness gate | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE6-A920` | Wave5 | owner can compare current vs draft behavior and see launch readiness before publish |
| B07 Deterministic closeout + rollout proof | `CONSOLE-OWNER-CONSULTANT-VERIFICATION-CLOSEOUT-A920` | Wave6 | feature is shipped behind a safe rollout plan with proof, screenshots, and post-merge monitoring |

## Git / worktree
- `Branch`: `feat/2026-03-13-owner-consultant-verification-program-a920`
- `Worktree path`: `/home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920`
- `Base ref`: `origin/main`
- `Merge policy`: doc-only planning branch may merge as one docs PR or fast-forward docs handoff after Brain review; implementation waves must use their own bounded branches/worktrees
- `Cleanup`: Brain / Top Architect after merge

## Plan (1..N)
1. Lock the product contract and open backlog items for the missing trust/simulation/feedback/compare slices.
2. Create Wave1 foundation TP with route, schema, feature-flag, and extraction discipline.
3. Create Wave2 kernel TP for safe simulation sessions and no-side-effect guarantees.
4. Create Wave3 and Wave4 TPs for owner chat, verdicts, and difficult scenario execution.
5. Create Wave5 and Wave6 TPs for weak-spot remediation loop and draft/live compare.
6. Create closeout TP for deterministic proof, rollout, post-merge monitoring, and doc sync.
7. Register session/doc inventory so the next agent can execute Wave1 without reconstructing context.

## DoD
- Master TP exists with explicit program block map and invariants.
- Child TPs exist for Waves 1-6 and closeout.
- Backlog items `UX-39..UX-43` are recorded with concrete evidence and `Open` status.
- Session log and index point to this program so future work can resume without hidden context.
- `STRUCTURE.md` and `STATE.md` acknowledge the new planning artifacts.

## Checks
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'CONSOLE-OWNER-CONSULTANT-VERIFICATION' docs/TASK_PACKAGES`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'UX-39|UX-40|UX-41|UX-42|UX-43' docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && python3 - <<'PY2'
from pathlib import Path
for path in [Path('docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md')]:
    assert path.exists(), path
print('program tp: OK')
PY2`

## Evidence
- Program TP + child TP files in `docs/TASK_PACKAGES/`
- Backlog entries in `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- Session artifacts in `docs/SESSIONS/SESSION-2026-03-13-owner-consultant-verification-program-a920.md` and `docs/SESSION_INDEX.md`
- Canon inventory updates in `STRUCTURE.md` and `STATE.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this planning block
- **Fail-fast / scenario lock:** planning only; no code/evals permitted
- **Stop condition:** if scope expands beyond Waves 1-6 + closeout, stop and split into a separate program TP instead of bloating this one
- **Escalation path:** Top Architect / Brain decide whether new business goals become a second program

## Release safety (mandatory for non-doc changes)
- **Strategy:** planning-only block; no runtime rollout permitted from this TP
- **Go/no-go signals:** all child TPs exist, backlog items are recorded, and implementation cannot start without selecting the next bounded wave
- **Rollback:** revert docs or drop the planning branch; no runtime rollback path needed because no code ships here
- **Post-release monitoring window:** n/a for this planning block; monitoring is defined in child waves and closeout

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
  - `STRUCTURE.md`
- `Drift closeout rule`:
  - each wave must update docs in the same block when contracts/routes/copy change; if not possible, record explicit `GAP` with owner and next wave

## Rollback
- Revert this docs-only branch or cherry-pick only accepted planning docs.
- Do not execute any implementation wave until Brain/Top Architect accepts the program sequence.

## No-go
- Starting implementation from Wave3+ before Wave1 and Wave2 are green.
- Building a fake demo route that bypasses production consultant logic.
- Treating owner-detected failures as support notes instead of tracked product evidence.
- Expanding `console.py` with large new consultant verification orchestration instead of extracting service helpers.

## Risks/Blockers
- `UX-20` owner/admin maintainability debt will worsen if Wave1 does not enforce service extraction.
- Existing simulation primitives may hide edge cases if Wave2 does not test no-side-effect guarantees against outbox/handover/booking paths.
- Pressure to make the feature look good may tempt silent filtering of bad outcomes; this is explicitly forbidden.
- Draft/live compare may reveal gaps in current knowledge preflight/publish contract and require follow-up.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no code implementation; no concrete data model yet for consultant verification sessions/findings; no new OpenAPI schemas yet.
- `Why not in this block`: this is the canon/planning lock block only.
- `Risk if deferred`: low for planning, but implementation must not start from an ambiguous program.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave1-a920.md`, `TP-2026-03-13-owner-consultant-verification-wave2-a920.md`, `TP-2026-03-13-owner-consultant-verification-wave3-a920.md`, `TP-2026-03-13-owner-consultant-verification-wave4-a920.md`, `TP-2026-03-13-owner-consultant-verification-wave5-a920.md`, `TP-2026-03-13-owner-consultant-verification-wave6-a920.md`, `TP-2026-03-13-owner-consultant-verification-closeout-a920.md`
- `Expiry/trigger to stop deferral`: no implementation branch may start until Wave1 TP is accepted as the deterministic next block.

## Next-block contract (mandatory)
- `Next block objective`: ship Wave1 route + IA + service-boundary foundation for owner consultant verification.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'consultant-verification' console-web/src/app/business console-web/src/components/ConsoleShell.tsx truffles-api/app/routers/console.py contracts/console_api/openapi.v1.yaml`
- `Blocked-by conditions`: Brain/Top Architect must accept the Wave1 scope and the UX backlog IDs opened by this program.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave1-a920.md`
- `Do not touch`: consultant core behavior outside explicit simulation-safe contract; no direct DB edits outside migrations in future waves
- `Open risks`: owner-facing honesty vs marketing pressure; `console.py` maintainability; side-effect suppression completeness
- `First command to verify`: `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'UX-39|UX-40|UX-41|UX-42|UX-43|CONSOLE-OWNER-CONSULTANT-VERIFICATION' docs`
