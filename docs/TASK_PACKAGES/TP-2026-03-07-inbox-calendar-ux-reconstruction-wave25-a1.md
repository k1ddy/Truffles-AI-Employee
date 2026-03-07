# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE25-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE24-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE24-A1
- `UNLOCKS`: managed team presets and shareable catalog URLs on top of the proven queue-state canon

## Название/цель
Добавить personal named saved views для `Заявки` и `Записи` поверх server-owned `Queue State Canon`, чтобы оператор мог сохранять, переиспользовать и помечать default operational views без возврата к browser-local хаосу.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: bounded split allowed: `Part A saved-view backend catalog`, `Part B frontend save/apply UX`
- `Cleanup`: Brain / Top Architect after the saved-views block is merged and verified

## FACT pre-check (before implementation)
- Wave24 canon is now implemented: backend owns current queue state and frontend restore precedence is `URL override -> server current state -> local fallback`: `truffles-api/app/services/console_queue_state.py`, `console-web/src/lib/queue-state.ts`.
- Queue state is now stored in a reusable canonical object, but only as current state; there is still no named catalog to save multiple views: `truffles-api/app/models/console_queue_state.py`.
- The current UI still requires operators to rebuild recurring views manually after switching tasks or experimenting with filters: `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`.
- Team-managed presets, shareable catalog URLs, and richer routing remain intentionally blocked until a personal saved-view layer proves the queue-state contract in a multi-view catalog.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.zendesk.com Managing your views shared personal views agents admins`
- **Date/time (local):** `2026-03-07T18:41:56+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- **Ready solutions found:** mature help-desk products separate personal views from shared/admin-managed views, keep the saved object server-owned, and treat filters/columns/order/defaults as explicit view metadata instead of browser-only state.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse the Wave24 queue-state canon as the saved payload and add a bounded personal catalog on top, instead of inventing a second view model.
- **Rejected options:** store saved views only in browser storage; jump straight to team-managed presets before the personal catalog proves the contract; couple saved views to case/panel presentation state.
- **Source quality:** high-signal primary source = official Zendesk documentation.

## Root cause (mandatory)
- **Symptom:** even after Wave24, operators still have only one recoverable current queue state and cannot keep multiple named operational views.
- **Minimal reproduction:** configure `Мои открытые`, then rebuild `Закрытые за 7 дней`, then return to the first slice; only one current state survives and the second useful slice must be rebuilt manually.
- **Evidence:** `truffles-api/app/models/console_queue_state.py`, `truffles-api/app/services/console_queue_state.py`, `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`.
- **Five Whys:**
  1. Why can’t operators reuse multiple queue slices? Because only one current state is stored.
  2. Why is one state insufficient? Because recurring operational work needs a small catalog, not just “last opened”.
  3. Why can’t local storage solve it? Because it is not governable, durable, or cross-device.
  4. Why not jump to team presets directly? Because personal catalog semantics must be proven first on the new canon.
  5. Why is this the right next layer? Because it is the smallest product step that validates the canon as a reusable object instead of a single snapshot.
- **Root cause statement:** Wave24 solved canonical current-state ownership, but the product still lacks a server-owned multi-view catalog, so operators cannot save and reliably reapply multiple named queue states.
- **Fix mechanism:** add a personal saved-view catalog that stores `name + surface + canonical query_state + default flag` per operator and integrates it into inbox/calendar apply/save/delete flows.

## Reuse-first plan (mandatory)
- **Reuse:** Wave24 canonical queue-state payload, surface-specific normalization, current queue-state restore/apply helpers, current inbox/calendar query semantics.
- **Integrate:** new saved-view catalog model/API layered on top of the existing canon; frontend uses the same queue-state snapshot helpers for save/apply.
- **Build only if needed:** one new saved-view storage model/migration and bounded save/apply UI; no team ACL/preset engine in this block.

## Invariant
- Wave24 precedence and current-state behavior must not regress.
- Saved views must store only operational queue state, not local presentation state.
- `selected case`, side panel mode, and visible fields stay out of the saved-view payload unless explicitly approved in a later block.
- Team-managed presets, shareable catalog links, and richer routing remain out of scope here.

