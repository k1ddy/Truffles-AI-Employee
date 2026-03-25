# 2026-02-19 Onboarding Reference Branch Normalization Step3 (A131)

## Scope

- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
- Branch: `feat/2026-02-19-onboarding-any-niche-step123-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-any-niche-step123-a131`
- Goal: реализовать этап 5 из onboarding any-niche плана: нормализация reference branches для fleet readiness/attention контуров.

## Implementation

1) Reference selection kernel
- Added service `truffles-api/app/services/reference_branch_selection.py`.
- Input signals per branch:
  - `is_active`
  - `go_live_allowed`
  - `has_recent_inbound` (window 30 days)
  - `has_instance_id`, `has_phone`
  - `onboarding_go_no_go`, `integration_ok`
- Decision:
  - If active production-like rows exist -> select all ordered by rank, reason `active_live_signals`.
  - Else fallback to best active candidate, reason `active_fallback_best_candidate`.
  - If no active branches -> reason `no_active_branches`.

2) Console backend integration
- `truffles-api/app/routers/console.py`:
  - Added `_build_reference_branch_decisions(...)`.
  - Added `_select_reference_active_branches(...)`.
  - Fleet counters in `_build_fleet_client_details_map(...)` now use scoped active reference branches.
  - `list_clients` and `list_fleet_attention` now expose:
    - `reference_branch_ids`
    - `reference_branch_reason`
  - `list_fleet_attention` branch-level stale/integration counters now ignore non-reference active branches when reference subset exists.
- `truffles-api/app/schemas/console.py`:
  - Extended `ConsoleClient` and `ConsoleFleetAttentionItem` with reference scope fields.

3) Ops diagnose integration
- `ops/diagnose.py`:
  - Container fleet analysis now computes per-client reference decisions and marks each row:
    - `reference_branch`
    - `reference_branch_reason`
  - Summary now includes:
    - `reference_mode`
    - `active_branches_raw`
    - `active_reference_branches`
  - Default mode for fleet diagnostics: normalized reference scope.
  - Added explicit override flag: `--all-active-branches` for
    - `onboarding-fleet-check`
    - `onboarding-hard-gate-rollout`
    - `onboarding-delivery-stabilize`

## Tests

- New: `truffles-api/tests/test_reference_branch_selection.py`
  - recency window behavior
  - production-like selection
  - fallback best candidate
  - no active branches
- Updated:
  - `truffles-api/tests/test_console_fleet_attention.py`
  - `truffles-api/tests/test_console_tenants_list.py`
  - `truffles-api/tests/test_diagnose_onboarding_fleet.py`

## Validation

- `python3 -m py_compile truffles-api/app/services/reference_branch_selection.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py ops/diagnose.py truffles-api/tests/test_reference_branch_selection.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> PASS
- `ruff check truffles-api/app/services/reference_branch_selection.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py ops/diagnose.py truffles-api/tests/test_reference_branch_selection.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> PASS
- `pytest -q truffles-api/tests/test_reference_branch_selection.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> PASS (`61 passed`)
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "hard_gate or onboarding_scorecard or go_live or require_branch_scorecard"` -> PASS (`10 passed, 34 deselected`)
- `pytest -q truffles-api/tests/test_console_onboarding_state.py` -> PASS (`29 passed`)
- `python3 truffles-api/scripts/generate_openapi.py --check` -> PASS

## Runtime Evidence

- Directory: `/tmp/onboarding_reference_branch_step3_a131/`
- Files:
  - `onboarding_fleet_check_normalized.json`
  - `onboarding_fleet_check_all_active.json`
  - `onboarding_hard_gate_rollout_actual.json`
  - `onboarding_delivery_stabilize_normalized.json`
  - `onboarding_delivery_stabilize_all_active.json`
- Snapshot note:
  - В текущем runtime у клиента только одна active branch, поэтому normalized/all-active totals совпадают; корректность подтверждается по `reference_mode` и row-level reference annotations.
  - `onboarding-fleet-check`:
    - normalized: `reference_mode=normalized`, `active_branches=1`, `active_not_ready=0`.
    - all-active: `reference_mode=all_active`, `active_branches=1`, `active_not_ready=0`.
  - `onboarding-delivery-stabilize`:
    - normalized: `reference_mode=normalized`, `active_delivery_critical=1`.
    - all-active: `reference_mode=all_active`, `active_delivery_critical=1`.

## Verdict

- Step 3 (Reference Branch Normalization): PASS
- Result:
  - Fleet readiness/attention scope теперь устойчив к шуму test branches.
  - Scope remains configurable (`--all-active-branches`) для операторского сравнения и расследований.
