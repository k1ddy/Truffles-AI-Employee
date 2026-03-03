# UVC Stage 1 IA Matrix (a705)

Date: `2026-03-02`
Parent TP: `TP-2026-03-02-uvc-ux-stage1-ia-matrix-a705.md`

## Goal
Зафиксировать единую матрицу ответственности вкладок UVC и убрать competing actions.

## Keep / Move / Remove Matrix

| Area | Primary business job | Keep | Move | Remove | Canonical entry point |
|---|---|---|---|---|---|
| `Tenants` | Fleet orchestration, lifecycle, priority queue | `tenants-action-queue`, context lens, lifecycle actions | none | local competing execute shortcuts outside queue intents | `Tenants -> Приоритетные задачи` |
| `Integrations` | Branch facts, diagnostics, SLA visibility | branch matrix, today mode, facts, `integrations-row-open-workspace` | none | any fleet-level competing action queue | `Integrations -> Открыть в Workspace` |
| `Company Workspace` | Execute remediation/provider actions | recommended action panel, action form, dry-run/execute | none | hidden action source fallback via storage | `Workspace -> Открыть форму действия` |
| `Ops` | Incident/jobs confirmation and monitoring | incident feed, run/job history | none | direct duplication of provider execute controls | `Ops -> Incident/Jobs panels` |

## Entry Point Rules
- One action, one owner tab.
- `Tenants` decides what to do first.
- `Integrations` explains facts and opens exact branch context.
- `Workspace` executes actions only.
- `Ops` confirms operations and incidents; no duplicate execute forms.

## Stage 1 implementation notes
- Removed legacy dual-source behavior for Workspace recommended action:
  - deleted local storage read/write path `console:workspace_recommended_action`.
  - kept URL query as single source (`recommended_action`, `action_source`, `action_reasons`, `action_mode`).
- Added shared business-language module for provider actions/reasons:
  - `console-web/src/lib/provider-ops-language.ts` is now reused by `Tenants`, `Integrations`, `Company Workspace`, and fleet attention panels.
  - action/reason labels are unified and rendered in plain language instead of raw internal codes.
- Result: action origin is explicit, reproducible, and auditable from URL context.
