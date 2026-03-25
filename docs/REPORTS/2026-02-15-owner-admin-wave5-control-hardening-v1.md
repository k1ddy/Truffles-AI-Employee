# Owner/Admin Wave-5 Report (Control Hardening + Rollback + Decomposition Start)

Date
- 2026-02-15

Goal
- После merge Wave-4 закрыть 4 follow-up направления единым пакетом:
  1. формализованный post-merge контроль `T+0/T+24`,
  2. impact KPI baseline/replay,
  3. guided remediation с rollback в Team KPI,
  4. старт декомпозиции owner/admin helper-логики из `console.py`.

Delivered
- Post-merge control loop v2:
  - runbook `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md` переписан под strict протокол `T+0` и `T+24`.
  - обязательный baseline path + replay compare (`--baseline`) зафиксированы в runbook.
- Owner/Admin KPI snapshot tool:
  - добавлен `ops/console_owner_admin_kpi_snapshot.py`.
  - snapshot включает бизнес KPI (`outbox_backlog`, `unresolved_cases`, `unresolved_older_than_60m`, `first_response_p90_seconds`), guard status, settings profile, LOC section.
  - поддержан baseline compare + impact summary (`improved|regressed|mixed_or_stable`) и `--fail-on-breach`.
- Team Performance remediation rollback:
  - при применении quick profile `5/30/60` сохраняется предыдущий SLA snapshot.
  - добавлен guided remediation блок с пошаговой инструкцией.
  - добавлена кнопка one-click rollback к предыдущим значениям SLA (`team-performance-quick-profile-rollback`).
- Decomposition starter:
  - owner/admin helper-функции вынесены из `truffles-api/app/routers/console.py` в `truffles-api/app/services/console_owner_admin.py`.
  - router подключает те же символы через import aliases (behavior-preserving).

Validation
- Backend:
  - `python3 -m py_compile ops/console_owner_admin_kpi_snapshot.py truffles-api/app/services/console_owner_admin.py`
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_owner_admin.py truffles-api/tests/test_console_owner_business.py`
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `54 passed`
- Frontend:
  - `npm --prefix console-web run lint` -> OK
  - `npm --prefix console-web run build` -> OK
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> owner/admin smoke cases listed, including Team KPI rollback surfaces.
  - note: worktree required `npm --prefix console-web install` before checks (`next: not found` initially).

Evidence
- `/tmp/owner_admin_wave5_t0.json`
- `/tmp/owner_admin_wave5_t24.json`
- `/tmp/owner_admin_wave5_t0_gate.json` (optional fail-fast gate)
- `T+0` snapshot facts (`/tmp/owner_admin_wave5_t0.json`):
  - `outbox_backlog=1673`
  - `unresolved_cases=2`
  - `unresolved_older_than_60m=0`
  - `first_response_p90_seconds=0.03`
  - `kpi.guard.status=critical`
  - `settings_profile=30/60/120`
- Gate run (`/tmp/owner_admin_wave5_t0_gate.json`) returned `exit_code=2` with `--fail-on-breach --fail-level critical`.

Result
- Owner/Admin loop перешёл от "применить фикс" к управляемому циклу:
  - есть rollback,
  - есть baseline/replay impact,
  - есть runbook на 24h,
  - owner/admin часть `console.py` получила первый безопасный extraction шаг.
