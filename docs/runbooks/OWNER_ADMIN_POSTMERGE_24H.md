# Owner/Admin Post-Merge 24H Control Loop (v2)

Purpose
- Проверить, что owner/admin улучшения после merge стабилизируют бизнес-контур, а не только UI.
- Вести сравнение `T+0` (сразу после merge) vs `T+24` (через ~24 часа) в одинаковом формате.

Fast path (automation wrapper)
- Вместо ручных шагов можно запускать orchestration:
  - `python3 ops/owner_admin_control_loop.py --mode t0 --client-slug demo_salon`
  - `python3 ops/owner_admin_control_loop.py --mode t24 --client-slug demo_salon --baseline /tmp/owner_admin_wave5_t0.json`
- Скрипт создаёт snapshot + gate + brief + log в `/tmp/owner_admin_control_loop/<run_id>/`.

When
- `T+0`: в течение 30 минут после merge.
- `T+24`: через 24 +/- 2 часа после `T+0`.

Required evidence
- `livecheck-auto` summary + `explain` trace/meta.
- KPI snapshot JSON (`ops/console_owner_admin_kpi_snapshot.py`) на `T+0` и `T+24`.
- Impact compare against baseline (`--baseline`).
- Session/report запись с абсолютными timestamp.

CI owner/admin acceptance lane (mandatory for `console_web` changes)
- Workflow job: `console-e2e-owner-admin-live` in `.github/workflows/ci.yml`.
- Required secrets:
  - `CONSOLE_OWNER_E2E_USERNAME`
  - `CONSOLE_OWNER_E2E_PASSWORD`
- Run command (inside CI job):
  - `npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --no-deps --reporter=list`
- Contract:
  - Missing owner/admin credentials is a hard fail (not skip).
  - `build-push` on main now waits for owner/admin lane result (`success|skipped`).

## 0) Integrity preflight (Wave 0.1 gate)

Перед `T+0` запуском зафиксировать data-integrity precondition:

```bash
python3 ops/diagnose.py integrity-gate \
  --client-slug demo_salon \
  --pretty \
  --output /tmp/integrity_gate_owner_t0.json
```

Gate mode:

```bash
python3 ops/diagnose.py integrity-gate \
  --client-slug demo_salon \
  --fail-on-critical \
  --output /tmp/integrity_gate_owner_t0_gate.json
```

Правило
- `summary.status=FAIL` или non-empty `summary.critical_failures` => stop-the-line до remediation/waiver.

## 1) T+0: runtime signal + baseline KPI

### 1.1 Live-check + explain

```bash
TEST_MODE=1 python3 ops/diagnose.py livecheck-auto \
  --suite ca10-outbox \
  --client-slug demo_salon \
  --base-url http://localhost:8000 \
  --noise none \
  --reset-before-suite \
  --poll-timeout 30 \
  --timeout 20
```

Success criteria
- `message_count=1`
- `message_dedup_count=1`
- `outbox_count=1`
- `outbox_status=PENDING|SENT`

Then run explain for produced `message_id`:

```bash
python3 ops/diagnose.py explain \
  --client-slug demo_salon \
  --message-id <message_id> \
  --minutes 60 \
  --limit 1
```

Success criteria
- `decision_meta` exists and includes `action/intent/source`.
- `decision_trace` has expected decision stage (`policy_gate:*` or flow stage).
- `outbox_latest.status` is not `FAILED`.

### 1.2 KPI baseline snapshot

```bash
python3 ops/console_owner_admin_kpi_snapshot.py \
  --client-slug demo_salon \
  --pretty \
  --output /tmp/owner_admin_wave5_t0.json
```

Optional hard-gate

```bash
python3 ops/console_owner_admin_kpi_snapshot.py \
  --client-slug demo_salon \
  --fail-on-breach \
  --fail-level critical \
  --output /tmp/owner_admin_wave5_t0_gate.json
```

Interpretation
- `kpi.guard.status=critical` => stop-the-line для owner/admin rollout решений.
- `kpi.guard.incident_class=runtime_incident` => это продуктовый/runtime инцидент.
- `kpi.guard.incident_class=external_block_only` => это внешний billing/provider block (например ChatFlow unpaid), фиксируется отдельно от runtime defects.
- Baseline path `/tmp/owner_admin_wave5_t0.json` обязателен для шага `T+24`.

## 2) T+24: replay + impact compare

### 2.1 Replay snapshot with baseline compare

```bash
python3 ops/console_owner_admin_kpi_snapshot.py \
  --client-slug demo_salon \
  --baseline /tmp/owner_admin_wave5_t0.json \
  --pretty \
  --output /tmp/owner_admin_wave5_t24.json
```

Expected output fields
- `impact.summary` (`improved|regressed|mixed_or_stable`).
- `impact.metrics.*.trend` and `delta` for:
  - `outbox_backlog`
  - `unresolved_cases`
  - `unresolved_older_than_60m`
  - `first_response_p90_seconds`

### 2.2 T+24 stop-the-line
- If `kpi.guard.status=critical` at `T+24` => incident owner + ETA обязательны.
- If `impact.summary=regressed` => rollback/remediation plan required before next UX wave.

## 3) Evidence checklist
- Log paths:
  - `livecheck-auto` output
  - `explain` output
  - `/tmp/owner_admin_wave5_t0.json`
  - `/tmp/owner_admin_wave5_t24.json`
- In session/report include:
  - absolute timestamps for `T+0` and `T+24`,
  - guard status both runs,
  - impact summary and top regressions/improvements,
  - decision owner if degraded/critical.

## 4) No-go
- Не сравнивать `T+24` с другим baseline (только `T+0` этого же merge).
- Не закрывать wave без `T+0` snapshot.
- Не интерпретировать один KPI вне guard+impact контекста.
