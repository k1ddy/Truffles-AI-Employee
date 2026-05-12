# pack_v1 — PoC

**Status:** PoC, not wired into runtime.
**Spec:** [`SPECS/PACK_V1.md`](../../../SPECS/PACK_V1.md)

A single typed loader over `packs/<pack_id>/pack.yaml` that replaces the seven
legacy `pack_runtime_*_adapter.py` modules with declarative data.

## Files

| File | Responsibility |
|---|---|
| `schema.py` | Pydantic models: `PackV1`, `PackBusiness`, `PackRulesV1`, `PackService`, `PackSpecialist`, `PackToolContract` |
| `loader.py` | Pure `load_pack(path) -> PackV1` |
| `pack_view_adapter.py` | `to_pack_view(pack) -> StaticPackView` for `policy_core_v3` |
| `errors.py` | `PackLoadError` |

## Invariants

- Pure: no DB, no network, no LLM.
- Strict: extra fields rejected; cross-references validated.
- Vertical-agnostic: same shape for salons, clinics, auto, etc.
- Compatible with `policy_core_v3.PackView` Protocol via `to_pack_view`.

## Example pack

`packs/beauty_salon_v1/pack.yaml` is the reference example.

## What this PoC does NOT do

- Read from operational DB or sync ids.
- Replace any legacy `pack_runtime_*_adapter`.
- Wire into `consultant_runtime`.
- Ingest knowledge files into RAG (referenced paths are only verified to exist).
