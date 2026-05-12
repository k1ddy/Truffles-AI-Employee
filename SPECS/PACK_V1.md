# PackV1 — Tenant Pack Specification

Status: DRAFT (PoC, not wired)
Owner: Top Architect
Classification: REPLACE for the 7 legacy `pack_runtime_*_adapter.py` modules
Date: 2026-05-11
Related: SPECS/POLICY_CORE_V3.md (consumer)

---

## 0. Why this exists

The current pack runtime is split across seven adapters — `pack_runtime_compat`,
`pack_runtime_default`, `pack_runtime_demo_adapter`,
`pack_runtime_demo_salon_adapter`, `pack_runtime_fallback_adapter`,
`pack_runtime_generic_adapter`, `pack_runtime_neutral_adapter` — plus
per-vertical knowledge directories (`demo_salon`, `clinic_pack`, `dental_pack`,
`generic`) with heterogeneous YAML/MD shapes (`SALON_TRUTH.yaml`,
`INTENTS_PHRASES_*.yaml`, `EVAL.yaml`, `POLICY.md`, etc.).

Consequences:

- vertical content lives partially in code (adapters), violating AGENTS §8
  ("tenant/pack differences belong in data, not in core");
- there is no single contract telling a future agent or owner what a "pack"
  is;
- each new vertical requires picking which adapter to clone, which is the
  scenario-fix antipattern in another shape;
- knowledge YAML files mix pack data, lexicon evidence, eval cases, and
  prompt fragments under one roof.

PackV1 is a single declarative tenant manifest with a typed loader and a
strict validation pass. Verticals scale by adding pack files, not code.

---

## 1. Position in the architecture

```
packs/<pack_id>/pack.yaml      ← canonical declarative source
   ↓
PackV1 loader (pure)           ← validates → typed PackV1
   ↓
PackV1                         ← consumed by:
                                  - Policy-Core v3 (via PackView Protocol)
                                  - Boundary (rules)
                                  - Evidence layer (services/aliases)
                                  - Capability registry (allowed capabilities)
                                  - Console (read-only display)
```

PackV1 is read-only at runtime. Console mutates the underlying source; a new
snapshot is loaded by tenants on activation. Versioning is explicit
(`pack_version` field) so that boundary/Policy-Core v3 can pin a version per
turn for trace.

---

## 2. Hard rules

1. PackV1 is **declarative data**, never code. No Python files inside
   `packs/`.
2. PackV1 must be sufficient for: policy-core prompt, boundary rules,
   evidence-layer aliases, Console display, and capability advertisement —
   without any vertical-specific Python.
3. PackV1 must be **vertical-agnostic** in shape. The same schema serves
   beauty salons, clinics, auto services, etc. Vertical specifics live in
   the data, not in extra fields.
4. PackV1 must be **locale-explicit**. A pack declares its primary locale
   and may carry localized strings for customer-facing fields.
5. PackV1 must be **linked to operational DB by id**, not by name. Service
   ids and specialist ids in the pack match the operational DB rows; the
   pack carries display/aliasing/policy, the DB carries availability and
   appointment state.
6. PackV1 must validate offline. The loader is pure: file → validated
   PackV1 or error. No DB, no LLM, no network.
7. PackV1 must satisfy the `PackView` Protocol from `policy_core_v3` so
   that v3 can consume it without a shim.

---

## 3. Top-level structure

A pack is a directory: `packs/<pack_id>/`.

| File | Required | Purpose |
|---|---|---|
| `pack.yaml` | yes | The canonical PackV1 manifest (this spec) |
| `knowledge/*.md` | optional | Free-form FAQ/policy text for RAG; referenced by `knowledge_sources` |
| `aliases.yaml` | optional | Extended alias tables for evidence layer |

`pack.yaml` is the only file with structural contract. `knowledge/` and
`aliases.yaml` are content fed into upstream layers (RAG / evidence) and are
not consumed directly by Policy-Core v3.

---

## 4. `pack.yaml` schema

