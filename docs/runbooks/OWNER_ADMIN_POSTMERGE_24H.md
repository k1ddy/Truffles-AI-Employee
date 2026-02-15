# Owner/Admin Post-Merge 24H Control Loop

Purpose
- Проверить, что owner/admin изменения после merge не ухудшили бизнес-контур (SLA, эскалация, подписка, trace/meta).

When
- Сразу после merge.
- Повторно через ~24 часа.

Required evidence
- `livecheck-auto` summary + explain trace.
- KPI snapshot (`outbox pending/failed`).
- KPI sample по клиенту: `outbox_backlog`, `unresolved_cases`, `first_response_p90_seconds`.

## 1) Live-check + explain

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
- `decision_meta` exists and contains `action/intent/source`.
- `decision_trace` contains expected stage (`policy_gate:*` or relevant flow stage).
- `outbox_latest.status` is not `FAILED`.

## 2) Runtime KPI snapshot

```bash
python3 ops/console_platform_admin_kpi_snapshot.py --pretty \
  --output /tmp/owner_admin_postmerge_kpi_$(date +%Y%m%d-%H%M%S).json
```

Stop-the-line rule
- If outbox guard status is `critical`, do not declare post-merge stable.

## 3) Business KPI sample (client-level)

```bash
DB_USER=$(docker exec -i truffles_postgres_1 /bin/sh -lc 'printf %s "${POSTGRES_USER:-postgres}"')
docker exec -i truffles_postgres_1 psql -U "$DB_USER" -d chatbot -Atc "
WITH target AS (
  SELECT id FROM clients WHERE name='demo_salon' LIMIT 1
),
outbox AS (
  SELECT COUNT(*) AS outbox_backlog
  FROM outbox_messages o JOIN target t ON o.client_id=t.id
  WHERE o.status IN ('PENDING','PROCESSING')
),
hand AS (
  SELECT COUNT(*) AS unresolved_cases
  FROM handovers h JOIN target t ON h.client_id=t.id
  WHERE h.status IN ('pending','active')
),
p90 AS (
  SELECT first_response_p90_seconds
  FROM metrics_analytics_daily m JOIN target t ON m.client_id=t.id
  ORDER BY metric_date DESC LIMIT 1
)
SELECT
  (SELECT outbox_backlog FROM outbox),
  (SELECT unresolved_cases FROM hand),
  (SELECT first_response_p90_seconds FROM p90);
"
```

Interpretation
- Track deltas vs previous run, not single value in isolation.
- Record exact timestamp and values in `docs/SESSIONS/SESSION-*.md`.

## 4) Handoff checklist
- Add command outputs/log paths to session evidence.
- Mention regressions explicitly (if any).
- If degraded/critical, attach remediation owner + ETA.
