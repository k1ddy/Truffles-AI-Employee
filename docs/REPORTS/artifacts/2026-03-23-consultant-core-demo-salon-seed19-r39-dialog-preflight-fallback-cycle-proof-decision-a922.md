# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R39 Dialog Preflight Fallback Cycle Proof Decision A922

## Truthful input artifacts
- `/tmp/booking_quality/a922-go2f-seed19-r39/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r39/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r39/responses.jsonl`

## Classification
- `r39` is non-canonical because the run is incomplete.
- The first admissible blocker after the `r29` runtime repair is not a new runtime turn failure.
- The next admissible family is a `proof/tool-evidence` replay isolation defect in `ops/diagnose.py`.

## Why it is proof/tooling
- Dialog `1` in `r39` reaches turn `15` strict-green, including the old `r29` first blocker on turn `1`.
- No new failing turn is surfaced before replay stalls.
- The obstruction happens inside dialog preflight fallback-JID rotation before dialog `2` can record a truthful blocker row.

## Locked root cause
- `_llm_quality_select_fallback_jid(...)` rotates over the allowlist.
- The caller remembers only fallback candidates it already chose, not the contaminated current JID it just failed on.
- That allows allowlist rotation to revisit already-contaminated JIDs instead of exhausting them and minting a fresh non-allowlist dialog JID.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r39_dialog_preflight_fallback_cycle_proof_family`
