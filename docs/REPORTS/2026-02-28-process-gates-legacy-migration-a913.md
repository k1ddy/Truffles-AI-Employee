# REPORT 2026-02-28-process-gates-legacy-migration-a913

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-LEGACY-MIGRATION-2026Q2`
- `Session`: `2026-02-28-process-gates-legacy-migration-a913`
- `Branch`: `feat/2026-02-28-process-gates-legacy-migration-a913`

## Goal
Выполнить wave-1 phased migration для legacy `missing` cohort: добавить явные режимы `optional` в выбранных stale active сессиях.

## Baseline (before)
- Source: `/tmp/session_adoption_a913_before.json`
- `open_sessions=112`
- `research_gate`: `required=4`, `optional=0`, `missing=108`, `invalid=0`
- `legacy_missing=108`

## Migration wave-1
- Cohort rule: top-20 `legacy_missing` + `status=active` с максимальным `age_hours`.
- Change applied in each selected session:
  - `research_gate: optional`
  - `root_cause_gate: optional`
  - `reuse_gate: optional`
  - `release_safety_gate: optional`

### Migrated sessions (20)
- `2026-01-27-livecheck-recovery-a1` (age_h=785)
- `2026-01-28-console-e2e-live-login-a2` (age_h=761)
- `2026-01-28-tenants-crud-a2` (age_h=761)
- `2026-01-27-consultant-canon-a2` (age_h=737)
- `2026-01-29-livecheck-ca03-ca06-a2` (age_h=737)
- `2026-01-29-tenants-company-backfill-a2` (age_h=737)
- `2026-01-29-tenants-list-api-a2` (age_h=737)
- `2026-01-31-inbox-macros-ui-fix-a3` (age_h=689)
- `2026-02-02-console-calendar-past-dates-a5` (age_h=641)
- `2026-02-02-console-inbox-auto-refresh-toggle-a4` (age_h=641)
- `2026-02-03-booking-confirm-full-verify-a6` (age_h=617)
- `2026-02-03-booking-full-cycle-gcal-a1` (age_h=617)
- `2026-02-03-session-index-hygiene-a1` (age_h=617)
- `2026-02-04-llm-policy-core-impl-a7` (age_h=593)
- `2026-02-04-llm-policy-fastpath-a9` (age_h=593)
- `2026-02-04-metrics-daily-auto-a6` (age_h=593)
- `2026-02-06-booking-quality-matrix-a10` (age_h=545)
- `2026-02-06-onboarding-flow-canon-a12` (age_h=545)
- `2026-02-06-booking-quality-matrix-a14` (age_h=521)
- `2026-02-07-decision-safe-degrade-a13` (age_h=521)

## Result (after)
- Source: `/tmp/session_adoption_a913_after.json`
- `research_gate`: `required=4`, `optional=20`, `missing=88`, `invalid=0`
- `legacy_missing=88`
- `delta_missing=20`
- `delta_optional=20`

## Owner closure decision
- `PROCESS-GATES` phase is marked closed by owner decision for current program lane.
- Remaining adoption/hygiene deltas (`legacy_missing/stale_active/done_cleanup_candidates`) are tracked as non-blocking backlog.
- No cross-phase dependency lock is allowed from this block.

## Checks
- `bash -n scripts/session_audit.sh scripts/session_check.sh scripts/session_gate.sh`
- `SESSION_AGENT=a913 scripts/session_check.sh`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a913_before.json`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a913_after.json`
- `jq` delta compare of before/after counts

## Risks / notes
- Wave-1 intentionally keeps legacy in `optional`; strict mode promotion can be executed later as dedicated governance backlog.
- `stale_active` and `done_cleanup_candidates` remain high and are treated as non-blocking hygiene backlog.

## Next block handoff
- `UNLOCK`: none (phase closed by owner decision)
- Optional follow-up backlog command:
  - `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_hygiene_followup.json`
