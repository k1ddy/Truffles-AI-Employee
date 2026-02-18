# Wave 0.1 + Wave 0 Baseline (2026-02-18)

## Scope
- Precondition integrity gate for core operational tables.
- Runtime backlog baseline with reason classification for outbox failures.
- Separation of `expected_external_block` (e.g., ChatFlow unpaid/billing) from `unexpected_failure`.

## Commands
```bash
python3 -m py_compile ops/diagnose.py ops/console_platform_admin_kpi_snapshot.py ops/console_owner_admin_kpi_snapshot.py
python3 ops/diagnose.py integrity-gate --client-slug demo_salon --pretty --output /tmp/integrity_gate_wave0_t0.json
python3 ops/diagnose.py integrity-gate --client-slug demo_salon --fail-on-critical --output /tmp/integrity_gate_wave0_t0_gate.json
python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_wave0_t0.json
python3 ops/console_platform_admin_kpi_snapshot.py --fail-on-breach --fail-level critical --output /tmp/platform_admin_kpi_wave0_t0_gate.json
python3 ops/console_owner_admin_kpi_snapshot.py --client-slug demo_salon --pretty --output /tmp/owner_admin_kpi_wave0_t0.json
python3 ops/console_owner_admin_kpi_snapshot.py --client-slug demo_salon --fail-on-breach --fail-level critical --output /tmp/owner_admin_kpi_wave0_t0_gate.json
```

## Integrity Gate Result (Wave 0.1)
- Status: `PASS`
- `infra_valid=true`
- Checks: `8` total, `8 PASS`, `0 WARN`, `0 FAIL`, `0 ERROR`
- Critical failures: none

Evidence:
- `/tmp/integrity_gate_wave0_t0.json`
- `/tmp/integrity_gate_wave0_t0_gate.json`

## Runtime Baseline (Wave 0)
- Platform guard: `critical` (`pending=2147`, `failed=1867`), `incident_class=runtime_incident`
- Owner/Admin guard: `critical` (`outbox_backlog=2147`), `incident_class=runtime_incident`
- Gate exits: platform `2`, owner/admin `2`

Evidence:
- `/tmp/platform_admin_kpi_wave0_t0.json`
- `/tmp/platform_admin_kpi_wave0_t0_gate.json`
- `/tmp/owner_admin_kpi_wave0_t0.json`
- `/tmp/owner_admin_kpi_wave0_t0_gate.json`

## Reason Classification (FAILED)
- `expected_external_block`: `314`
- `unexpected_failure`: `1548` (platform) / `1546` (owner/admin)

Top `unexpected_failure` reasons:
1. `Outbound delivery failed: [CHATFLOW_ERROR] ... invalid_response` -> `1237`
2. `... payload_failure` -> `122`
3. `invalid_payload:event:invalid_tenant_context_contract` -> `41`
4. `... ChatFlow returned 502` -> `38`
5. `calendar_sync_failed:provider_error` -> `28`

Top `expected_external_block` reason:
1. `CHATFLOW_BILLING_BLOCKED ... plan renewal required` -> `314`

## Blockers
1. Runtime is still in `critical` state; rollout for visit/reminder/marketing waves remains blocked.
2. `unexpected_failure` dominates `FAILED` backlog; billing-only interpretation is incorrect.
3. `manual_revert:invalid_tenant_context_contract` remains in `PENDING` backlog and needs targeted remediation loop.
4. Outbox classification is now explicit in snapshots, but remediation actions are still operational/manual.

## Decision
- `Wave 0.1` precondition is satisfied for current tenant snapshot.
- `Wave 0` is **not** complete: guard remains `critical` with dominant runtime failures.
- Next execution should target only `unexpected_failure` classes first; `expected_external_block` tracked as external operating constraint.
