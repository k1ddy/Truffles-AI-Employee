# Code Topology Audit

Fresh primary deep-audit companion: `docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md`

## Purpose
Show why the current repo shape still encourages local repair even after meaningful architecture recovery work.

## Main topology problem
Too many live semantic and continuity concerns are still concentrated in large compatibility-era files.

Important hotspots:
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/services/intent_service.py`

## Why size alone is not the issue
The main problem is not line count by itself.
The main problem is mixed authority:
- orchestration
- continuity repair
- legacy compatibility
- reply shaping
- boundary logic
- and domain-specific residue

all still cohabit the same files.

## Architectural consequence
Even when the target direction is known, the current topology still makes one more local branch feel cheap.
That is why truthful audits and bad implementations were able to coexist.

## Required response
External researchers should evaluate not only target components, but also the migration shape needed to drain authority out of these hotspots without a blind rewrite.

## Key evidence anchors
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_services_intent_service.md`
