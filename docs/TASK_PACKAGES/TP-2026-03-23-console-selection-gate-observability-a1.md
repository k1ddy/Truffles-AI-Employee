# TP-2026-03-23-console-selection-gate-observability-a1

- Block ID: `console-selection-gate-observability-a1`
- Название/цель: добавить bounded client-side observability и controlled verification для selection-gate/auth-session drift, чтобы плавающий серый экран можно было доказывать или исключать по сигналам, а не по воспоминаниям пользователей.
- Canon refs: `STATE.md` (`DONE (prod deployed, selection-gate stabilization)`), `docs/TASK_PACKAGES/TP-2026-03-23-console-selection-gate-stabilization-a1.md`, `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-stabilization-a1.md`, `STRUCTURE.md` (`console-web/src/components/ConsoleShell.tsx`, `console-web/src/components/LoginButton.tsx`, `console-web/e2e/`, `console-web/src/app/api/`), `TECH.md`.

## Invariant

- Не ослаблять tenant isolation, auth-gates, explicit logout semantics и ранее внесённый hotfix сохранения последнего валидного scope при auth/session expiry.
- Не вводить новый server-owned scope model в этом блоке.
- Не превращать monitoring route в general-purpose analytics sink; только bounded event family для selection-gate/session drift.

## Scope

- Добавить bounded console-web telemetry route для четырёх событий:
  - `selection_gate_shown`
  - `selection_gate_confirmed`
  - `auth_session_expired_signout`
  - `scope_cleared_explicit_logout`
- Логировать reason-fields и scope-presence, достаточные для RCA:
  - `gate_kind`
  - `reason_code`
  - `session_error`
  - `api_error_code`
  - `company/client/branch` presence
- Добавить controlled verification coverage, которая доказывает emission этих событий в ключевых flows.
- Подготовить operator evidence path для `docker logs truffles-console-web`.

## Out of Scope

- Backend API schema migrations, Prometheus counters, audit DB persistence, or a new console telemetry product surface.
- Перенос selected scope из localStorage в server-owned session.
- Полный incident dashboard или alerting stack для этих событий.

## Touch-list

- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/components/LoginButton.tsx`
- `console-web/src/app/api/console-client-events/route.ts`
- `console-web/src/lib/console-client-events.ts`
- `console-web/e2e/smoke.spec.ts`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-observability-a1.md`

## Work mode

- `implementation`

## One web search (mandatory before implementation)

- **Query (exact):** `MDN navigator.sendBeacon fetch keepalive page unload telemetry official docs`
- **Date/time (local):** `2026-03-23 18:05 Asia/Almaty`
- **Sources opened (from this query):**
  - MDN `Request: keepalive property`: `https://developer.mozilla.org/en-US/docs/Web/API/Request/keepalive`
  - MDN `Navigator.sendBeacon()`: `https://developer.mozilla.org/fr/docs/Web/API/Navigator/sendBeacon`
- Found ready-made solutions:
  - `fetch(..., { keepalive: true })` is explicitly meant for analytics/session-end requests that must survive page unload/navigation.
  - `navigator.sendBeacon()` remains the standard low-friction fallback for fire-and-forget telemetry during unload.
- **Decision:** `reuse/integrate`
  - Reuse browser-native unload-safe delivery (`fetch keepalive` with `sendBeacon` fallback) for auth-signout/logout telemetry instead of inventing custom retry or local persistence.
- **Rejected options:**
  - `build`: local queue/retry persistence in browser storage was rejected as unnecessary for this bounded telemetry family.
  - `backend-first`: adding a new backend transport before proving the bounded console-web signal path was rejected as wider than needed for the current monitoring block.

## Root cause (mandatory)

- Symptom:
  - После hotfix логин под `admin/admin` иногда выглядит нормальным, но инцидент остаётся плавающим: нельзя доказать, исчезла ли именно auth/session-driven family или просто не повезло её не встретить.
- Minimal reproduction:
  - Логин под multi-company аккаунтом.
  - Либо дождаться auth/session drift, либо вручную сбросить stored scope / воспроизвести expired session.
  - Сегодня UI может не зависнуть, но в следующий раз семейство повторится без доказуемого следа на клиентской стороне.
- Evidence:
  - Ранее root cause уже был завязан на `invalid_grant` / `RefreshAccessTokenError` и повторный `selection_gate`.
  - После hotfix есть только container log про refresh failure и внешний UX-симптом; нет machine-readable signals о том, показывался ли gate, подтвердил ли его пользователь, ушёл ли shell в signout из-за session expiry, и очистился ли scope только по explicit logout.
  - Без этих signals one successful login under `admin/admin` не закрывает incident family.
- Five Whys:
  - Why can’t we tell whether the bug is actually gone? Because the client emits no bounded telemetry for the selection-gate/session-expiry family.
  - Why do server logs alone not close the gap? Because `invalid_grant` in console-web logs does not prove whether the UI showed the gate, whether it remained interactive, or whether the user explicitly logged out.
  - Why is this important for a flaky issue? Because pass/fail depends on timing and browser state, so anecdotal checks are noisy.
  - Why is the current verification insufficient? Because existing smoke coverage proves the fix path locally, but production monitoring lacks matching runtime signals.
  - Why does that block truthful closeout? Because we cannot correlate complaint -> auth drift -> gate shown/confirmed/signout without a bounded client event trail.
- Root cause statement:
  - The hotfix reduced a known root cause, but the incident remains operationally unverifiable because console-web has no bounded runtime telemetry for the exact selection-gate/session-expiry family and no controlled verification that those signals survive redirect-sensitive flows like auth signout.
