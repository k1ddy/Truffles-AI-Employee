# SESSION 2026-02-11-deploy-ephemeral-source-a27 — Deploy Ephemeral Source

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-11-deploy-ephemeral-source-a27.md
- branch: fix/2026-02-11-deploy-ephemeral-source-a27
- worktree: /home/zhan/truffles-main
- base_ref: origin/main
- scope: Убрать persistent deploy clone на сервере из CI и перейти на временный checkout в `/tmp` с очисткой.
- done:
  - Подготовлен patch для `.github/workflows/ci.yml`: deploy source checkout через `mktemp` + `trap cleanup`.
- next:
  - Закоммитить изменения в ветку `fix/2026-02-11-deploy-ephemeral-source-a27`.
  - Открыть PR и проверить CI deploy.
  - После merge выполнить разовый cleanup старой директории `/home/zhan/truffles-main-deploy`.
- evidence:
  - `.github/workflows/ci.yml`
  - `python3` YAML parse (`YAML_PARSE_OK`)
- last_updated: 2026-02-11
