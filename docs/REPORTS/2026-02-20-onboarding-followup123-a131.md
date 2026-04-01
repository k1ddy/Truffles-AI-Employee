# 2026-02-20 Onboarding Follow-up 1/2/3 (A131)

## Scope

- TP: `docs/TASK_PACKAGES/TP-2026-02-20-onboarding-followup123-a131.md`
- Branch: `feat/2026-02-20-onboarding-followup123-a131`
- Worktree: `/home/zhan/worktrees/2026-02-20-onboarding-followup123-a131`
- Goal: close follow-up items `1/2/3` after onboarding any-niche merge:
  - `1` delivery-closure quality without weakening fail-closed semantics.
  - `2` Console UX/UI visibility for reference-scope + contract sync.
  - `3` docs cleanup for missing canonical end2end-TZ file.

## Implementation

### 1) Delivery closure quality

- Readiness delivery counters now filter only delivery outbox events (`whatsapp.send_*`, `telegram.send_*`, `instagram.send_*`, `web.send_*`, `provider_gateway.outbound`) instead of counting unrelated outbox failures.
- Added billing thresholds:
  - `warn` on first billing-blocked signal.
  - `critical` on sustained billing-blocked failures (`>=3` in 24h window).
- Added explicit blocker question for billing warn signal.
- Updated ops diagnose delivery profile to mirror the same delivery-event filtering and expose `non_delivery_failed_24h` as separate noise counter.
- Added deterministic tests for:
  - billing `warn` behavior,
  - billing `critical` threshold behavior,
  - non-delivery outbox row exclusion.

### 2) Console UX/UI + contracts for reference scope

- Added reference-scope fields to canonical contract (`openapi.v1.yaml`):
  - `Client.reference_branch_ids`
  - `Client.reference_branch_reason`
  - `FleetAttentionItem.reference_branch_ids`
  - `FleetAttentionItem.reference_branch_reason`
- Console pages now display explicit reference-scope lines and reason labels:
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/app/integrations/page.tsx`
- Frontend generated types synchronized for the two new fields in:
  - `console-web/src/types/api.generated.ts`

### 3) Docs cleanup (end2end-TZ canonical)

- Added canonical umbrella document:
  - `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-end2end-tz.md`
- This closes broken references from prior onboarding plan docs/reports and maps all stage artifacts.

## Validation

- `python3 -m py_compile truffles-api/app/services/onboarding_state.py ops/diagnose.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> `0`
- `ruff check truffles-api/app/services/onboarding_state.py ops/diagnose.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> `0`
- `pytest -q truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_diagnose_onboarding_fleet.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_tenants_list.py` -> `88 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> `0`
- `npm --prefix console-web run generate:api` -> `0` (not used as final source of truth due known alias churn; final file kept as minimal contract patch)
- `npm --prefix console-web run lint -- --file src/app/tenants/page.tsx --file src/app/integrations/page.tsx --file src/types/api.generated.ts` -> `0`
- `npm --prefix console-web run build` -> `0`
- `python3 ops/diagnose.py onboarding-fleet-check --json` -> `0`
- `python3 ops/diagnose.py onboarding-delivery-stabilize --json` -> `0`

## Runtime Evidence

Artifacts:
- `/tmp/onboarding_followup123_a131/onboarding-fleet-check.json`
- `/tmp/onboarding_followup123_a131/onboarding-delivery-stabilize.json`

Snapshot highlights (`onboarding-delivery-stabilize`):
- `active_reference_branches=1`
- `active_delivery_critical=1`
- `delivery_failure_profile.total_failed_24h=1`
- `delivery_failure_profile.non_delivery_failed_24h=202`
- primary reason: `provider_billing_blocked`
- hard-gate blockers include:
  - `delivery:failed_24h_critical`
  - `delivery:provider_billing_blocked_critical`
  - `traffic:whatsapp_capability_mismatch`

Interpretation:
- Noise from non-delivery outbox rows is now separated and no longer inflates delivery failure totals.
- Branch remains delivery-critical due real provider billing signal and traffic mismatch, not due counting artifacts.

## Verdict

- Item `1`: PASS (delivery counting and blockers are reason-aware and noise-filtered).
- Item `2`: PASS (reference-scope is visible in Console UI and reflected in contract/types).
- Item `3`: PASS (missing end2end-TZ canonical doc restored).
- TP result: PASS.
