# TP-2026-03-13-owner-consultant-verification-wave4-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE4-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE3-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE5-A920`

## Название/цель
Добавить owner-facing stress layer: готовые сложные сценарии, data-driven quick prompts, session summary и replay внутри consultant verification, чтобы владелец бизнеса мог не только писать вручную, но и быстро прогонять типовые «сломай систему» кейсы по своей нише.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave3-a920.md`
- `CA_ID`: `UX-39`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_consultant_verification.py`
  - `truffles-api/app/services/capabilities_service.py`
  - `truffles-api/app/routers/console.py` (`reference-packs` and related business routes)
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'reference-packs|onboarding-blueprints|capabilities' truffles-api/app/routers/console.py console-web/src/lib/api-client.ts`
  - `cd /home/zhan/truffles-main && rg -n 'scenario|eval_cases|EVAL' truffles-api/app docs console-web/src -g '*.py' -g '*.yaml' -g '*.md'`
  - `cd /home/zhan/truffles-main && rg -n 'consultant verification' console-web/src/app/business truffles-api/app/routers/console.py`
- `FACT findings`:
  - Domain/reference-pack and capabilities data already exist and should be the source of quick scenarios, not hardcoded strings in runtime core.
  - Existing eval/scenario assets live in consultant/knowledge space but are not exposed as owner-friendly stress presets.
  - There is no session summary or replay contract for owner-facing verification yet.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:platform.openai.com/docs evals best practices test cases rubrics`
- **Date/time (local):** `2026-03-13 18:17, Asia/Almaty`
- **Why this query is precise:** Wave4 needs scenario structure, coverage principles, and reusable stress prompts without turning the surface into a developer-only eval UI.
- **Sources opened (from this query):**
  - `OpenAI Evals guide` — `https://platform.openai.com/docs/guides/evals`
  - `OpenAI evaluations cookbook/docs entry` — `https://platform.openai.com/docs/guides/evals`
- **Existing solutions found:** reusable scenario sets, explicit pass/fail dimensions, and fixed prompts are useful only when they stay close to user-facing intents and can be replayed consistently.
- **Decision:** `integrate` — expose a business-readable scenario library and replay summary, while keeping the underlying cases data-driven from packs/capabilities rather than hardcoded branch logic.
- **Rejected options:** giant static list of canned prompts in React code; direct exposure of internal eval YAML; developer-only rubric language on the owner screen.
- **Open questions:** whether owner-saved scenarios should live in branch-scoped DB tables or be session-only in Wave4 and become durable in Wave5.

## Root cause (mandatory)
- **Symptom:** Manual chat alone is not enough for skeptical owners; they need fast structured ways to probe difficult scenarios.
- **Minimal reproduction:**
  1. Use the future Wave3 chat with no presets.
  2. Observe every difficult scenario must be typed and remembered manually.
  3. Observe no summary exists across the session to show what passed, what required handoff, and what looked weak.
- **Evidence to capture:** absence of scenario endpoints, existing pack/capability assets, owner feedback about difficult-case testing need.
- **Five Whys (or equivalent):**
  1. Why is manual chat insufficient? Because owners do not know every important stress scenario from scratch.
  2. Why can’t we hardcode a few prompts? Because pack/capability/domain differences belong in data, not core code.
  3. Why is summary necessary? Because owners want to know whether the session generally held up, not just read message by message.
  4. Why must replay start here? Because once a hard question is found, it must be rerunnable.
  5. Why is this a separate wave? Because scenario sourcing and summary/replay semantics are their own data/product problem.
- **Root cause statement:** the current product idea lacks a structured, repeatable stress-testing layer built from domain data and owner-facing summaries.
- **Fix mechanism:** add a data-driven scenario library, quick-run stress prompts, session summaries, and bounded replay actions over saved session turns.

## Reuse-first plan (mandatory)
- **Internal reuse:** `reference-packs`, capabilities, existing eval/scenario assets, Wave2 sessions, Wave3 verdict UI.
- **External reuse:** OpenAI evals guidance for reusable case structure and consistent replay.
- **Why not reinvent the wheel:** Truffles already has domain facts and eval thinking; Wave4’s job is to expose a business-readable layer over them, not invent new semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `7`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this wave spans API, data sourcing, and owner UI, but should remain bounded to scenarios/summary only.