## Scope
- `Part A saved-view backend catalog`:
  - add personal saved-view model/storage and CRUD API for `cases` and `calendar`
  - reuse Wave24 canonical `query_state` as saved payload
  - support bounded `is_default` behavior per surface/operator
- `Part B frontend save/apply UX`:
  - list personal saved views
  - save current state under a name
  - apply/delete saved views
  - optionally mark one personal view as default per surface

## Out of scope
- managed team presets/defaults by role/branch
- share-by-`view_id` public URLs
- cross-agent sharing/ACLs
- richer routing or bookings supervisor-grade ownership/history

## Touch-list
- `truffles-api/app/models/*` (new saved-view model)
- `truffles-api/app/services/console_queue_state.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/migrations/*`
- `truffles-api/tests/*`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/types/api.generated.ts`

## Saved-view canon (mandatory)
- `Saved view payload`:
  - `surface`
  - `name`
  - `version`
  - `query_state` (exact Wave24 canon)
  - `is_default`
  - `position/order` only if needed for deterministic UI
- `Excluded from payload`:
  - selected case
  - side panel mode
  - visible columns/fields
  - transient cursor/pagination
  - transient composer/form state

## Plan (1..N)
1. Define backend personal saved-view schema/model and bounded CRUD API.
2. Add deterministic tests for create/list/apply/delete/default semantics.
3. Wire frontend inbox/calendar to list and apply saved views.
4. Add save/delete/default controls with explicit operator feedback.
5. Re-run deterministic/backend/frontend checks and sync canon docs.

## DoD
- Operators can save multiple named personal views for `cases` and `calendar`.
- Applying a saved view restores the same canonical queue state as Wave24 current-state restore.
- One personal default view per surface can be marked and persisted server-side.
- Saved views do not leak local presentation state into the shared operational payload.
- Wave24 current-state behavior remains green.

## Checks
- `cd truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/models app/services/console_queue_state.py app/routers/console.py app/schemas/console.py tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/queue-state.ts --file src/lib/api-client.ts --file src/components/CaseList.tsx --file src/app/calendar/page.tsx`
- `cd console-web && npm run build`

## Evidence
- backend saved-view schema/migration/API diff
- frontend save/apply/delete/default UX diff
- deterministic/backend/frontend output proving saved-view reuse

## Release safety (mandatory)
- **Rollout:** additive; current-state path remains the baseline and saved-view catalog is layered on top.
- **Go/no-go:** merge only if inbox/calendar still function when no saved views exist.
- **Rollback:** revert the saved-view commit(s) and keep Wave24 current-state behavior intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave25 checks
- confirm Wave24 current-state behavior still restores correctly

## No-go
- Do not mix team-managed presets into the personal catalog block.
- Do not save panel/case/visible-fields presentation state as part of the canonical payload.
- Do not change routing policy in the same block.
- Do not replace current-state restore with saved views; saved views layer on top.

## Риски/блокеры
- If saved-view payload diverges from Wave24 canon, the product will recreate two state models.
- If `is_default` is not bounded per surface/operator, restores will feel random.
- If the UI couples saved views to local presentation, future team presets will inherit the wrong contract.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: managed team presets, catalog share links, bookings supervisor-grade follow-up ownership/history, and richer routing remain deferred.
- `Why not in this block`: personal saved views are the smallest product layer that proves catalog semantics without ACL and governance complexity.
- `Risk if deferred`: admins still cannot govern team defaults and operators still cannot share a catalog URL by id, but the product gains a reusable personal layer.
- `Linked follow-up Task Package(s)`: open managed presets only after saved-view catalog evidence is green.
- `Expiry/trigger to stop deferral`: if Wave25 lands and teams still need branch/role default views, the next block must be managed presets rather than unrelated UI polish.

## Next-block contract (mandatory)
- `Next block objective`: managed team presets and governed defaults built on the exact same saved-view object with different ownership/ACL.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Saved-view canon|is_default|Excluded from payload" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md`
- `Blocked-by conditions`: any regression in Wave24 queue-state restore, or any attempt to mix presentation state/team ACL into the personal-catalog block.
- `Owner role for closure`: Brain / Top Architect.