Top-level fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `pack_id` | string | yes | Stable id, e.g. `beauty_salon_v1`, `clinic_v1` |
| `pack_version` | int | yes | Monotonic; bump on any non-additive change |
| `vertical` | string | yes | Free-form label, e.g. `beauty_salon`, `clinic` |
| `locale` | string | yes | BCP-47, e.g. `ru-KZ` |
| `business` | object | yes | See §4.1 |
| `rules` | object | yes | See §4.2 |
| `capabilities` | string[] | yes | Subset of: `FACT`, `COLLECT`, `BOOKING`, `MANAGE`, `HANDOFF` |
| `services` | object[] | yes | See §4.3 |
| `specialists` | object[] | yes (may be empty) | See §4.4 |
| `tools` | object[] | yes | Tool contracts available to this pack — see §4.5 |
| `knowledge_sources` | string[] | optional | Relative paths under the pack dir for RAG ingestion |
| `aliases` | object | optional | See §4.6 |

Unknown top-level fields are an error. The loader is strict.

### 4.1 `business`

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Display name |
| `summary` | string | yes | 1–3 sentences in `locale`, used by Policy-Core v3 in the system header |
| `address` | string | optional | Free-form |
| `hours` | string | optional | Free-form, customer-readable |
| `contacts` | object | optional | `{phone?, instagram?, website?}` |
| `branches` | object[] | optional | Multi-branch businesses; each `{id, name, address}` |

### 4.2 `rules`

| Field | Type | Required | Notes |
|---|---|---|---|
| `bot_can_confirm` | bool | yes | Whether the bot may finalize bookings/cancellations without admin |
| `required_for_booking` | string[] | yes | Slot ids needed before booking commit, e.g. `["service", "datetime", "name", "phone"]` |
| `identity_for_lookup` | string[] | yes | At least one of these must be present to disclose an existing appointment, e.g. `["name_or_phone"]` |
| `escalate_topics` | string[] | yes | Topic labels that force handoff (e.g. `medical`, `refund`, `complaint`, `legal`) |
| `cancellation_policy` | string | optional | Customer-facing text |
| `reschedule_policy` | string | optional | Customer-facing text |

### 4.3 `services` (each item)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable id, matches operational DB |
| `name` | string | yes | Display name in `locale` |
| `aliases` | string[] | optional | Customer-language variants for evidence/lexicon |
| `duration_min` | int | optional | |
| `price_display` | string | optional | Display string ("5000 KZT", "от 5000 тг") — numeric pricing is operational DB |
| `description` | string | optional | 1–2 sentences for FACT answers |
| `category` | string | optional | Free-form grouping |
| `escalate` | bool | optional | If true, every booking attempt for this service routes to handoff (e.g. medical procedure) |

### 4.4 `specialists` (each item)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable id, matches operational DB |
| `name` | string | yes | Display name |
| `service_ids` | string[] | yes (may be empty) | Subset of `services[].id` |
| `aliases` | string[] | optional | |
| `bio` | string | optional | Short description for FACT answers |

### 4.5 `tools` (each item)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Tool id, e.g. `calendar.book_slot`, `handoff.create` |
| `description` | string | yes | One-line description shown to the model |
| `args_schema` | object | yes | Map of arg name → kind (`text`, `text_list`, `number`, `datetime`) |
| `requires_capability` | string | optional | Pack capability gating this tool |

The set of tool ids is **closed** within a pack: Policy-Core v3 will reject
any tool not in this list (`tool_not_in_contract`).

### 4.6 `aliases`

Free-form table grouped by domain, e.g.:

```yaml
aliases:
  service:
    brows: ["брови", "бровки", "оформление бровей"]
  time:
    morning: ["утром", "с утра"]
```

This block is consumed by the upstream **evidence layer**, not by
Policy-Core v3. Policy-Core v3 receives the resolved evidence as
`evidence_bundle`. It is included in PackV1 because it is tenant data, not
core code.

---

## 5. Loader contract

`load_pack(path: pathlib.Path) -> PackV1` — pure function.

Failure modes (raised as `PackLoadError`):

- file missing or unreadable
- YAML parse error
- pydantic validation error (typed message; field path included)
- duplicate `services[].id` or `specialists[].id`
- `specialists[*].service_ids` references a missing service id
- `tools[*].requires_capability` references a missing capability
- empty `pack_id`, empty `services` (a pack with no services is not viable
  for Beauty Salon v1 acceptance — relax later if needed)

The loader does not read `knowledge/*.md` or `aliases.yaml` content beyond
verifying paths exist. RAG ingestion is downstream.

The loader does not consult the operational DB. ID consistency with the DB
is the responsibility of pack-activation, which is out of scope for v1.

---

## 6. PackView compatibility

`PackV1` exposes a `pack_view(self) -> PackView` method (or properties
matching the Protocol) so that Policy-Core v3 can consume it directly:

