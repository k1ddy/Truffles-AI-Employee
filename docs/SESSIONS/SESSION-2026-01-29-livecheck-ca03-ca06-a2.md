# SESSION 2026-01-29-livecheck-ca03-ca06-a2 — Session 2026-01-29-livecheck-ca03-ca06-a2

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-01-29-livecheck-ca03-ca06.md
- branch: feat/2026-01-29-livecheck-ca03-ca06-a2
- worktree: /home/zhan/worktrees/2026-01-29-livecheck-ca03-ca06-a2
- base_ref: origin/main
- scope: Fix CA03/CA06 live-check regressions (trace retention + consult short-circuit heuristics).
- done:
  - Added `info_class` to decision_trace critical retention.
  - Relaxed force-consult blockers to allow consult cues with price/duration/hours.
  - Local tests: `PYTHONPATH=. pytest -q tests/test_demo_salon_eval.py -k "truth_first_info_bundle or consult_pack_only_and_short_circuit"`.
- next:
  - Open PR and run Livecheck Only CI.
  - Capture livecheck evidence + update STATE.md if required.
- evidence:
  - docs/TASK_PACKAGES/TP-2026-01-29-livecheck-ca03-ca06.md
  - Local test output: 2 passed, 8 deselected (3.12s).
- last_updated: 2026-01-29
