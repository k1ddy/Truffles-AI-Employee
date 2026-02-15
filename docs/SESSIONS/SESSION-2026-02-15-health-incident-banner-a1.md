# SESSION 2026-02-15-health-incident-banner-a1 — Incident Banner Compact/Snooze Controls

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-15-platform-admin-wave12345-a1.md
- branch: fix/2026-02-15-health-incident-banner-a1
- worktree: /home/zhan/truffles-main
- base_ref: origin/main
- scope: platform admin P0 incident banner UX hardening (collapse/snooze/show + deterministic e2e coverage).
- done:
  - Added compact default mode for global incident banner.
  - Added per-incident `Скрыть на 30м` and `Показать` controls with localStorage state.
  - Added e2e coverage for collapse/snooze/show flow in `platform-admin.spec.ts` with mocked health endpoint.
- next:
  - Run session check, commit, push branch, open PR.
- evidence:
  - npm --prefix console-web run lint
  - npm --prefix console-web run build
  - npm --prefix console-web exec -- playwright test e2e/platform-admin.spec.ts --list
- last_updated: 2026-02-15
