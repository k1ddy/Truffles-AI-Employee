# SESSION 2026-02-10-deploy-clean-source-a27 — Deploy clean-source isolation

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-10-main-ci-deploy-contract-fix-a23.md
- branch: fix/2026-02-10-deploy-clean-source
- worktree: /home/zhan/truffles-main
- base_ref: origin/main
- scope: Fix deploy gate failure caused by dirty runtime worktree on host.
- done:
  - Investigated failed run 21867575107 and captured root cause from deploy logs.
  - Implemented clean deploy-source checkout flow in CI deploy step.
- next:
  - Commit patch and open PR.
- evidence:
  - https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21867575107
  - /tmp/deploy-job-63113390651.logs.bin
- last_updated: 2026-02-10
