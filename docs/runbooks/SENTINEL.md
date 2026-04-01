# Runbook: Sentinel

Purpose
- Detect silent failures (inbound without outbound, infra health regressions).

Checks
```bash
docker ps | rg truffles-sentinel
```

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/admin/health
```

Common alerts
- inbound received but no outbound
- provider down (ChatFlow/Qdrant)

Recovery steps
1) Restart sentinel
```bash
docker restart truffles-sentinel
```

2) Validate health endpoints
```bash
curl -s http://localhost:8000/admin/health | jq .
```

Evidence to capture
- Sentinel logs (last 100 lines)
- Health endpoint snapshots
- Outbox status if alert relates to delivery

Notes
- Sentinel should not be the only signal; confirm with SQL or admin health.
- Keep a single sentinel instance to avoid duplicate alerts.
