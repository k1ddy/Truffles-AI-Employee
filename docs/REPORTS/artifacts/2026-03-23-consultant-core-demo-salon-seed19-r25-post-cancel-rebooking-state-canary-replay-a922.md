# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Canary Replay A922

## Fresh replay truth
- Started a fresh local runtime on `127.0.0.1:18186` using `/home/zhan/truffles-main/truffles-api/.env`.
- Verified runtime parity before replay: `/admin/version.git_commit == HEAD` and `/admin/health` returned `200`.
- Audited and excluded three non-canonical replay attempts before the truthful run:
  - `r26`: pre-existing stale `system_exit` artifact with missing strict artifacts
  - `r27`: blocked by `manual_audit_pending:a922-go2f-seed19-r26` before scenario execution
  - `r28`: `invalid_runtime_fingerprint_preflight` after local uvicorn was started without the canonical env file
- Truthful fresh replay artifact: `/tmp/booking_quality/a922-go2f-seed19-r29`
- Strict audit: `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`

## Outcome
- The old post-cancel rebooking family is no longer the first surfaced blocker; replay stops earlier on dialog `1`, turn `1`.
- `r29` is `infra_valid=true`, `artifact_integrity.valid=true`, and `semantic_valid=false`.
- `stop_reason=max_failures_reached:1`, so this is an admissible fail-fast closure artifact.

## New first blocker surfaced by replay
- Row: `LLM-QUAL-a922-go2f-seed19-r29-001-01-5279e4`
- User: `Я хочу записаться на маникюр на завтра.`
- Expected contract: `booking_prompt` / `collect`, `source=llm_policy_core`, `expected_reply_type=time`, trace contains `question_contract`.
- Actual runtime path: `turn_planner_safe_explicit_handoff_owner` with `decision_meta.action='escalate'`, `tool_action='handoff'`, `reason_code='terminal_owner_unresolved'`.
- Strict fail: `expected_meta_mismatch`, `expected_trace_miss`.

## Classification
- `r29` does not introduce a new proof/oracle blocker.
- The first surviving blocker is now a bounded runtime contract regression on the initial booking entry path.
- Shadow risk remains explicit because both `booking_prompt` and `explicit_handoff` owner names are duplicated in `truffles-api/app/services/reasoning_core.py`.
