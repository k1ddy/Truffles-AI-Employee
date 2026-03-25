# TP-2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Canary Replay A922

- Title/goal: rerun the exact seed-`19` replay on fresh runtime parity after the bounded `r23` runtime repair and classify the first surviving blocker truthfully.
- Canon refs: `STATE.md` NOW; `docs/ACTIVE_PROGRAM.md`; `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-implementation-a922.md`; `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-implementation-a922.md`.
- Invariant: keep replay truthful on the locked scenario set; no new runtime or proof edits in this block.
- Scope: one fresh replay `/tmp/booking_quality/a922-go2f-seed19-r24` plus strict audit and truthful blocker classification.
- Out of scope: runtime code changes; proof tooling changes; scenario regeneration.
- Touch-list:
  - `/tmp/booking_quality/a922-go2f-seed19-r24`
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-canary-replay-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- Plan:
  1. Confirm no stale listener is active on `127.0.0.1:18186`.
  2. Start a fresh local runtime from the active worktree with canonical env and prove `/admin/health` + `/admin/version.git_commit == HEAD`.
  3. Replay the locked `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` set into `/tmp/booking_quality/a922-go2f-seed19-r24`.
  4. Strict-audit the artifact and classify the first surviving blocker before any further edits.
  5. Sync canon to either closure or the next bounded family.
- DoD:
  - fresh replay artifact exists;
  - strict audit is done;
  - runtime repair is either closed on fresh evidence or the next blocker is classified truthfully.
- Work mode (mandatory): `closure`
- Checks:
  - `ss -ltnp | rg ':18186' || true`
  - `curl -sf http://127.0.0.1:18186/admin/health`
  - `curl -sf http://127.0.0.1:18186/admin/version`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r24 --status done --strict-artifacts`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
- Rollback: stop the local runtime and discard the replay artifact if the run is non-canonical or parity-invalid.
- No-go:
  - no scenario regeneration;
  - no stale runtime reuse;
  - no gate weakening;
  - no code edits before replay classification.
- Risks/blockers:
  - fail-fast can surface the next family before full dialog coverage;
  - local runtime parity can fail if a stale listener survives on `:18186`.
- Residual architecture debt (mandatory):
  - Current residuals accepted in this block: any next surfaced family remains outside this replay closure block.
  - Why not in this block: this block only proves or disproves the bounded `r23` repair on fresh evidence.
  - Risk if deferred: canon would keep pointing at a potentially closed runtime family.
  - Linked follow-up Task Package(s): `TP-2026-03-23-consultant-core-demo-salon-seed19-r23-post-replay-decision-a922.md` or the next surfaced family TP.
  - Expiry/trigger to stop deferral: immediately after strict audit of `r24`.
- Next-block contract (mandatory):
  - Next block objective: classify the first surviving blocker from `r24` and lock the next admissible family.
  - First deterministic check command: `python3 - <<'PY'\nimport json\nrows=[json.loads(line) for line in open('/tmp/booking_quality/a922-go2f-seed19-r24/responses.jsonl')]\nprint(rows[-1]['message_id'], rows[-1]['evaluation'])\nPY`
  - Blocked-by conditions: runtime parity mismatch; incomplete strict audit; run manifest refusing the replay.
  - Owner role for closure: Brain / Top Architect
