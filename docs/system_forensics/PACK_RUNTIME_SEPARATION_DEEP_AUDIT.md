# Pack Runtime Separation Deep Audit

Status: `open_first_pass`
Purpose: explain exactly where the repo still mixes pack truth, pack-specific behavior, and runtime execution authority.

## What this document covers
This is the fresh primary deep audit for pack/runtime separation.
It answers:
- where truth loading ends and behavior begins,
- where pack-specific logic still sits in generic runtime paths,
- where the repo already has salvageable pack-agnostic pieces,
- and why the fact-side architecture gap is larger than one `parking` symptom.

## Desired separation
The intended model is simple:
- packs hold truth and declarative configuration;
- runtime holds reusable mechanisms;
- tenant/domain differences live in manifests, capabilities, and adapters, not in core branching.

The live repo still does not consistently meet that model.

## Current separation stack
### Layer 1. Runtime primes pack truth before turn execution
`truffles-api/app/core/consultant_runtime.py:_prime_runtime_context`
- loads runtime capabilities via `capabilities_runtime.py`
- loads runtime truth via `knowledge_runtime.py`
Meaning:
- pack truth is injected into runtime context early.
- this is acceptable, but it means later fact behavior is inseparable from runtime state unless a strict renderer contract exists.

### Layer 2. Pack facade exposes retrieval and reply helpers
`truffles-api/app/services/pack_runtime_service.py`
- owns runtime retrieval-mode logic such as `runtime_local`, `backend_shadow`, `backend_primary`, and fallback metadata
- exposes `build_master_reply_from_pack(...)`, `format_reply_from_truth(...)`, and `get_pack_decision(...)`
Meaning:
- the facade already does something useful: it centralizes retrieval observability and runtime source metadata.
- but it does not by itself guarantee exact fact scope or fact-side pack neutrality.

### Layer 3. Generic adapter dispatch is still module-code dispatch
`truffles-api/app/services/pack_runtime_default.py`
- `_resolve_adapter(client_slug)` maps slugs to Python modules
- forwards many behavior APIs into the adapter module:
  - `build_info_combined_reply(...)`
  - `format_reply_from_truth(...)`
  - `get_pack_decision(...)`
  - service and signal helpers
Meaning:
- tenant resolution is still code-module dispatch, not one narrow data-driven contract.
- the adapter seam exists, but behavior is still whatever the selected module decides to do.

### Layer 4. Demo adapters preserve demo-specific behavior as the default executable path
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
Meaning:
- the repo already has explicit adapter modules whose only job is to re-export demo-salon behavior.
- this is a clear sign that tenant behavior is still encoded as Python modules, not only as pack manifests.

### Layer 5. Demo pack module still behaves like a behavior engine
`truffles-api/app/services/demo_salon_knowledge.py`
- defaults to `_DEFAULT_CLIENT_SLUG = "demo_salon"`
- falls back to `INTENTS_PHRASES_DEMO_SALON.yaml` and `demo_salon_intents`
- defines signal detection for hours, parking, location, contact, pricing, and duration
- implements `build_info_combined_reply(...)`
- implements `get_pack_decision(...)`
- embeds Qdrant-backed service-search behavior such as `_SERVICES_COLLECTION` and `_QDRANT_HOST`
- widens some single intents such as `location`, `hours`, and `parking` into combined replies
Meaning:
- this module is not only truth data.
- it is a mixed domain behavior engine with lexicon logic, classification, composition, and rendering.

### Layer 6. Legacy webhook info path still co-owns factual behavior
`truffles-api/app/routers/webhook/info.py`
- imports pack-oriented helpers such as `_has_parking_signal`, `_has_contact_signal`, and `build_info_combined_reply(...)`
- contains `_detect_location_policy_pack_refs(...)`
- contains `_build_info_intent_reply(...)`
- still decides when to produce combined location/hours/parking bundles
Meaning:
- pack/runtime separation does not stop at the adapter seam.
- legacy webhook info helpers still co-own fact selection and rendering.

