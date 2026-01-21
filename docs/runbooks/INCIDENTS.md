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
5) Record: update STATE.md with evidence and status.

Minimum evidence
- Time window + symptom
- 5-15 log lines or SQL output
- System health snapshot
- Action taken

Post-incident
- Root cause summary
- Preventative task (with Task Package)
- Update runbooks if gaps found

Notes
- Do not edit DB/trace to fabricate evidence.
