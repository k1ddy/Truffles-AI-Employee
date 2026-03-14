# TP-2026-03-13-owner-consultant-verification-wave5-a920

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE5-A920`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE4-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-WAVE6-A920`

## Название/цель
Сделать owner-detected weak spots first-class product evidence: любой turn, который владелец считает плохим или подозрительным, должен сохраняться как finding, группироваться по failure family/root cause, попадать в remediation loop и возвращаться владельцу с понятным статусом (`new/in review/needs data/fixed/retested`).

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave4-a920.md`
- `CA_ID`: `UX-41`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/learning_service.py`
  - `console-web/src/app/knowledge/page.tsx`
  - `docs/CONSULTANT_CODEMAP.md`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'knowledge_backlog' truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/admin.py docs/CONSULTANT_CODEMAP.md`
  - `cd /home/zhan/truffles-main && rg -n 'learning candidates|learning_candidate|approve_learning_candidate' truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx`
  - `cd /home/zhan/truffles-main && rg -n 'failure family|failure families' docs/TASK_PACKAGES docs`
  - `cd /home/zhan/truffles-main && rg -n 'consultant verification|finding|issue status' console-web/src truffles-api/app`
- `FACT findings`:
  - `knowledge_backlog` already captures missing facts from runtime misses.
  - `learning_candidates` already expose owner/admin approval workflow inside `Knowledge`.
  - Failure-family language already exists in quality canon, but it is not connected to owner-detected bad turns.
  - There is no owner-facing finding object or status lifecycle tied to consultant verification sessions.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google/workbook alerting on slos actionable signals noise reduction`
- **Date/time (local):** `2026-03-13 18:21, Asia/Almaty`
- **Why this query is precise:** Wave5 must avoid noisy bug reporting and instead create actionable, clustered signals that drive remediation.
- **Sources opened (from this query):**
  - `The Site Reliability Workbook — Alerting on SLOs` — `https://sre.google/workbook/alerting-on-slos/`
  - `The Site Reliability Workbook — Monitoring` — `https://sre.google/workbook/monitoring/`
- **Existing solutions found:** actionable signal beats noisy event lists; clustering by symptom family and linking to concrete next actions is essential.
- **Decision:** `integrate` — findings will be deduped/clustered by failure family and surfaced with actionable statuses rather than raw turn dumps.
- **Rejected options:** plain unstructured “report bug” inbox; one row per flagged turn without grouping; support-ticket-only flow disconnected from knowledge/learning pipelines.
- **Open questions:** whether the first persistence layer should reuse `knowledge_backlog` with extended metadata or add a dedicated `consultant_verification_findings` table that links to backlog/learning objects.

## Root cause (mandatory)
- **Symptom:** The owner can potentially find a bad answer, but today there is no durable, owner-visible path that turns that finding into product remediation.
- **Minimal reproduction:**
  1. Inspect knowledge backlog and learning candidates.
  2. Observe they are fed from runtime/admin flows, not from owner verification chat.
  3. Observe there is no finding status model for owner verification.
- **Evidence to capture:** backlog table path, learning candidate route/UI, failure-family canon refs, absence of consultant verification findings.
- **Five Whys (or equivalent):**
  1. Why would owner trust still be weak after Waves 3-4? Because even found problems can disappear into human memory.
  2. Why can’t we just dump flagged turns into knowledge backlog? Because owners need statuses and product triage, not raw fact-miss rows only.
  3. Why is grouping necessary? Because repeated weak turns should become one failure family, not noisy duplicates.
  4. Why must owner see status? Because transparency about remediation is part of trust.
  5. Why is this a separate wave? Because it crosses product workflow, data model, knowledge pipeline, and owner-facing status UI.
- **Root cause statement:** Truffles lacks a first-class bridge from owner-detected bad consultant turns to clustered remediation evidence with visible lifecycle state.
- **Fix mechanism:** add consultant verification findings, family clustering, linkage into knowledge/learning queues, and owner-visible status updates.

## Reuse-first plan (mandatory)
- **Internal reuse:** `knowledge_backlog`, `learning_candidates`, existing quality `failure family` language and evidence discipline, owner/admin knowledge UI patterns.
- **External reuse:** SRE actionable-alert principles for dedupe, severity, and state transitions.
- **Why not reinvent the wheel:** the platform already has remediation surfaces; Wave5 should connect them instead of creating a disconnected bug tracker.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** Wave5 is a workflow/data-model integration block with clear owner-facing consequences.

