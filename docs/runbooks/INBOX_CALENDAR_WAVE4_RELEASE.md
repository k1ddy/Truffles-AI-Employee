# Inbox+Calendar Wave4 Release Runbook

## Purpose
Операционный SOP для wave4 (`SSE + reliability KPI`) на вкладках `Заявки/Записи`: canary, go/no-go, rollback.

## Scope
- `console-web` runtime behavior (`SSE-first` updates in case workspace).
- KPI from `/console/v1/metrics/daily`:
  - `queue_lag_seconds`
  - `stale_view_rate`
  - `case_action_apply_latency_seconds`

## Preconditions
- Wave4 branch merged to deploy target.
- Доступны env:
  - `E2E_USERNAME`
  - `E2E_PASSWORD`
  - `KEYCLOAK_ISSUER`
  - `KEYCLOAK_CLIENT_ID`
  - `KEYCLOAK_CLIENT_SECRET`
- `NEXT_PUBLIC_CASE_SSE_ENABLED` explicitly set (`1` for rollout, `0` for rollback).

## Stage 0 Preflight
1. `cd console-web && npm run lint -- --file src/hooks/useCaseData.ts --file e2e/inspect_case.spec.ts`
2. `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`
3. `cd console-web && INSPECT_CASE_USE_MOCKS=0 PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`

`Pass/Block rule`
- `pass`: mocked lane green and live lane gives either `pass` or explicit reasoned `skip` with screenshot.
- `block`: unreasoned failure in live lane or regression in mocked lane.

## Canary Plan
1. `Stage A (1 branch, 30m)`:
`NEXT_PUBLIC_CASE_SSE_ENABLED=1` only for canary branch.
2. `Stage B (25% branches, 2h)`:
Expand only if Stage A go.
3. `Stage C (100% branches)`:
Expand only if Stage B go.

## KPI Snapshot Command
1. Get token:
```bash
TOKEN=$(curl -s -X POST "https://auth.truffles.kz/realms/truffles/protocol/openid-connect/token" \
  -d "client_id=${KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
  -d "grant_type=password" \
  -d "username=${E2E_USERNAME}" \
  -d "password=${E2E_PASSWORD}" | jq -r '.access_token')
```
2. Read daily metrics:
```bash
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://api.truffles.kz/console/v1/metrics/daily" | jq '{
    date,
    queue_lag_seconds,
    stale_view_rate,
    case_action_apply_latency_seconds
  }'
```

## Go/No-Go
1. `queue_lag_seconds <= 180`
2. `stale_view_rate <= 0.05`
3. `case_action_apply_latency_seconds <= 300`
4. `inspect_case` mocked lane pass
5. `inspect_case` live lane `pass` or `skip` only with `auth gate` reason and screenshot evidence

`No-Go triggers`
- KPI threshold breach for 2 consecutive snapshots.
- Live lane failure without explicit reasoned skip.
- Frontend regression in `CaseConversation/Calendar` flow.

## Fast Rollback
1. Set `NEXT_PUBLIC_CASE_SSE_ENABLED=0`.
2. Restart console-web.
3. Re-run:
`cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`
4. If degradation persists: revert wave4 PR commit set.

## Decision Log Template
```text
wave4_stage: A|B|C
timestamp_utc:
sse_flag:
inspect_case_mocked: pass|fail
inspect_case_live: pass|skip(auth_gate)|fail
queue_lag_seconds:
stale_view_rate:
case_action_apply_latency_seconds:
decision: GO|NO_GO|ROLLBACK
operator:
notes:
```
