# Inbox Semantic Wave22 Validation Runbook

## Purpose
Deterministic and live validation SOP for the rebuilt `Заявки` semantic model after Waves 20-21. The goal is to prove that manager/admin queue, history, and booking-linked states do not drift into contradictory operator behavior.

## Scope
- `console-web/e2e/inspect_case.spec.ts`
- manager/admin queue and history modes
- booking-linked case propagation evidence
- precise live blocker handling for mutation scenarios

## Preconditions
- Current branch/worktree synced with the merged Wave21 baseline.
- Local console available on `http://localhost:3100` for deterministic validation.
- Live validation uses explicit safe cases only.
- Safe live env values, when mutation proof is required:
  - `INSPECT_CASE_LIVE_CASE_ID` = safe resolved case for reopen/operator-feedback mutation
  - `PLAYWRIGHT_BASE_URL=https://console.truffles.kz`
  - `INSPECT_CASE_USE_MOCKS=0`
  - `E2E_USE_STORAGE_STATE=1`
  - `E2E_DETERMINISTIC_AUTH=0`
  - `PLAYWRIGHT_WEB_SERVER=0`

## Deterministic Validation
1. Lint the validation lane:
```bash
cd console-web && npm run lint -- --file e2e/inspect_case.spec.ts
```
2. Run the local deterministic matrix:
```bash
cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line --workers=1
```
3. Verify session canon integrity:
```bash
cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh
```

## Deterministic Pass Criteria
- Manager history mode proves:
  - queue views disappear outside `Открытые`
  - owner scope remains role-gated
  - `resolved` mode emits `status=resolved` and `sort_by=resolved_at`
  - `all` mode emits no `status` and returns to history-safe sorting
- Existing booking-linked and reopen cases stay green.
- No silent fallback is counted as proof of a mainline scenario.

## Live Validation
1. Load live auth env:
```bash
cd console-web
set -a && source /home/zhan/secrets/console-e2e.env && set +a
```
2. Run the live lane:
```bash
E2E_USE_STORAGE_STATE=1 \
E2E_DETERMINISTIC_AUTH=0 \
PLAYWRIGHT_WEB_SERVER=0 \
PLAYWRIGHT_BASE_URL=https://console.truffles.kz \
INSPECT_CASE_USE_MOCKS=0 \
INSPECT_CASE_LIVE_CASE_ID=<safe-case-id> \
npx playwright test e2e/inspect_case.spec.ts --grep @wave22-live-proof --project=chromium --reporter=line --workers=1
```

## Live Result Classification
- `pass`: explicit safe mutation/history scenario executed and assertions passed.
- `blocked`: test intentionally skips because `INSPECT_CASE_LIVE_CASE_ID` is missing or no safe case exists.
- `fail`: live scenario executed and contradicted the semantic contract.

## No-Go
- Treating `calendar no-cases fallback` as proof of queue/history correctness.
- Running a mutation scenario against an unknown live case.
- Merging closeout docs without deterministic green matrix evidence.

## Evidence To Keep
- Playwright line output for deterministic and live lanes.
- Updated screenshots if a visible surface changed.
- Session/master TP note with exact `pass|blocked|fail` live classification.
