# Runbook: Incidents

Purpose
- Provide a repeatable incident process with evidence.

When to declare
- Customer-impacting outage
- Message delivery failure
- Security or data isolation risk

Process
1) Declare incident and owner (single person).
2) Triage: identify scope (tenant/branch), time window, symptom.
3) Mitigate: rollback, restart, rate limit, or disable noisy path.
4) Verify: evidence via /admin/health, SQL, logs, trace.
   - For message-chain issues, capture `ops/diagnose.py trace-bundle` output.
   - Pull `timing.stages` for controller/RAG/dedup/outbox to localize latency.
5) Record: update STATE.md with evidence and status.

Monitoring quick checks
```bash
curl -s http://localhost:9090/api/v1/targets | python3 - <<'PY'
import json, sys
data = json.load(sys.stdin)
for t in data.get("data", {}).get("activeTargets", []):
    if t.get("labels", {}).get("job") == "truffles-api":
        print("truffles-api:", t.get("health"), t.get("lastError", ""))
PY
```

```bash
curl -s http://localhost:9090/api/v1/alerts | python3 - <<'PY'
import json, sys
data = json.load(sys.stdin)
alerts = data.get("data", {}).get("alerts", [])
for a in alerts:
    if a.get("state") == "firing":
        print(a.get("labels", {}).get("alertname"), a.get("annotations", {}).get("summary", ""))
PY
```

```bash
curl -s http://localhost:3200/metrics | rg -m 1 tempo_distributor_spans_received_total
```

Minimum evidence
- Time window + symptom
- 5-15 log lines or SQL output
- System health snapshot
- Trace-bundle JSON path (if message-chain related)
- timing.stages snapshot (e.g., controller_llm_ms, rag_ms, outbox_process_ms)
- Action taken

Post-incident
- Root cause summary
- Preventative task (with Task Package)
- Update runbooks if gaps found

Notes
- Do not edit DB/trace to fabricate evidence.
