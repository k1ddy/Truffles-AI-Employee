# TP-2026-03-23 Consultant Core Demo Salon Seed19 R22 Preflight Contamination Canary Replay A922

- Title/goal: rerun the exact seed-`19` replay on fresh runtime parity after the bounded proof isolation repair and classify the first surviving blocker.
- Canon refs: `STATE.md` NOW; `docs/ACTIVE_PROGRAM.md`; `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r22-preflight-contamination-proof-implementation-a922.md`.
- Invariant: keep runtime parity truthful and do not use non-canonical or regenerated scenarios.
- Scope: one fresh replay `/tmp/booking_quality/a922-go2f-seed19-r23` plus strict audit.
- Out of scope: new runtime or proof edits.
- Touch-list:
  - `/tmp/booking_quality/a922-go2f-seed19-r23`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r22-preflight-contamination-canary-replay-a922.md`
- Plan:
  1. Start a fresh local runtime from the active worktree and confirm `/admin/health` + `/admin/version` parity.
  2. Replay the frozen `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` scenario set into `/tmp/booking_quality/a922-go2f-seed19-r23`.
  3. Strict-audit the artifact and classify the next surviving blocker before any new code.
- DoD:
  - fresh replay artifact exists;
  - strict audit is done;
  - proof isolation closure or the next blocker is documented truthfully.
- Work mode (mandatory): closure
- Checks:
  - `curl -sf http://127.0.0.1:18186/admin/health`
  - `curl -sf http://127.0.0.1:18186/admin/version`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r23 --status done --strict-artifacts`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r23/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
- Rollback: discard the replay artifact and stop the local runtime.
- No-go:
  - no scenario regeneration;
  - no stale runtime reuse;
  - no gate weakening.
- Risks/blockers:
  - fail-fast can surface the next runtime family before full dialog coverage.
- Residual architecture debt (mandatory):
  - Current residuals accepted in this block: any new surfaced family after replay remains outside this closure block.
  - Why not in this block: this block only proves or disproves the proof-family closure on fresh evidence.
  - Risk if deferred: canon would keep pointing at a closed proof family.
  - Linked follow-up Task Package(s): `TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-decision-a922.md`
  - Expiry/trigger to stop deferral: immediate after the fresh replay audit.
- Next-block contract (mandatory):
  - Next block objective: classify the first surviving blocker from `r23` and lock the next admissible family.
  - First deterministic check command: `python3 - <<'PY'\nimport json\nrows=[json.loads(line) for line in open('/tmp/booking_quality/a922-go2f-seed19-r23/responses.jsonl')]\nprint(rows[-1]['message_id'], rows[-1]['evaluation'])\nPY`
  - Blocked-by conditions: runtime parity mismatch; incomplete manual audit.
  - Owner role for closure: Brain / Top Architect
