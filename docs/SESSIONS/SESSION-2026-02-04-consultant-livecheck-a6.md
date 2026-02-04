# SESSION 2026-02-04-consultant-livecheck-a6 — Consultant live dialog check

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-04-consultant-livecheck.md
- branch: feat/2026-02-04-consultant-livecheck-a6
- worktree: /home/zhan/worktrees/2026-02-04-consultant-livecheck-a6
- base_ref: origin/main
- scope: Live-check CA06 consult (и CA05 booking-commit при готовности gates) с фиксацией evidence.
- done:
  - Session created.
  - Preflight: prod host confirmed, /admin/health captured (minimum_data_contract missing for 2 branches) `/tmp/admin_health_20260204_consultant_livecheck.json`.
  - Livecheck CA06 consult succeeded; evidence `/tmp/livecheck_ca06_consult_20260204.txt`.
  - Live dialog booking script run via webhook (custom sequence); evidence `/tmp/live_dialog_booking_message_ids_20260204.json`, `/tmp/outbox_payload_live_dialog_booking_20260204.json`, `/tmp/trace_bundle_live_dialog_LC-DIALOG-07099f34.json`, `/tmp/trace_bundle_live_dialog_LC-DIALOG-722f2abc.json`, `/tmp/trace_bundle_live_dialog_LC-DIALOG-f8546bf3.json`, `/tmp/trace_bundle_live_dialog_LC-DIALOG-5f533133.json`.
- next:
  - Decide whether to run CA05 booking-commit (blocked by minimum_data_contract in /admin/health).
- evidence:
  - docs/TASK_PACKAGES/TP-2026-02-04-consultant-livecheck.md
- last_updated: 2026-02-04
