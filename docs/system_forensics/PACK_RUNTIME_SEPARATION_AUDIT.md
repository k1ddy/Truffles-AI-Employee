# Pack Runtime Separation Audit

Fresh primary deep-audit companion: `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`

## Purpose
Explain where the repo still mixes data truth with product behavior.

## Desired separation
- packs should hold domain truth and declarative configuration
- runtime should hold reusable mechanisms
- tenant/domain growth should prefer manifests and registries over core branching

## Current drift
The system still contains places where factual branch behavior is effectively encoded in helper logic rather than in a clean declarative fact contract.

The clearest visible example is factual reply composition:
- domain truth exists in pack-like data
- but combined reply behavior still lives in runtime/helper code

## Why this matters
When packs and runtime are not cleanly separated, each new domain nuance invites another branch in core logic.
That is exactly the anti-pattern the current program is trying to stop.

## Research question
What part of fact behavior belongs in data manifests versus reusable renderers versus runtime boundary policy?

## Key evidence anchors
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_services_intent_service.md`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `docs/system_forensics/final/TARGET_DECISION.md`