### Layer 7. Neutral adapter proves a healthier local model already exists
`truffles-api/app/services/pack_runtime_neutral_adapter.py`
- loads YAML truth and policy pack data without importing demo-specific knowledge modules
- uses a small deterministic contract for generic facts like `location`, `hours`, and `parking`
Meaning:
- the repo already contains a cleaner counterexample.
- this file shows that the target direction is possible without a big rewrite.

## Strongest leakage examples
### Leakage 1. Slug selects a code module, not only a data manifest
`pack_runtime_default._resolve_adapter(...)` means the runtime delegates behavior to Python modules named per tenant/domain.
That is more dynamic than hardcoded `if demo_salon`, but it is still code-selected behavior, not only data-selected behavior.

### Leakage 2. Demo-salon defaults still leak into generic runtime assumptions
`demo_salon_knowledge.py` defaults to `demo_salon` slug and demo-specific intent phrase fallbacks.
That means even the fallback behavior of the pack layer is still demo-centered in several places.

### Leakage 3. Demo pack code still contains direct factual business behavior
`demo_salon_knowledge.py` performs:
- signal interpretation
- info-intent inference
- composition rules
- fallback reply selection
- direct decision building
This is where truth and behavior are most visibly fused.

### Leakage 4. Runtime info helper still owns factual widening
`webhook/info.py` still chooses whether location/hours/parking/contact become standalone or combined replies.
That means one of the most important product semantics on the fact side still lives in a legacy runtime helper, not in a strict fact contract.

### Leakage 5. Retrieval observability is strong, but emitted fact scope is not enforced
`pack_runtime_service.py` tracks `retrieval_mode`, `selected_source`, and `fallback_reason`.
That is good.
But the runtime still lacks a governing object for requested fact ids versus emitted fact ids.

## Salvage versus rewrite
### Salvageable pieces
- `knowledge_runtime.py`
  - useful as runtime truth loader
- `pack_runtime_service.py`
  - useful as retrieval-source and observability facade
- `pack_runtime_neutral_adapter.py`
  - strongest local example of cleaner separation
- `compile_pack_payload(...)` in `pack_compiler_service.py`
  - useful basis for stricter pack manifests

### Split or replace candidates
- `pack_runtime_default.py`
  - keep the facade role, but narrow adapter authority to a stricter manifest-based contract
- `pack_runtime_demo_adapter.py`
- `pack_runtime_demo_salon_adapter.py`
  - remove the need for demo-only re-export adapters by narrowing the shared fact contract
- `demo_salon_knowledge.py`
  - split truth/config from semantic classification and composition logic
- `webhook/info.py`
  - drain factual composition authority into a dedicated fact resolver/renderer contract

### Why this is not a rewrite fantasy
The repo already has:
- compiled pack payloads,
- runtime truth loading,
- a neutral adapter,
- and typed owner outputs carrying `pack_refs`.
The missing piece is not invention from zero. It is the materialization of one executable fact contract across these layers.

## Main verdicts
### Verdict 1. Pack/runtime separation is still incomplete at exactly the seams that matter for product facts
The biggest visible symptom is over-composed info replies.
The deeper problem is that fact behavior is still split across adapter dispatch, pack code, runtime helpers, and legacy info orchestration.

### Verdict 2. The adapter seam is necessary but not sufficient
Adapters alone do not guarantee pack-agnostic runtime behavior.
They only move the branch point unless the adapter contract is kept narrow and declarative.

### Verdict 3. The neutral adapter shows the right direction better than the demo pack module does
The cleanest current separation example is `pack_runtime_neutral_adapter.py`, not the demo-specific knowledge module.
That is an important architecture clue.

### Verdict 4. Fact architecture remains the first implementation candidate for architecture recovery
This audit reinforces the earlier fact-runtime deep audit.
The fact-side path still lacks one governing object for:
- requested fact ids
- allowed standalone/composite combinations
- emitted fact refs
- render policy
- fallback rules

## Main blockers surfaced by this audit
- slug-to-module dispatch still selects behavior in code
- demo-salon defaults and demo-only adapter modules still leak into the generic runtime path
- demo pack module still mixes data, classification, composition, and rendering
- `webhook/info.py` still co-owns factual composition rules
- retrieval-source observability exists, but exact emitted fact scope does not

## Evidence anchors
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/tool_registry_service.py`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_services_intent_service.md`