- Fix mechanism:
  - Add a bounded console-web telemetry route plus a small client helper that emits four specific events with unload-safe delivery for signout/logout paths.
  - Add controlled Playwright verification that captures and asserts those emissions in selection-gate and auth-expiry flows.

## Reuse-first plan (mandatory)

- Strategy: `reuse -> integrate -> configure -> build`
- Internal reuse:
  - existing `ConsoleShell` gate/auth handlers
  - existing `LoginButton` explicit logout path
  - existing Playwright auth helpers in `console-web/e2e/smoke.spec.ts`
  - existing Next.js `app/api/*` route pattern
- External reuse:
  - browser-native `fetch keepalive` and `navigator.sendBeacon` delivery semantics from MDN
- Why no new framework/library:
  - The problem is bounded event delivery and verification, not missing analytics infrastructure.

## Token / run budget (mandatory for expensive suites)

- Max full runs: `1`
- Planned expensive runs:
  - one targeted lint pass
  - one `npm run build`
  - one targeted Playwright smoke run for selection-gate telemetry
- Stop condition:
  - Stop after one green proof bundle; if the telemetry flow fails twice without new evidence, return to RCA instead of widening scope.

## Plan

1. Keep the same single worktree and switch it to a new follow-up branch from `origin/main`.
2. Create the follow-up TP/session docs and wire the new session to the current branch.
3. Add a bounded `console-client-events` route in `console-web` that validates and logs only the required event family.
4. Add a shared client helper that emits structured events with `keepalive`/`sendBeacon` support for redirect-sensitive flows.
5. Instrument `ConsoleShell` and `LoginButton` for `selection_gate_shown`, `selection_gate_confirmed`, `auth_session_expired_signout`, and `scope_cleared_explicit_logout`.
6. Add controlled Playwright verification that captures telemetry payloads for selection gate, explicit logout, and forced auth-expiry signout.
7. Run targeted checks and record the operator evidence path in docs/STATE.

## DoD

- Console-web emits exactly the bounded event family with machine-readable fields sufficient for RCA.
- Auth-expiry/signout and explicit logout use unload-safe telemetry delivery.
- Controlled verification proves telemetry emission for selection-gate and auth-expiry flows.
- Operator evidence path for production observation is documented and practical.
- No regression to the existing selection-gate hotfix or explicit logout cleanup semantics.

## Checks

- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && npm run lint -- --file src/components/ConsoleShell.tsx --file src/components/LoginButton.tsx --file src/lib/console-client-events.ts --file src/app/api/console-client-events/route.ts --file e2e/smoke.spec.ts`
- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && PLAYWRIGHT_BASE_URL=http://localhost:3000 PLAYWRIGHT_WEB_SERVER=0 E2E_USERNAME=admin E2E_PASSWORD=admin npx playwright test e2e/smoke.spec.ts --project chromium --workers 1 --grep 'selection gate telemetry'`

## Evidence

- Session log: `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-observability-a1.md`
- Code diff in the touch-list
- Targeted lint/build/Playwright outputs
- Example operator command against container logs after deploy

## Release safety (mandatory for non-doc changes)

- Strategy: additive console-web-only observability route and client events; no backend schema change.
- Go/no-go signals:
  - targeted lint/build green
  - targeted Playwright telemetry verification green
  - no sign-in/sign-out regression in local or live smoke
  - route logs only the bounded event family and rejects invalid payloads
- Rollback:
  - revert the observability commit(s) and redeploy `console-web`
- Post-release monitoring window:
  - `72h`, focusing on `console_client_event` lines, `Error refreshing access token`, and any renewed reports of gray selection gate dead-ends

## Rollback

- Revert the console-web telemetry route/helper/instrumentation commit(s) and redeploy `console-web`.

## No-go

- Do not add a generic analytics sink or tenant-unbounded telemetry endpoint.
- Do not log raw company/client/branch IDs in the new event payload.
- Do not change backend auth/session semantics in this block.
- Do not create another worktree.

## Risks / blockers

- `sendBeacon` / unload timing can still be browser-sensitive; mitigation is `fetch keepalive` first with `sendBeacon` fallback.
- If telemetry route becomes noisy, logs may be harder to read; mitigation is strict event-family validation and concise structured payloads.

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - Events are logged in console-web runtime logs, not persisted as first-class backend audit records.
  - There is still no dedicated dashboard/counter surface for this family.
- Why not in this block:
  - The immediate need is truthful monitoring and reproducible proof, not a broader telemetry platform.
- Risk if deferred:
  - Correlation remains log-based and manual rather than queryable via product surface.
- Linked follow-up Task Package(s):
  - Follow-up TP required if the family repeats and needs persisted backend counters/audit exposure.
- Expiry/trigger to stop deferral:
  - Any repeated gray-screen complaint after this monitoring block or any need for multi-day trend aggregation beyond container logs.

## Next-block contract (mandatory)

- Next block objective:
  - Either close the incident after `72h` clean monitoring with evidence, or open the first persisted-backend telemetry TP if the family repeats.
- First deterministic check command:
  - `docker logs --since 72h truffles-console-web | rg "console_client_event|Error refreshing access token"`
- Blocked-by conditions:
  - This block must deploy first; observation cannot start before live telemetry exists.
- Owner role for closure:
  - Top Architect / Brain

## Branch + Worktree + Base ref + Merge policy + Cleanup

- Branch: `feat/2026-03-23-console-selection-gate-observability-a1`
- Worktree: `/home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1`
- Base ref: `origin/main`
- Merge policy: merge only after targeted local proof and docs sync
- Cleanup: keep the same worktree; remove branch after merge if no longer needed
