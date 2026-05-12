# Intent Vocabulary Normalization

Status: DRAFT — first version derived from full real-LLM corpus run.
Date: 2026-05-11
Owner: Top Architect
Spec: SPECS/POLICY_CORE_V3.md (consumer), SPECS/SHADOW_RUN_V3.md (motivation)

---

## 0. Why this exists

The first real-LLM shadow-run on `beauty_salon_pilot_v0.jsonl` (27 turns,
gpt-4o-mini, JSON mode) produced `intent_match_rate=0.333` while manual
inspection shows that v3 was **semantically correct in 26 of 27 turns**
(96%). The 0.333 is a vocabulary artifact, not a quality issue:

- Legacy `intent_service` uses domain-flavored labels:
  `booking_request`, `cancel_request`, `reschedule`, `medical`,
  `complaint`, `refund`, `master_query`, `discount_haggle`,
  `unsupported`, `smalltalk`, `fact_question`, `booking_manage`.
- v3 uses a closed normalized enum:
  `fact_question`, `slot_collect`, `booking_request`, `booking_manage`,
  `handoff_request`, `smalltalk`, `unsupported`, `unknown`.

These vocabularies overlap (`fact_question`, `smalltalk`, `unsupported`,
`booking_manage`, `booking_request`) but differ on routing-by-effect:

- Legacy treats every turn aiming at a future booking as `booking_request`,
  even when the bot is still **collecting slots**. v3 separates `slot_collect`
  (still asking) from `booking_request` (ready to commit / committed).
- Legacy keeps a separate label per escalation reason
  (`cancel_request`, `reschedule`, `medical`, `complaint`, `refund`).
  v3 collapses every escalation into `handoff_request` and carries the
  reason in `candidate_action.args.reason`.
- Legacy has `master_query` and `discount_haggle` as first-class intents.
  v3 treats them as `fact_question` because the bot answers from pack data.

A normalization layer is required so that:
- divergence aggregation reflects semantic agreement, not vocabulary noise;
- Phase D cutover removes legacy labels from the hot path with a clear
  mapping and audit trail;
- new verticals can extend their pack vocabulary without forking core.

This document is the binding mapping table.

---

## 1. Mapping table (binding for cutover gate)

| Legacy intent | v3 intent | Notes |
|---|---|---|
| `fact_question` | `fact_question` | identical surface |
| `smalltalk` | `smalltalk` | identical surface |
| `unsupported` | `unsupported` | identical surface |
| `booking_manage` | `booking_manage` | identical surface |
| `booking_request` (state has full required slots, ready to commit) | `booking_request` | preserved when v3 is committing |
| `booking_request` (state still missing required slots) | `slot_collect` | v3 explicitly separates collection from commit |
| `cancel_request` | `handoff_request` | with `args.reason="cancel_request"` |
| `reschedule` | `handoff_request` | with `args.reason="reschedule"` |
| `medical` | `handoff_request` | with `args.reason="medical"` |
| `complaint` | `handoff_request` | with `args.reason="complaint"` |
| `refund` | `handoff_request` | with `args.reason="refund"` |
| `legal` | `handoff_request` | with `args.reason="legal"` |
| `payment` | `handoff_request` | with `args.reason="payment"` |
| `master_query` | `fact_question` | with `evidence_refs` citing `pack:specialist:*` |
| `discount_haggle` | `fact_question` | with `evidence_refs` citing `pack:promotions` |
| (any other legacy label) | `unknown` | escalates to manual audit |

---

## 2. Required-slots discriminator for booking_request vs slot_collect

For the legacy `booking_request` row, the discriminator between mapping to
`booking_request` (commit-ready) vs `slot_collect` (still collecting) is the
pack rule `rules.required_for_booking`. The normalizer needs the active
`PackV1` to evaluate.

Algorithm:

```
required = pack.rules.required_for_booking          # e.g. ["service", "datetime", "name", "phone"]
collected = derive_collected_slot_kinds(state, legacy_summary)
if required.issubset(collected) and legacy_summary.tool_action == "calendar.book_slot":
    → booking_request
else:
    → slot_collect
```

`derive_collected_slot_kinds` is a small mapping from concrete slot keys
(`service_id`, `datetime`, `customer_name`, `customer_phone`) to the
abstract kinds in `required_for_booking`. The mapping is a closed table
in `policy_core_v3_corpus.normalize_intent`.

---

## 3. Tool-id and reason consistency

Legacy carries `tool_action` separately from `intent`. v3 carries the tool
in `candidate_action.tool`. The normalizer must preserve the legacy tool id
when v3 also chose it (most handoffs already match: `handoff.create` ↔
`handoff.create`). No normalization is needed for tool ids in v1.

For escalation reasons, the normalizer compares legacy `intent` against v3
`candidate_action.args.reason` after mapping legacy intent through the
table above. A v3 record with `intent=handoff_request` and
`args.reason="cancel_request"` matches a legacy record with
`intent="cancel_request"` semantically even though v3's enum value is
different.

---

## 4. Public surface

Module: `truffles-api/app/policy_core_v3_corpus/intent_vocabulary.py`

```python
def normalize_legacy_intent(
    legacy_intent: str,
    *,
    legacy_tool_action: str | None = None,
    state_slots: dict[str, Any] | None = None,
    required_for_booking: list[str] | None = None,
) -> str: ...

def semantic_match(
    legacy_summary: LegacySummary,
    v3_decision: PolicyDecisionV3 | DegradeVerdict,
    pack_rules: PackRulesV1 | None = None,
) -> bool: ...
```

`semantic_match` returns True if either:
- the v3 intent equals the normalized legacy intent, OR
- v3 returned `handoff_request` with `args.reason` equal to the original
  legacy intent (e.g. legacy=`cancel_request`, v3=`handoff_request` with
  `reason="cancel_request"`).

`normalize_legacy_intent` is **pure**. No I/O.

---

## 5. Aggregator extension

`policy_core_v3_corpus.aggregator.aggregate_records` will compute, in
addition to `intent_match_rate`, a `semantic_match_rate` that uses
`semantic_match`. Both must remain in the report so the team can see the
vocabulary delta.

---

## 6. Acceptance criteria

1. `normalize_legacy_intent` and `semantic_match` are pure and unit-tested.
2. On `beauty_salon_pilot_v0.jsonl` real-LLM run, the report shows:
   - `intent_match_rate ≥ 0.30` (current: 0.333)
   - `semantic_match_rate ≥ 0.90` (target ≈ 0.96 from manual audit)
3. Adding a new legacy intent label requires one Decision Ledger entry
   plus one row in §1.

---

## 7. Do-not-repeat

- Do not add per-pack normalization branches in core. The mapping is
  vocabulary-level and shared.
- Do not silently absorb unknown legacy intents as `fact_question`. They
  must map to `unknown` and surface in the histogram.
- Do not collapse `slot_collect` into `booking_request` to inflate
  match-rate. The discriminator is required.
- Do not extend the v3 enum to mirror legacy domain labels. The point of v3
  is to keep the enum minimal and route specifics into typed
  `args.reason` / `args.service_id` / etc.
