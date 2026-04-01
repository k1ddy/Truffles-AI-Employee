# Failure Family Atlas

## Purpose
Summarize the main consultant-core failure families at the level external researchers need: by mechanism class, not by isolated dialog IDs.

## Product-practical lane families
- `owner-side booking service grounding`
  - mechanism class: owner grounding / slot carry
  - current status: closed as scoped
- `collect to commit stale service reprompt`
  - mechanism class: booking collect to commit transition
  - current status: closed as scoped
- `booking datetime continuity under degrade`
  - mechanism class: boundary continuity preservation
  - current status: closed as scoped
- `live check-booking temporal clue continuity`
  - mechanism class: booking-manage continuity through degraded follow-up
  - current status: closed as scoped
- `booking verification confirm recovery`
  - mechanism class: degrade-time confirm continuity
  - current status: closed as scoped
- `parking owner grounding`
  - mechanism class: owner branch-fact specificity
  - current status: closed as scoped
- `fact over-composition on location/parking replies`
  - mechanism class: fact selection / fact composition
  - current status: open as visible weak residue

## Architecture-level families
- distributed semantic ownership
- multiple truth carriers
- boundary semantic leakage
- mixed pack/runtime behavior
- live legacy compatibility mesh
- duplicated operational entrypoints

## Why the atlas matters
Earlier work often knew the family names.
The missing step was converting those families into a stable external explanation of:
- which ones are product-path blockers
- which ones are architectural blocker classes
- which ones are oracle/evaluator residue

## Evidence anchors
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
