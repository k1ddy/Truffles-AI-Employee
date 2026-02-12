# SESSION 2026-02-12-console-contract-live-fallback-a32 — Console Contract Live Fallback

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-12-console-contract-live-fallback-a32.md
- branch: fix/2026-02-12-console-contract-live-fallback-a32
- worktree: /home/zhan/truffles-main
- base_ref: origin/main
- scope: Устранить fail в `console-contract-live` из-за отсутствующих fallback env при резолве selection headers.
- done:
  - Снят fail-пакет из run `21930218302` (`Resolve console selection headers`, HTTP 401 на `/console/v1/me`).
  - Подготовлен точечный patch в `.github/workflows/ci.yml`.
- next:
  - Прогнать session/yaml checks.
  - Закоммитить и открыть PR.
  - Проверить `console-contract-live` в новом CI run.
- evidence:
  - `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21930218302`
  - `.github/workflows/ci.yml`
- last_updated: 2026-02-12
