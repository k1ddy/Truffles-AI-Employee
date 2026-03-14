# TP-2026-03-13-owner-consultant-verification-closeout-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-CLOSEOUT-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE6-A920`
- `UNLOCKS`: owner/admin release decision for `Проверка консультанта`

## Название/цель
Закрыть initiative только через доказательство: deterministic API + UI proof, visual audit, one-client canary, post-merge monitoring, and explicit go/no-go decision for owner/admin consultant verification.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave6-a920.md`
- `CA_ID`: `UX-39`, `UX-40`, `UX-41`, `UX-42`, `UX-43`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - all Wave1-6 touched files
  - `console-web/e2e/owner-admin-business.spec.ts`
  - `truffles-api/tests/test_console_consultant_verification_api.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `truffles-api/tests/test_console_knowledge_preflight.py`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'consultant verification|compare|finding|scenario|simulation' console-web/src truffles-api/app contracts/console_api/openapi.v1.yaml`
  - `cd /home/zhan/truffles-main && sed -n '1,260p' console-web/e2e/owner-admin-business.spec.ts`
  - `cd /home/zhan/truffles-main && rg -n 'consultant_verification' truffles-api/tests console-web/e2e`
- `FACT findings`:
  - Closeout cannot rely on happy-path screenshots alone; the feature spans runtime safety, owner UX, remediation loop, and release gating.
  - Existing owner-admin lane is the natural E2E home; a dedicated consultant verification spec may still be justified if `owner-admin-business.spec.ts` becomes overloaded.
  - Rollout must stay gated until one-client canary and post-merge monitoring confirm no regressions in auth, metrics, or knowledge publish flow.
- `Detected drift (docs vs code)`: to be re-evaluated at closeout; any mismatch is a blocker.

## One web search (mandatory before implementation)
- **Query (exact):** `site:playwright.dev/docs best practices locators isolation avoid implementation details`
- **Date/time (local):** `2026-03-13 18:29, Asia/Almaty`
- **Why this query is precise:** closeout depends on stable owner-admin E2E coverage with business-readable assertions rather than brittle DOM-detail tests.
- **Sources opened (from this query):**
  - `Playwright Best Practices` — `https://playwright.dev/docs/best-practices`
  - `Playwright Locators` — `https://playwright.dev/docs/locators`
- **Existing solutions found:** test user-visible behavior, isolate scenarios, and keep selectors anchored to stable product semantics.
- **Decision:** `integrate` — closeout tests should assert route visibility, verdict states, findings/compare behavior, and role gates via stable test ids and business text, not internal implementation details.
- **Rejected options:** screenshot-only acceptance; giant end-to-end mega test without isolation; text-diff-only checks of assistant replies.
- **Open questions:** whether to keep consultant verification in `owner-admin-business.spec.ts` or split into `owner-admin-consultant-verification.spec.ts` during closeout if scope becomes too large.

## Root cause (mandatory)
- **Symptom:** A complex business-facing feature can look complete while still being unsafe, brittle, or under-proven.
- **Minimal reproduction:**
  1. Ship Waves 1-6 without a dedicated closeout block.
  2. Observe there would be no explicit rollout/canary/post-merge proof contract.
- **Evidence to capture:** deterministic suites, visual captures, E2E, canary notes, monitoring snapshots, docs sync.
- **Five Whys (or equivalent):**
  1. Why is closeout separate? Because product completeness is not the same as release proof.
  2. Why can’t targeted unit tests alone close it? Because owner trust is a workflow and IA problem too.
  3. Why is canary mandatory? Because this route touches business navigation, simulation runtime, knowledge workflow, and owner expectations.
  4. Why do we need post-merge monitoring? Because silent regressions in auth/metrics/publish paths may appear only under real usage.
  5. Why is visual audit required? Because trust surfaces can regress through layout/copy overload even when APIs pass.
- **Root cause statement:** without a dedicated closeout block, the initiative would risk shipping on partial confidence and would violate Truffles release-safety discipline.
- **Fix mechanism:** run deterministic contract proof, owner-admin E2E, visual inspections, canary rollout, post-merge monitoring, and explicit go/no-go documentation before removing the feature gate.

