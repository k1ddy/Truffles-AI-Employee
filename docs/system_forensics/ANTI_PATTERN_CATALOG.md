# Anti Pattern Catalog

## Purpose
Record the specific failure modes that earlier work already proved harmful and that future implementation must avoid.

## Main anti-patterns
1. `scenario patching`
   - fixing one dialog or one turn as if it were the architecture unit
2. `phrase hardcode in core`
   - using literal text branching as the main semantic engine
3. `document-only architecture`
   - having the right narrative without a machine-readable or executable contract
4. `boundary as semantic router`
   - using validation/degrade logic to invent or repair business meaning
5. `pack behavior in code`
   - putting domain-specific reply behavior in runtime helpers instead of data/manifests
6. `mixed truth carriers`
   - allowing multiple co-equal semantic state sources to coexist
7. `god-file migration`
   - calling a file “legacy” while it still hosts live authority
8. `test as surrogate architecture`
   - relying on tests to freeze behavior that has no clear architecture object underneath

## Why this catalog exists
Earlier external-facing documents described many problems correctly, but they did not always turn those findings into explicit anti-repeat rules for future implementers.

## Evidence anchors
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
