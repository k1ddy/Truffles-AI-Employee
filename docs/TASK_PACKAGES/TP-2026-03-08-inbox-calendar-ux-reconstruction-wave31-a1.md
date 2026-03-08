# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE31-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1
- `UNLOCKS`: only bounded routing v2 or capability-aware inputs after Wave30 proves operationally sufficient

## Название/цель
Следующий блок после Wave30 — не “ещё один routing tweak”, а decision gate: определить, есть ли уже реальные server-owned capability inputs для assignee routing v2, или продукту достаточно Wave30 routing profiles без дальнейшей автоматизации.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: define on activation
- `Cleanup`: Brain / Top Architect after merge

## Invariant
- Не изобретать fake `skills`, `presence`, `shift` или “availability” в UI/local state.
- Не вводить routing v2, если входные capability signals всё ещё не server-owned и не тестируемы контрактно.
- Не ломать Wave24-30 queue/saved-view/share-link/follow-up governance/routing profile contracts.

## Scope
- Определить, есть ли в системе реальные server-owned assignee capability inputs для следующего routing layer.
- Если inputs есть — ограничить следующий block до одного bounded routing v2 slice.
- Если inputs нет — зафиксировать stop condition и не раздувать routing дальше.

## Out of scope
- Реализация Wave31 в этом TP не стартует автоматически.
- Любой новый code diff по routing v2/capabilities без обновления этого TP запрещён.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## One web search (mandatory before implementation)
- Этот блок пока `not started`.
- Перед любым Wave31 implementation обязательно записать ровно один точный search и решение `reuse/integrate/build`.

## Root cause (mandatory)
- **Symptom:** после Wave30 routing стал управляемым, но ещё не доказано, нужен ли следующий automation layer вообще.
- **Minimal reproduction:** попытка проектировать routing v2 без новых server-owned inputs быстро скатывается в fake capability modeling.
- **Evidence:** Wave30 canon and code already cover queue-state, presets, share URLs, follow-up governance, explainable routing, and assignee routing profiles.
- **Root cause statement:** следующий routing layer блокируется не отсутствием кода, а отсутствием подтверждённых server-owned capability signals.
- **Fix mechanism:** открыть Wave31 только после deterministic proof, что новые capability inputs существуют, принадлежат серверу и имеют bounded operational value.

## Plan (1..N)
1. Проверить operational effect of Wave30 after merge.
2. Доказать наличие или отсутствие новых server-owned capability inputs.
3. Либо ограничить Wave31 до одного bounded routing v2 slice, либо зафиксировать stop and hold.

## DoD
- Следующий routing block либо чётко определён, либо явно заблокирован без fake scope expansion.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave30|Wave31|routing profiles|routing v2|capability" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`

## Evidence
- Canon-only until Wave31 activation.

## Rollback
- Remove this planning TP if Brain/Top Architect choose a different next block.

## No-go
- Не стартовать Wave31 code changes из этого planning stub.
- Не использовать этот TP как разрешение на fake capability routing.

## Риски/блокеры
- Главный риск — начать routing v2 без новых фактов и снова смешать operational truth with UI heuristics.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: Wave31 still depends on real capability inputs that may not exist yet.
- `Why not in this block`: this TP is a stop-gap planning contract, not an implementation block.
- `Risk if deferred`: команда может снова начать спор о routing maturity без factual inputs.
- `Linked follow-up Task Package(s)`: next implementation TP must supersede this stub explicitly.
- `Expiry/trigger to stop deferral`: if Wave30 proves insufficient and new capability data becomes server-owned, this planning stub must be replaced by an execution TP.

## Next-block contract (mandatory)
- `Next block objective`: either bounded routing v2 on real capability inputs or explicit no-go decision to stay on Wave30.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "One web search|Root cause|Plan|DoD" docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `Blocked-by conditions`: no real server-owned capability inputs; any attempt to fake them blocks immediately.
- `Owner role for closure`: Brain / Top Architect.
