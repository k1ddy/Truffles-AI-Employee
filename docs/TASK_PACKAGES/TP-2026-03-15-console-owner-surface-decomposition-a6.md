# TP-2026-03-15-console-owner-surface-decomposition-a6

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-SURFACE-DECOMPOSITION-A6`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-SCOPE-GATE-UNIFICATION-A5`
- `DEPENDS_ON`: `CONSOLE-OWNER-SCOPE-GATE-UNIFICATION-A5`
- `UNLOCKS`: simpler owner-first `Knowledge` / `Проверка консультанта` paths where advanced diagnostics no longer dominate the primary workflow

## Название/цель
Сделать первый реальный срез `UX-52`: убрать часть перегруженности из owner/admin экранов `Knowledge` и `Проверка консультанта` через progressive disclosure и role-aware surface split, чтобы owner видел только основной путь (`готовность -> действие -> проверка`), а вторичные инструменты команды не конкурировали с ним на первом экране.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-owner-knowledge-stabilization-reset-a4.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-scope-gate-unification-a5.md`

## Git / worktree
- `Branch`: `feat/2026-03-15-console-owner-surface-decomposition-a6`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-a6`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `console-web/src/app/knowledge/page.tsx` is `3243` LOC and still mixes branch readiness, draft authoring, validation, publish, rollback, learning candidates, and low-level inspector tooling on one screen.
- In the draft step, `Client Pack Inspector` appears inline next to the main authoring flow (`console-web/src/app/knowledge/page.tsx:2403-2450`), even though it is a support/debugging tool rather than the primary owner action.
- `Learning candidates` are still always rendered at the bottom of the main page (`console-web/src/app/knowledge/page.tsx:3091-3178`), which keeps secondary remediation content in the primary owner path.
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx` is `1078` LOC and still renders primary owner actions, session navigation, compare, findings, and advanced details in one dense workspace.
- The consultant verification workspace currently places `recent sessions`, `compare`, and `findings` on the same primary screen as the owner chat and explainer (`console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx:553-1074`).
- `UX-52` remains open in `docs/CONSOLE_AUDIT/UX_BACKLOG.md`: the previous stabilization blocks fixed truth/state issues, but not the surface density that keeps producing owner frustration.

## One web search (mandatory before implementation)
- **Query (exact):** `site:design-system.service.gov.uk ask users for information progressively`
- **Date/time (local):** `2026-03-15T11:47:00+05:00`
- **Sources opened (from this query):**
  - `https://design-system.service.gov.uk/patterns/question-pages/`
- **Ready solutions found:** GOV.UK recommends asking for information progressively and keeping one primary decision/action in focus instead of forcing users through dense multi-purpose screens.
- **Decision:** `integrate` — keep `Knowledge` and `Проверка консультанта` on their existing routes, but demote advanced/admin tooling behind progressive disclosure and clearer role-aware sections so owners see the smallest truthful path first.
- **Rejected options:** leave all tools inline and try to fix overload with copy only; split every workflow into new routes immediately; remove advanced tools entirely for owner/admin.
- **Source quality:** primary/high-signal source = official GOV.UK Design System guidance.

## Root cause (mandatory)
- **Symptom:** owner/admin pages remain frustrating even after sync and scope fixes because the screens still present too many mixed responsibilities at once.
- **Minimal reproduction:**
  1. Open `Knowledge` as an owner on a branch with valid sync.
  2. Observe that draft authoring, support inspector data, publish readiness, history, rollback, and learning candidates compete on one surface.
  3. Open `Проверка консультанта` as an owner.
  4. Observe that the owner chat shares the same visible screen weight with session management, compare, findings, and team diagnostics.
- **Evidence:** code refs above, open `UX-52`, and repeated user feedback that the interface became less effective after earlier fixes.
- **Five Whys (or equivalent):**
  1. Why do these screens still feel heavy? Because advanced/admin tools remain inline with the primary owner flow.
  2. Why are advanced tools inline? Because prior blocks fixed correctness first and kept the existing page structure.
  3. Why does that hurt owners now? Because every additional truth/safety control now occupies the same visual priority as the owner's next action.
  4. Why does that increase bug frustration? Because users have to parse too much state before they can tell what to do next.
  5. Why is this still unresolved after scope-gate unification? Because scope-gate reuse reduced drift, but did not separate primary and secondary responsibilities.
- **Root cause statement:** `Knowledge` and `Проверка консультанта` still treat owner actions, admin tooling, and diagnostic context as one flat surface, so even correct behavior feels overloaded and hard to trust.
- **Fix mechanism:** apply progressive disclosure and role-aware surface split: keep the primary owner lane visible by default, move secondary/admin tooling into bounded support sections, and extract the new sections into smaller components so the pages stop accumulating mixed concerns.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing role resolution in both pages, existing `details`/secondary panel pattern in consultant verification, existing shared scope gate, and existing child panels (`Compare`, `Findings`, `SessionSummary`) rather than rewriting page behavior.
- **External reuse:** GOV.UK progressive disclosure guidance for reducing dense multi-purpose screens.
- **Why not build from scratch:** the data contracts and child components already exist; the problem is information architecture and composition, not missing primitives.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted frontend lint/build + `1` targeted Playwright suite for this slice.
- **Fail-fast / scenario lock:** stop after the first regression without a new RCA delta.
- **Stop condition:** owner primary lanes are visibly smaller on both pages and deterministic proof is green.
- **Escalation path:** Brain / Top Architect if a second rerun is needed without new evidence.

