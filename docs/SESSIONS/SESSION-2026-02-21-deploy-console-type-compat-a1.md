# SESSION 2026-02-21-deploy-console-type-compat-a1 — Console Deploy Type Compatibility

- status: active
- owner: Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-21-deploy-console-type-compat-a1.md
- branch: fix/2026-02-21-company-schema-type-a1
- worktree: /home/zhan/worktrees/fix-2026-02-21-company-schema-type-a1
- base_ref: origin/main
- scope: Restore `console-web` build compatibility on current OpenAPI types and unblock `main` deploy.
- done:
  - Reproduced failing build path and traced type-contract drift.
  - Added legacy schema/operation aliases in `api.generated.ts`.
  - Fixed strict payload/type mismatches across impacted console pages/components.
  - Ran full `npm --prefix console-web run build` to green.
- next:
  - Commit and push branch.
  - Open PR and monitor CI/deploy run.
- evidence:
  - `npm --prefix console-web run build` (pass, static generation completed)
- last_updated: 2026-02-21
