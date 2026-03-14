# TP-2026-03-13-owner-consultant-verification-wave6-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE6-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE5-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-CLOSEOUT-A920`

## Название/цель
Добавить `live vs draft` compare и readiness gate для owner consultant verification: владелец бизнеса должен видеть, как текущий опубликованный консультант отвечает сейчас, как будет отвечать после изменений, и достаточно ли этого, чтобы публиковать знания/настройки без слепой веры.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave5-a920.md`
- `CA_ID`: `UX-42`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_knowledge_preflight.py`
  - `truffles-api/app/services/console_consultant_verification.py`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'knowledge/current|knowledge/validate|knowledge/publish|knowledge/history|knowledge/rollback' truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx contracts/console_api/openapi.v1.yaml`
  - `cd /home/zhan/truffles-main && rg -n 'console_knowledge_preflight|preflight' truffles-api/app/services/console_knowledge_preflight.py truffles-api/tests`
  - `cd /home/zhan/truffles-main && rg -n 'simulation|source_mode|draft|live' truffles-api/app console-web/src/app/business/consultant-verification`
- `FACT findings`:
  - Knowledge lifecycle and preflight gates already exist in Console.
  - There is still no owner-facing compare route or `draft/live` explanation flow.
  - Existing publish safety focuses on validation freshness, not on owner-visible conversational proof.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google/workbook canarying releases compare baseline candidate`
- **Date/time (local):** `2026-03-13 18:25, Asia/Almaty`
- **Why this query is precise:** Wave6 is effectively a canary/compare problem for consultant behavior: baseline (`live`) vs candidate (`draft`) under fixed prompts and findings.
- **Sources opened (from this query):**
  - `The Site Reliability Workbook — Canarying Releases` — `https://sre.google/workbook/canarying-releases/`
  - `The Site Reliability Workbook — Monitoring Distributed Systems` — `https://sre.google/workbook/monitoring-distributed-systems/`
- **Existing solutions found:** compare a candidate against a fixed baseline, use explicit go/no-go signals, and keep rollback/proof paths first-class.
- **Decision:** `integrate` — run the same consultant verification prompts/findings against both `live` and `draft`, display deltas, and only mark readiness green when compare signals pass.
- **Rejected options:** draft preview without baseline comparison; publish based on owner gut feel; replacing existing knowledge preflight instead of extending it.
- **Open questions:** whether compare-ready failures should hard-block publish in Wave6 or first appear as fail-closed warning with explicit override token owned by Top Architect.

## Root cause (mandatory)
- **Symptom:** Owners may see current behavior, but still cannot trust that a draft actually improves it before publish.
- **Minimal reproduction:**
  1. Open `Knowledge` and observe validate/publish flow.
  2. Open business surfaces and observe no draft/live consultant compare.
  3. Observe there is no retest loop for previously flagged findings.
- **Evidence to capture:** current knowledge lifecycle routes, absence of compare endpoints, no finding retest contract.
- **Five Whys (or equivalent):**
  1. Why is current testing incomplete? Because it shows only one version of behavior at a time.
  2. Why is compare mandatory? Because owners need proof that changes improved or at least did not regress important scenarios.
  3. Why can’t publish validation alone solve this? Because schema/pack validation does not prove conversational outcome quality.
  4. Why must flagged findings be retested? Because “fixed” needs evidence, not a promise.
  5. Why is this a separate wave? Because version comparison, readiness scoring, and publish interaction are a release-governance problem, not just chat UI.
- **Root cause statement:** the product lacks a release-grade compare loop that turns owner verification into an evidence-backed `live vs draft` decision before publish.
- **Fix mechanism:** add compare endpoints and readiness scoring over fixed prompts/findings, surface deltas in owner language, and connect the result to knowledge preflight/publish decisions.

## Reuse-first plan (mandatory)
- **Internal reuse:** knowledge current/validate/publish/preflight routes, Wave2 session kernel, Wave5 findings and retest list.
- **External reuse:** Google SRE canarying principles for baseline-vs-candidate and explicit go/no-go decisions.
- **Why not reinvent the wheel:** the existing knowledge workflow already owns draft/live lifecycle; we only need to add owner-facing behavioral proof over it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** Wave6 is a behavior compare/release-governance layer and must ship code, tests, and docs together.