## Invariant
- Scenario suggestions must be data-driven (`reference pack`, `capabilities`, or explicit scenario catalog), not semantic hardcode in core.
- Stress mode must not change consultant decision logic; it only changes what the owner chooses to ask.
- Session summary must be honest and count handoffs as a valid category, not auto-fail.

## Scope
- Add scenario catalog endpoint(s) or payloads for the owner route.
- Add quick scenario chips/cards and a replay action for a prior session or saved prompt set.
- Add session summary: count of confident answers, clarifications, correct handoffs, and suspected weak spots.
- Add domain-appropriate difficult prompts sourced from packs/capabilities/reference data.

## Out of scope
- Persistent issue statuses and remediation lifecycle.
- Draft/live compare.
- Mandatory publish blocking.

## Touch-list
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/*`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/capabilities_service.py` (read-only integration only if needed)
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `STATE.md`

## Plan (1..N)
1. Define scenario source hierarchy (`pack/reference/capability -> branch/session custom`).
2. Expose scenario list and replay-friendly payload contract.
3. Add quick scenario surface and stress prompt launchers.
4. Add session summary cards and replay CTA.
5. Prove that handoff/clarify/weak-spot categories summarize correctly.
6. Sync docs and targeted e2e coverage.

## DoD
- Owner sees scenario presets appropriate to current business context.
- Owner can launch a difficult scenario quickly without typing the whole prompt.
- Session summary renders category counts and recent weak turns.
- Replay can rerun a saved prompt or scenario set against the same session contract.
- No hardcoded domain branches are added to consultant core.

## Checks
- `cd truffles-api && pytest -q tests/test_console_consultant_verification_api.py -k 'scenario or replay or summary'`
- `cd console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification scenarios"`

## Evidence
- screenshot of scenario library and summary panel
- API payload showing scenario catalog source
- targeted tests and replay evidence for one difficult scenario

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** use one deterministic scenario fixture per lane before broader catalog checks
- **Stop condition:** if scenario suggestions require core hardcode or violate pack-agnostic rules, stop and redesign data source contract
- **Escalation path:** Brain / Top Architect must approve any new source of scenario truth

## Release safety (mandatory for non-doc changes)
- **Strategy:** keep scenario library behind the same owner/admin feature gate and one-client canary
- **Go/no-go signals:** scenario source payload valid; summary counts deterministic; replay does not mutate session truth unexpectedly
- **Rollback:** hide scenario library UI and replay actions while retaining Wave3 chat
- **Post-release monitoring window:** 24h review of scenario usage vs manual usage and summary correctness

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
- `Drift closeout rule`:
  - scenario source contract must be documented together with replay semantics

## Rollback
- Disable scenario/replay UI and retain plain chat flow.
- Revert scenario endpoints if source hierarchy is wrong.

## No-go
- Hardcoding niche-specific prompts in runtime core.
- Presenting scenario summary as pass/fail without honest category breakdown.
- Letting replay mutate previously captured evidence.

## Risks/Blockers
- Scenario catalog can drift from actual business packs if not sourced carefully.
- Replay semantics can become ambiguous if `source_mode`/session versioning is weak.
- Too many presets can overload the page and reduce clarity.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no persistent finding ownership/statuses; no draft/live compare.
- `Why not in this block`: Wave4 focuses on structured owner testing, not remediation or compare.
- `Risk if deferred`: medium; owners can find issues faster but still cannot track them to closure.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave5-a920.md`
- `Expiry/trigger to stop deferral`: if owners start finding weak spots, Wave5 must follow immediately to avoid losing them.

## Next-block contract (mandatory)
- `Next block objective`: make bad turns durable findings with remediation lifecycle and failure-family grouping.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'knowledge_backlog|learning_candidate|failure family|learning candidates' truffles-api/app console-web/src docs`
- `Blocked-by conditions`: Wave4 scenario catalog and summary must be green.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py`
- `Do not touch`: consultant semantic routing; keep scenario additions data-driven
- `Open risks`: scenario source drift, replay ambiguity, UI overload
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'scenario|replay|summary' console-web/src/app/business/consultant-verification truffles-api/app/routers/console.py`