## Invariant
- Do not change backend contracts or runtime behavior.
- Do not weaken fail-closed sync/readiness behavior.
- Do not remove compare/findings/learning capabilities; only move them out of the primary path.
- Do not introduce a second scope-gate implementation.

## Scope
- Frontend-only surface decomposition for `Knowledge` and `Проверка консультанта`.
- Extract/support smaller components where needed.
- Progressive disclosure for secondary/admin tooling.
- Role-aware presentation so owner primary path is smaller while admin/platform admin still retain access to advanced tooling.
- Deterministic Playwright proof for the reduced owner path and preserved advanced access.
- Canon/docs/state sync for `UX-52`.

## Out of scope
- New backend endpoints.
- Full rewrite of `knowledge/page.tsx`.
- New compare/finding features.
- Role permission changes.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
- `console-web/src/app/business/consultant-verification/_components/*` (new/extracted presentation helpers if needed)
- `console-web/src/components/*` (new owner/admin support components if needed)
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-console-owner-surface-decomposition-a6.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Start a clean dedicated session/worktree from `origin/main`.
2. Decompose `Проверка консультанта` into a primary owner lane and a secondary team-tools lane, keeping compare/findings/advanced details out of the default owner scan path.
3. Demote `Knowledge` secondary tools (`Client Pack Inspector`, `Learning candidates`, and other support-only blocks touched in this slice) behind progressive disclosure / support sections so the draft->validate->publish path stays primary.
4. Extract any new support sections into smaller components to reduce page-level orchestration.
5. Extend deterministic Playwright coverage for owner-visible simplification and preserved advanced access.
6. Sync canon docs/state/backlog and prepare PR.

## DoD
- `Проверка консультанта` shows a smaller default owner path than current main, with compare/findings/team diagnostics moved into secondary tooling.
- `Knowledge` keeps draft/validate/publish primary while support-only tools touched in this slice are no longer inline-first.
- Advanced/admin tooling remains accessible and functional.
- No backend contract changes are required.
- Targeted frontend checks and Playwright proof are green.
- Canon docs/state reflect `UX-52` progress and remaining residual debt.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-a6/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-a6/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-a6/console-web && npm run dev -- --hostname 127.0.0.1 --port 3000` + `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'consultant verification owner surface|knowledge support tools disclosure'`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-a6 && SESSION_AGENT=a6 scripts/session_check.sh`

## Evidence
- Code diff showing smaller primary owner lanes and extracted support sections.
- Targeted Playwright proof for owner simplification + preserved advanced access.
- Updated `STATE.md` entry before merge.

## Release safety (mandatory for non-doc changes)
- Strategy: frontend-only IA/decomposition change on existing routes.
- Go/no-go signals:
  - owner can still complete draft/validate/publish and consultant verification without opening advanced panels,
  - advanced tools remain reachable for admin/platform admin,
  - no regression in existing sync-block/readiness behavior.
- Rollback: revert the PR; existing surfaces remain available.
- Post-release monitoring window: first 48h after merge; watch owner reports about missing controls or hidden-but-needed actions.

## Rollback
- Revert the feature branch merge.
- Restore the previous page layout/components.

## No-go
- No backend changes.
- No new product features.
- No hiding critical owner actions behind advanced panels.
- No partial decomposition that leaves duplicate advanced blocks in two places.

## Risks/Blockers
- `knowledge/page.tsx` is still very large, so the first slice must stay narrow and avoid opportunistic refactors.
- Existing Playwright mocks may need updates because previously-inline blocks become collapsible or role-aware.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `knowledge/page.tsx` and `ConsultantVerificationWorkspace.tsx` will still remain larger than ideal after this first decomposition slice.
- Owner/admin surface split will still be partial until the remaining secondary flows are extracted out of the page files.

### Why not in this block
- This slice is intentionally limited to primary-vs-secondary surface separation with no backend changes.

### Risk if deferred
- Future owner-facing fixes will still be more expensive until the remaining page-level orchestration is extracted.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-surface-decomposition-partb-a6`

### Expiry/trigger to stop deferral
- If the next owner-facing fix touches the same pages again, the remaining extraction becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Extract the remaining page-level orchestration from `Knowledge` and `ConsultantVerificationWorkspace` into smaller owner/admin-specific components once the primary surface split is proven.

### First deterministic check command
- `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`

### Blocked-by conditions
- This primary-vs-secondary surface split must land first.
- Need confirmation from targeted Playwright proof that hidden secondary tooling remains reachable.

### Owner role for closure
- Brain / Top Architect