## Invariant
- Draft/live compare must use fixed prompts/findings and the same simulation kernel.
- Compare results must be explicit about regressions, not just improvements.
- Publish safety cannot be weakened to make the feature feel nicer.
- Owners must see honest `ready/not ready/needs data` output.

## Scope
- Add compare endpoints and payloads for running selected prompts/findings against `live` and `draft`.
- Add UI diff view and readiness scorecard.
- Add retest action for Wave5 findings.
- Extend knowledge preflight or publish safety to consume compare readiness as part of the go/no-go signal.

## Out of scope
- Fleet-wide rollout analytics.
- Automatic draft fixing.
- Cross-tenant scenario sharing.

## Touch-list
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/console_knowledge_preflight.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_knowledge_preflight.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`

## Plan (1..N)
1. Define fixed compare input contract (`prompt/finding/scenario`, `live`, `draft`).
2. Implement compare service and readiness aggregation.
3. Add UI diff and readiness cards with explicit regressions.
4. Add retest flow for Wave5 findings.
5. Connect compare readiness to knowledge preflight/publish surface.
6. Add deterministic tests and targeted e2e coverage.

## DoD
- Owner can run the same prompt/finding against `live` and `draft`.
- UI shows side-by-side or delta summary with explicit regression markers.
- Findings can be retested and status can move to `retested`/`fixed` with evidence.
- Knowledge preflight/publish surface reflects compare readiness.
- Deterministic tests prove baseline/candidate compare semantics.

## Checks
- `cd truffles-api && pytest -q tests/test_console_consultant_verification_api.py -k compare`
- `cd truffles-api && pytest -q tests/test_console_knowledge_preflight.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/knowledge/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification compare"`

## Evidence
- sample compare payload/result for `live` vs `draft`
- screenshot of readiness scorecard and regression marker
- test outputs proving compare and preflight linkage
- retest evidence for one prior finding

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** use one fixed prompt and one fixed finding first; only expand after diff semantics are stable
- **Stop condition:** any ambiguous compare result or publish-gate inconsistency after three iterations -> stop and re-open RCA
- **Escalation path:** Top Architect decides hard-block vs explicit override if compare readiness reveals product-policy conflict

## Release safety (mandatory for non-doc changes)
- **Strategy:** one-client canary + owner/admin flag; compare gate initially warning+fail-closed for internal clients, then broaden
- **Go/no-go signals:** compare outputs deterministic; regressions visible; publish surface honors readiness state; no bypass of existing preflight law/policy gates
- **Rollback:** disable compare UI/gate integration and keep prior knowledge workflow intact
- **Post-release monitoring window:** 48h review of compare runs, publish attempts, and false-regression reports

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/runbooks/*` if preflight/publish SOP changes
  - `STATE.md`
- `Drift closeout rule`:
  - compare readiness and publish interaction must be documented in the same block

## Rollback
- Disable compare/readiness flag and revert preflight integration if needed.
- Keep prior Wave1-5 route usable in single-version mode.

## No-go
- Comparing different prompt sets between `live` and `draft`.
- Hiding regressions behind aggregated green statuses.
- Weakening existing knowledge publish safeguards for convenience.

## Risks/Blockers
- Draft source resolution can be tricky if current knowledge lifecycle does not expose the needed snapshot cleanly.
- Compare UI can become too complex if delta language is not strictly business-readable.
- Preflight/publish interaction may surface previously hidden workflow debt.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no final rollout proof, visual audit, or post-merge monitoring lane yet.
- `Why not in this block`: Wave6 finishes feature completeness; closeout is separate.
- `Risk if deferred`: medium; the feature can be functionally complete but not yet proven/released safely.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-closeout-a920.md`
- `Expiry/trigger to stop deferral`: do not remove feature gate or call the surface complete before closeout proof is green.

## Next-block contract (mandatory)
- `Next block objective`: deterministic closeout, visual proof, rollout, and post-merge monitoring.
- `First deterministic check command`: `cd /home/zhan/truffles-main && sed -n '1,260p' console-web/e2e/owner-admin-business.spec.ts`
- `Blocked-by conditions`: Wave6 compare/retest/readiness flow must be green.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py`
- `Do not touch`: existing knowledge law/policy gates without explicit proof
- `Open risks`: compare determinism, draft source selection, publish integration semantics
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'compare|ready|draft|live|retest' console-web/src/app/business/consultant-verification truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx`