## Reuse-first plan (mandatory)
- **Internal reuse:** owner-admin Playwright lane, existing build/lint/openapi flows, current runbook patterns for owner/admin post-merge loops.
- **External reuse:** Playwright best practices for resilient user-facing tests.
- **Why not reinvent the wheel:** closeout needs disciplined proof, not a new testing framework.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `30`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** closeout reopened bounded auth/runtime/test blockers in the real proof path, so this block must allow implementation-scale fixes while still forbidding broad refactors.

## Invariant
- No feature-gate removal without green deterministic + UI + canary evidence.
- No downgrade of publish safety or simulation safety to make closeout pass.
- If any reopened failure family appears, closeout fails closed and a new wave TP is created.

## Scope
- Run all deterministic checks for Waves 1-6.
- Execute owner-admin E2E lane and visual audit.
- Define canary/go-no-go/rollback notes and collect post-merge monitoring evidence.
- Sync docs and decide `go` vs `blocked`.

## Out of scope
- New feature work beyond blocker fixes.
- Large refactors unrelated to closeout.
- Broad marketing content around the feature.

## Touch-list
- `console-web/e2e/owner-admin-business.spec.ts` or `console-web/e2e/owner-admin-consultant-verification.spec.ts` (if split is justified)
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_knowledge_preflight.py`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/*`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Run deterministic backend/API/OpenAPI checks.
2. Run owner-admin E2E lane for consultant verification.
3. Capture visual evidence at desktop widths and one mobile-safe width.
4. Run one-client canary and collect post-merge monitoring notes.
5. Decide go/no-go and document any reopened failure families.
6. Sync docs/backlog/state.

## DoD
- Deterministic backend/API checks are green.
- Owner-admin E2E lane for consultant verification is green.
- Visual audit confirms readable trust surface and no technical-jargon regression.
- Canary and post-merge monitoring are recorded.
- `STATE.md` reflects the explicit go/no-go decision with evidence.

## Checks
- `cd truffles-api && pytest -q tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py tests/test_console_knowledge_preflight.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/knowledge/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification"`

## Evidence
- backend/API test outputs
- Playwright output
- screenshots at `390px`, `1024px`, `1280px`, `1440px`
- canary notes and post-merge monitoring snapshot
- final `STATE.md` entry with go/no-go decision

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** first run deterministic only, second run adds canary/post-merge evidence after blockers are resolved
- **Stop condition:** any reopened failure family or red canary signal -> stop and open a new bounded wave TP
- **Escalation path:** Top Architect owns final go/no-go

## Release safety (mandatory for non-doc changes)
- **Strategy:** one-client canary under feature gate, then phased owner/admin rollout
- **Go/no-go signals:** deterministic lanes green; E2E green; visual audit clean; no unexpected simulation side effects; no publish-gate regression
- **Rollback:** disable feature gate, remove nav visibility, keep evidence/finding data intact
- **Post-release monitoring window:** 72h with daily review of route usage, findings volume, compare usage, and error signals

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
  - `STRUCTURE.md`
- `Drift closeout rule`:
  - all route names, endpoint paths, and release status must be reflected in docs before closure

## Rollback
- Hide route via feature gate and revert canary exposure.
- Preserve findings/session evidence for future reactivation.

## No-go
- Declaring release-ready based only on local screenshots.
- Removing feature gate before canary/monitoring evidence exists.
- Ignoring reopened failure families because core checks are green.

## Risks/Blockers
- E2E lane may become too broad and require split for maintainability.
- Visual trust issues can survive deterministic green checks.
- Canary may expose auth/context-selection edge cases not visible locally.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none intentionally; any remaining issue must become a new bounded follow-up TP.
- `Why not in this block`: closeout should either pass or explicitly fail closed.
- `Risk if deferred`: high — shipping without closeout proof breaks release discipline.
- `Linked follow-up Task Package(s)`: `none if green`; otherwise a new bounded remediation TP opened from the first reopened failure family
- `Expiry/trigger to stop deferral`: immediate; no deferral allowed after closeout starts

## Next-block contract (mandatory)
- `Next block objective`: either merge-go with post-merge monitoring or open the first remediation TP from reopened failure family evidence.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'consultant verification' STATE.md docs/CONSOLE_GUIDE.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: Waves 1-6 must be complete.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `console-web/e2e/owner-admin-business.spec.ts`
- `Do not touch`: shipped contracts unless a blocker is proven
- `Open risks`: e2e maintainability, visual trust regressions, canary-only edge cases
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'consultant verification|compare|finding|scenario' console-web/e2e truffles-api/tests docs`