- `pack_id` ↔ `PackV1.pack_id`
- `services` ↔ map `services[*]` to `policy_core_v3.ServiceView`
- `specialists` ↔ map `specialists[*]` to `policy_core_v3.SpecialistView`
- `rules` ↔ build `policy_core_v3.PackRules` from `rules` block
- `business_summary` ↔ `business.summary`

A unit test asserts that a loaded `PackV1` is a structural `PackView`.

---

## 7. Migration plan from legacy adapters

### Phase A — PoC (this session)
- `SPECS/PACK_V1.md` (this document).
- `truffles-api/app/pack_v1/` with `schema.py`, `loader.py`, `errors.py`,
  `pack_view_adapter.py`.
- `packs/beauty_salon_v1/pack.yaml` example.
- Unit tests under `truffles-api/tests/pack_v1/`.
- Not wired into runtime.

### Phase B — Migrate demo data
- Convert `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml` into
  `packs/beauty_salon_v1/pack.yaml` while keeping `demo_salon/` untouched.
- Validate cross-references against operational DB rows for the canary
  tenant.
- Expose new pack via Console read-only.

### Phase C — Replace runtime callers
- One legacy `pack_runtime_*_adapter` at a time: redirect callers to a thin
  shim built on PackV1, behind a per-call feature flag.
- Compare outputs on the approved corpus.

### Phase D — Cleanup
- Delete all 7 `pack_runtime_*_adapter.py` files.
- Delete `pack_runtime_compat.py`, `demo_salon_knowledge_compat.py`.
- Delete vertical-specific knowledge YAMLs once their content lives in pack
  files.
- Remove pack-related compatibility carriers from
  `compatibility_carrier_inventory.json`.

---

## 8. Acceptance criteria for the PoC

1. `python3 -m py_compile` succeeds on all new files.
2. `pytest truffles-api/tests/pack_v1/ -q` passes.
3. The loader is pure (no DB, no network, no LLM).
4. `packs/beauty_salon_v1/pack.yaml` validates and yields a `PackV1`
   instance.
5. The same `PackV1` instance, fed through `pack_view_adapter`, satisfies
   `policy_core_v3.PackView` (asserted by isinstance against the Protocol
   and by a smoke test that builds a Policy-Core v3 prompt from it).
6. No file in `truffles-api/app/services/` or `truffles-api/app/core/` is
   modified.
7. No legacy `pack_runtime_*_adapter` is touched.
8. A Decision Ledger entry records the PoC.

---

## 9. Acceptance criteria for production cutover (Phase D)

1. All legacy `pack_runtime_*_adapter.py` files deleted.
2. All tenants in canary load packs through `pack_v1.loader.load_pack`.
3. Cross-tenant smoke pack (clinic, auto, salon) demonstrates that adding
   a vertical requires only a new pack directory.
4. Boundary rules and Policy-Core v3 read all tenant data through PackV1.
5. Console can render a PackV1 pack read-only without bespoke per-vertical
   code.

---

## 10. Open questions

- **Q1**: Should `services[].price_display` be replaced by a typed price
  table once operational pricing lives in DB? Tentative answer: yes;
  `price_display` is a transitional field and will be removed when
  `services` table owns price.
- **Q2**: Multi-branch + multi-locale: should a pack be a single file with
  conditional sections, or one pack per branch+locale? Tentative answer:
  one pack per `(business, locale)`; branches are sub-objects in
  `business.branches`.
- **Q3**: How to express "service requires identity at lookup but not at
  booking"? Today `rules.identity_for_lookup` is global. If per-service
  rules emerge, add `services[].rules` with same shape.
- **Q4**: Compatibility with existing operational DB ids — handled by
  pack-activation outside the loader. Out of scope here.

---

## 11. Do-not-repeat (binding)

- Do not put pack-specific Python in `truffles-api/app/services/` or
  `truffles-api/app/core/`. New pack content goes in `packs/<id>/`.
- Do not create a new `pack_runtime_<niche>_adapter.py`. The contract is
  one loader + data files.
- Do not put booking decision policy in pack data. Pack data declares
  rules; boundary enforces them; policy-core decides intent.
- Do not embed lexicon decisions in pack code. Aliases stay as data
  consumed by the evidence layer.
- Do not break the PackView Protocol contract. If v3 needs more, extend
  the Protocol explicitly with a Decision Ledger entry.
