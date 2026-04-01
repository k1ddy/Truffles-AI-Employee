# SESSION 2026-02-16-tool-args-typed-a88 — Strict Tool Args Typed Contracts

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-16-tool-args-typed-a88.md
- branch: feat/2026-02-16-tool-args-typed-a88
- worktree: /home/zhan/worktrees/2026-02-16-verifier-timeout-kernel-a88
- base_ref: origin/main
- scope: Единый strict typed-contract для `tool_args` на schema/runtime уровне + контрактные тесты без затрагивания других подсистем.
- done:
  - Добавлен TP для отдельного wave по typed contracts.
  - Внесены schema/runtime правки и добавлены регрессионные тесты.
  - Пройдены целевые проверки и `test_message_endpoint.py`.
- next:
  - Зафиксировать изменения коммитом.
  - Открыть отдельный PR по TP.
- evidence:
  - docs/TASK_PACKAGES/TP-2026-02-16-tool-args-typed-a88.md
  - pytest: `test_llm_policy_core.py`, `test_booking_appointments.py` target, `test_message_endpoint.py`
- last_updated: 2026-02-16