## Invariant
- A flagged turn cannot be silently dropped.
- Repeated findings should cluster into failure families when evidence matches.
- Owner-facing statuses must stay business-readable and not expose internal queue chaos.
- Existing knowledge/learning moderation rules remain intact; owner flagging does not auto-publish anything.

## Scope
- Add finding entity/contract, capture endpoint, list endpoint, and status model.
- Add linkage from finding -> session/turn -> failure family -> knowledge backlog/learning candidate when applicable.
- Add owner-facing finding panel/list with statuses and last update.
- Add moderator/admin transition paths as needed for triage and closure.

## Out of scope
- Draft/live compare.
- Full automated issue fixing.
- Cross-tenant aggregation or fleet-level analytics.

## Touch-list
- `truffles-api/migrations/*consultant_verification_findings*.sql` (new if needed)
- `truffles-api/app/models/*` (new or extended)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/learning_service.py`
- `truffles-api/app/routers/webhook/decision.py` (only if backlog linkage requires shared helper extraction)
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_learning_service.py`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/knowledge/page.tsx` (only if linkage surfacing is needed)
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`

## Plan (1..N)
1. Define finding schema, lifecycle statuses, and family key contract.
2. Implement capture/list/status APIs and extracted service helpers.
3. Link findings to existing knowledge backlog / learning candidate flow where appropriate.
4. Add owner-facing findings list and per-turn flag action.
5. Add deterministic tests for dedupe, status transitions, and linkage.
6. Sync docs and targeted e2e.

## DoD
- Owner can flag a specific consultant turn as problematic.
- The finding persists with a visible status.
- Repeated equivalent findings cluster into a family key rather than duplicating indefinitely.
- Findings can link into knowledge/learning remediation where appropriate.
- Owner-facing surface shows last update and current state.

## Checks
- `cd truffles-api && pytest -q tests/test_console_consultant_verification_api.py -k finding`
- `cd truffles-api && pytest -q tests/test_learning_service.py`
- `cd console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/knowledge/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep "consultant verification findings"`

## Evidence
- sample finding payload + stored family key
- screenshot of owner finding status list
- tests proving dedupe/status/linkage
- one trace from flagged turn to remediation object

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** target one finding family fixture first, then one cross-link fixture to learning/knowledge
- **Stop condition:** if capture cannot stay actionable/deduped after two iterations, stop and revisit family-key design
- **Escalation path:** Top Architect approves any schema reuse vs new-table decision

## Release safety (mandatory for non-doc changes)
- **Strategy:** same owner/admin flag gate, canary on internal client first
- **Go/no-go signals:** flagged turns persist, dedupe works, no accidental auto-learning, owner statuses visible
- **Rollback:** hide flag action and keep prior sessions read-only while preserving captured evidence
- **Post-release monitoring window:** 48h review of finding volume, duplicate rate, and status update latency

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSULTANT_CODEMAP.md`
  - `STATE.md`
- `Drift closeout rule`:
  - finding statuses and remediation linkage must match the shipped contract in docs

## Rollback
- Disable finding capture UI and APIs while preserving read access to already captured evidence if needed.
- Revert linkage helpers if they create noisy or unsafe automation.

## No-go
- Treating owner findings as ephemeral UI-only comments.
- Auto-publishing knowledge updates from flagged turns.
- Duplicating the same weak spot as dozens of ungrouped rows.

## Risks/Blockers
- Dedupe/family key may be too coarse or too granular.
- Owner-visible statuses may diverge from internal triage states if not carefully mapped.
- Linking into learning/knowledge flows can create moderation confusion if ownership is unclear.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no draft/live compare and readiness gate yet.
- `Why not in this block`: Wave5 is remediation capture, not change comparison.
- `Risk if deferred`: medium; issues become trackable, but owners still cannot verify whether a draft actually fixed them.
- `Linked follow-up Task Package(s)`: `TP-2026-03-13-owner-consultant-verification-wave6-a920.md`
- `Expiry/trigger to stop deferral`: once findings exist, compare/retest must follow so “fixed” can be proven.

## Next-block contract (mandatory)
- `Next block objective`: compare `live` vs `draft`, retest findings, and expose readiness before publish.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n 'knowledge/current|knowledge/validate|knowledge/publish|console_knowledge_preflight' truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx truffles-api/app/services/console_knowledge_preflight.py`
- `Blocked-by conditions`: finding capture + status lifecycle must be green.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py`
- `Do not touch`: knowledge publish moderation contract unless explicitly required
- `Open risks`: family-key design, owner-visible status mapping, linkage noise
- `First command to verify`: `cd /home/zhan/truffles-main && rg -n 'knowledge_backlog|learning candidates|finding|family' truffles-api/app console-web/src/app/business/consultant-verification`
