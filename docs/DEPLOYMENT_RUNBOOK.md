# Truffles Deployment Runbook

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                           │
│  truffles_internal-net                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ truffles-api │   │   qdrant     │   │  postgres, redis │ │
│  │  :8000       │   │  :6333       │   │                  │ │
│  └──────────────┘   └──────────────┘   └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
          ↓ port 8000
    Traefik → api.truffles.kz
          
┌──────────────────────────┐
│  console-web (Docker)    │  ← preferred (Traefik → console.truffles.kz)
│  :3000                   │
└──────────────────────────┘
┌──────────────────────────┐
│  console-keycloak        │  ← auth.truffles.kz (OIDC)
│  :8080                   │
└──────────────────────────┘
```

## What runs where

| Component | Runtime | Reason |
|-----------|---------|--------|
| truffles-api | Docker | Needs internal network for qdrant, postgres |
| console-web | Docker (preferred) / PM2 (legacy) | Next.js Console UI |
| console-keycloak | Docker | OIDC (auth.truffles.kz) |
| qdrant | Docker | Persistent vector storage |
| postgres | Docker | Persistent relational storage |

## Console Web (preferred: Docker + Traefik)

**Keycloak:**
```bash
docker compose -f /home/zhan/truffles-main/docker-compose.console.yml up -d console-postgres console-redis console-keycloak
```

**Console UI:**
```bash
docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web
```

**Config:**
- `console-web/.env.local` must match `console.truffles.kz` + `auth.truffles.kz`.
- `truffles-api/docker-compose.yml` sets `CONSOLE_OIDC_*`.

---

## PM2 Rules (legacy)

**DO:**
- `pm2 start npm --name console-web -- run start` (production mode)
- `pm2 save` after changes

**DON'T:**
- ❌ Never add `truffles-api` to PM2
- ❌ Never use `npm run dev` in PM2

## Docker Rules

**Restart API after code changes:**
```bash
cd /home/zhan/truffles-main/truffles-api
docker-compose build --no-cache
docker-compose up -d
```

**Check logs:**
```bash
docker logs truffles-api --tail 100 -f
```

## Health Check Commands

```bash
# API health
curl http://localhost:8000/health

# Full health (includes qdrant, postgres, outbox)
curl http://localhost:8000/admin/health/check | jq

# Frontend health  
curl http://localhost:3000/api/health/full

# PM2 status
pm2 status

# Docker status
docker ps | grep truffles
```

## Known Issues

### Qdrant connectivity
- **Symptom:** `/admin/health/check` shows `qdrant: unhealthy`
- **Cause:** DNS resolution between containers
- **Workaround:** Check network membership:
  ```bash
  docker network inspect truffles_internal-net | grep -A5 qdrant
  docker network inspect truffles_internal-net | grep -A5 truffles-api
  ```

### Outbox failed messages
- **Symptom:** `outbox.failed: N` in health check  
- **Action:** Run manual heal:
  ```bash
  curl -X POST http://localhost:8000/admin/outbox/retry-failed
  ```

## Deployment Checklist

Before merge:
- [ ] All CI checks pass (lint, tests, secret-scan)
- [ ] Local build works: `docker-compose build`
- [ ] Health check returns ok

After deploy:
- [ ] `docker logs truffles-api` shows "Sentinel worker started"
- [ ] `/admin/health/check` shows database: healthy
- [ ] PM2 shows console-web online with 0 restarts

## Monitoring

### Stack Overview

| Component | URL | Purpose |
|-----------|-----|---------|
| Prometheus | http://localhost:9090 | Metrics storage & alerting |
| Grafana | http://localhost:3001 | Dashboards & visualization |
| Alertmanager | http://localhost:9093 | Alert routing & notifications |

### Grafana

**Login:** `admin` / password from `GRAFANA_PASSWORD` env (default: `admin`)

**Dashboards:**
- Truffles API: `/d/truffles-api`

### Alertmanager

Alerts are sent to Telegram DevOps group.

**Alert rules** (see `ops/alert_rules.yml`):

| Alert | Condition | Severity |
|-------|-----------|----------|
| APIHealthDegraded | API down 1 min | 🔴 Critical |
| DatabaseConnectionIssue | DB unavailable 1 min | 🔴 Critical |
| OutboxBacklogCritical | backlog > 100 for 2 min | 🔴 Critical |
| OutboxBacklogHigh | backlog > 50 for 5 min | 🟡 Warning |
| QdrantUnavailable | Qdrant down 5 min | 🟡 Warning |
| HighEscalationRate | rate > 0.3/5m for 10 min | 🟡 Warning |

### Available Metrics

Query at `/metrics` endpoint:

| Metric | Type | Description |
|--------|------|-------------|
| `http_request_count` | Counter | HTTP requests by method, path, status |
| `http_request_latency` | Histogram | HTTP latency in seconds |
| `http_request_in_progress` | Gauge | Concurrent requests |
| `outbox_backlog` | Gauge | Pending outbox messages |
| `outbox_latency` | Histogram | Outbox wait time |
| `llm_time` | Histogram | LLM call latency |
| `escalation_count` | Counter | Escalations triggered |

### Restart Monitoring Stack

```bash
cd /home/zhan/infrastructure
docker compose -f docker-compose.truffles.yml restart prometheus alertmanager grafana
```
