# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE11-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-PARTB-A1

## Название/цель
Довести reassignment в `Заявки` до policy-based routing automation без нового route/tab: менеджер и супервизор должны не только видеть нагрузку, но и запускать серверное назначение по прозрачной политике прямо из текущих single-case и bulk surfaces.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred; split only into `Part A backend policy contract` then `Part B UI/apply surfaces` if backend is ready earlier
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/types/api.generated.ts`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
- `Baseline findings`:
  - reassignment recommendation уже есть, но она живет в клиентском `resolveRecommendedAssignee(...)` и опирается только на локально загруженный `open_case_count`;
  - сервер не отдаёт policy decision как контракт и не умеет применить назначение через `route by policy`, поэтому bulk/single-case routing остаётся ручным и слабо аудируемым;
  - текущий `bulk reassign` умеет только принять конкретный `agent_id`, а не policy mode, поэтому супервизор всё ещё вручную раскладывает очередь даже там, где правило очевидно;
  - branch-scoped доступность ассайни требует, чтобы policy decision принимался сервером, а не копировался по разным UI-компонентам.

## One web search (mandatory before implementation)
- **Query (exact):** `Dynamics 365 Customer Service assignment rules capacity routing official docs`
- **Date/time (local):** `2026-03-06T18:47:00+05:00`
- **Sources opened:**
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-assignment-rules`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/queues-omnichannel`
- **Ready solutions found:** mature service desks separate queue eligibility from assignment decision and keep the routing rule server-side; the agent UI gets an explainable recommendation or one-click apply action instead of rebuilding policy in each screen.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse current assignee/load queries and existing `reassign` flow, but add a bounded server policy contract (`least_open_cases`, branch-scoped) and wire it into current single-case and bulk panels.
- **Rejected options:** silent fully automatic reassignment on every queue refresh; new routing screen/tab; client-side-only heuristics duplicated in multiple components.
- **Source quality:** high-signal primary source = official Microsoft Learn documentation.

## Root cause (mandatory)
- **Symptom:** reassignment is less blind than before, but still not policy-driven: managers see a recommendation, then manually choose/apply it; bulk routing has no one-click policy mode.
- **Minimal reproduction:** open an active case or select several active cases in one branch -> UI shows who has fewer open cases -> operator must still manually pick that agent; there is no server-stamped decision, no explicit policy metadata, no bulk auto-route action.
- **Evidence:** current backend only exposes assignee options with `open_case_count`; current frontend computes recommendation locally in `CaseConversation.tsx` and `CaseList.tsx`; `/cases/bulk` accepts only `action=reassign` with explicit `agent_id`.
- **Five Whys:**
  1. Why is routing still slow? Because the operator must manually replicate the obvious recommendation.
  2. Why is the recommendation brittle? Because each UI surface computes it locally from partial state.
  3. Why is this risky at scale? Because branch eligibility and future policy rules can drift between components.
  4. Why is supervisor control incomplete? Because bulk routing cannot apply a transparent policy in one action.
  5. Why does this block mature queue governance? Because routing exists as UI advice, not as a server-owned business contract.
- **Root cause statement:** current routing assist is presentational, not contractual: the policy decision lives in frontend heuristics instead of a backend-owned, auditable routing contract that both single-case and bulk flows can share.
- **Fix mechanism:** move recommendation/apply logic to backend as an explicit routing policy contract and expose one-click `route by policy` actions in the existing reassignment surfaces.

## Reuse-first plan (mandatory)
- **Reuse:** `_list_case_assignee_options`, current `open_case_count` load mapping, existing `reassign` mutations, bulk toolbar, current assignee UI panels, existing audit/idempotency patterns.
- **Integrate:** add server policy evaluation on top of existing assignee query and use it from both direct reassign and bulk actions.
- **Build only if needed:** one small routing-policy helper and minimal response/request extensions; no new queue engine and no new screen.

## Invariant
- Не вводить скрытое автоназначение без явного действия менеджера/супервизора.
- Не допускать cross-branch reassignment в обход текущих branch access rules.
- Не ломать существующий manual `reassign` path.
- Не добавлять новый tab/route ради routing automation.

## Scope
- `Part A (this TP)`:
  - backend policy contract for `single-case` and `bulk` routing based on current eligible assignees and `open_case_count`;
  - explicit policy metadata in API response (`policy`, `recommended_agent_id`, `reason summary`);
  - policy apply path that reuses existing reassignment semantics and audit trail.
- `Part B (same PR if small enough)`:
  - single-case `Передать` panel gets `Назначить по политике` / `Применить рекомендацию сервера`;
  - bulk toolbar gets `Распределить по политике` for same-branch selection;
  - inspect-case deterministic lane validates the new controls and payload/response handling.

## Out of scope
- Presence-aware routing and real capacity model.
- Round-robin across branches/teams with overtime/availability rules.
- Background automatic routing without operator click.
- A new supervisor dashboard.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Зафиксировать новый Wave12 TP и перевести session canon на policy-routing block.
2. Добавить backend routing policy helper и API contract для recommendation/apply.
3. Подключить same policy contract к `single-case` и `bulk` flows без дублирования логики.
4. Обновить UI surfaces в `CaseConversation` и `CaseList` на one-click policy action.
5. Синхронизировать OpenAPI/generated types и обновить inspect-case lane.

## DoD
- Сервер умеет вернуть и применить routing decision по прозрачной policy, не только список assignees.
- Single-case reassignment имеет one-click policy apply.
- Bulk routing умеет применять ту же policy для same-branch selection.
- Manual reassignment остаётся рабочим и не регрессирует.
- Targeted backend/frontend checks зелёные и inspect-case lane подтверждает новый flow.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Targeted pytest/OpenAPI/lint/Playwright outputs.
- Session log with Wave12 evidence.

## Release safety (mandatory)
- **Rollout:** explicit operator action only; no hidden automation. Existing manual reassignment stays available as safe fallback.
- **Go/no-go:** policy recommendation resolves only eligible assignees, bulk action refuses mixed-branch or invalid selections, manual reassign still passes.
- **Rollback:** revert bounded diff; UI falls back to explicit assignee selection only.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave12 checks.

## No-go
- Переносить routing policy в клиентские if/else вместо backend ownership.
- Автоматически менять владельца без явного action пользователя.
- Поддерживать mixed-branch bulk routing через best-effort fallback.
- Раздувать scope до полноценного workforce management.

## Риски/блокеры
- Нужно удержать explainability: why this assignee was chosen must remain visible in UI.
- Bulk policy apply должен либо быть same-branch only, либо явно отказывать без partial silent reassignment.
- Будущая presence/capacity модель не должна ломать этот контракт; поэтому policy name и reason должны быть explicit в API.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: policy останется bounded to `least_open_cases` within eligible assignees; no real presence/capacity; no background auto-routing.
- `Why not in this block`: это следующий maturity step без ухода в новый routing subsystem.
- `Risk if deferred`: без richer capacity model возможны спорные назначения при одинаковой загрузке или реальной недоступности менеджера.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`, `TBD follow-up for presence/capacity-aware routing if Wave12 proves valuable`.
- `Expiry/trigger to stop deferral`: если после Wave12 менеджеры всё ещё вручную перераспределяют большинство новых заявок из-за отсутствия presence/capacity signals, нужен отдельный follow-up TP.

## Next-block contract (mandatory)
- `Next block objective`: after Wave12 merge, validate whether `least_open_cases` policy is enough or whether the next required block is presence/capacity-aware routing for supervisors.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: Wave12 must not regress existing manual reassign/bulk reassign flows or branch access constraints.
- `Owner role for closure`: Brain / Top Architect.
