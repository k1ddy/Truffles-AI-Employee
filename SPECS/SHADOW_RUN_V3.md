# Shadow-Run for Policy-Core v3 — Specification

Status: DRAFT (PoC, not wired)
Owner: Top Architect
Phase: B.1
Date: 2026-05-11
Related: SPECS/POLICY_CORE_V3.md, SPECS/PACK_V1.md

---

## 0. Why this exists

Policy-Core v3 (`SPECS/POLICY_CORE_V3.md`) and PackV1 (`SPECS/PACK_V1.md`)
are landed as isolated PoCs. To gain confidence before cutover, v3 must run
**alongside** the legacy `intent_service` for the same turn, with both
decisions captured and compared. This specification defines the shadow-run
mechanism.

This is **observation only**: legacy still owns the customer reply. v3
output is captured for analysis; it never reaches the customer in this
phase.

---

## 1. Hard rules

1. The shadow path must not affect customer-facing behavior. Legacy owns
   the reply; legacy errors must surface as today; v3 errors must never
   propagate to the customer.
2. The shadow path must not block the hot path. v3 invocation runs without
   adding more than a configurable budget (default: 0 ms blocking — fire
   and forget if needed; configurable to inline-await for offline runs).
3. The shadow path is **off by default**. Gated by
   `settings.policy_core_v3_enabled` (already exists, default `False`).
4. The shadow module must not import from `app/services/`, `app/core/`, or
   `app/adapters/`. It depends only on `app/policy_core_v3/` and
   `app/pack_v1/`. (Static guard test enforces this.)
5. The shadow module must not perform DB writes. It writes only to the
   comparison artifact sink (function injected by the caller).
6. The shadow module must not introduce scenario-specific logic. Same rule
   as v3.

---

## 2. Boundaries with neighbors

```
                   consultant_runtime (LEGACY)
                            │
                ┌───────────┼────────────┐
                ▼                        ▼
        intent_service.run        shadow_runner.run_shadow
        (legacy decision)         (v3 decision via invoker)
                │                        │
                ▼                        ▼
         (customer reply)         comparison_artifact_sink
```

`shadow_runner.run_shadow(...)` is the only public entrypoint for
production wiring (Phase B.2). It is also directly callable from
standalone dry-run scripts and tests.

---

## 3. Public surface

### `LegacyTurnContext` (dataclass)

The minimum bridge from existing legacy state to v3 inputs. Caller fills
this from whatever data sources the legacy runtime already has.

| Field | Type | Notes |
|---|---|---|
| `tenant_id` | str | |
| `conversation_id` | str | |
| `current_message` | str | |
| `history` | list[Turn] | role/text |
| `state_slots` | dict[str, Any] | |
| `pack` | `PackV1` | Loaded via `pack_v1.load_pack` upstream |
| `evidence_bundle` | list[EvidenceItem] | Empty list is allowed; populated upstream when available |
| `now` | datetime | tz-aware |
| `locale` | str | falls back to `pack.locale` |
| `policy_version` | str | for trace pinning |

### `to_policy_turn_input(ctx) -> PolicyTurnInput`

Pure function. Builds a v3 `PolicyTurnInput` from `LegacyTurnContext` by
adapting the pack via `pack_v1.to_pack_view` and copying tools from the
pack's tool contracts.

### `SyncLLMProvider` (Protocol)

Local Protocol matching the synchronous shape of the legacy
`LLMProvider.generate(...)`. The shadow module duck-types against it; no
import dependency on `app.services.llm`.

### `SyncToAsyncLLMAdapter`

Wraps a `SyncLLMProvider` into a `policy_core_v3.LLMCallable` (async
single-arg callable returning `str`). Translates `TimeoutError` and
generic exceptions into `LLMTimeout` / `LLMProviderError` (defined in
`policy_core_v3.invoker`) so the v3 retry policy can route them
deterministically.

Configurable parameters per instance:
- `model`
- `temperature`
- `max_tokens`
- `timeout_seconds`
- `response_format` (passed verbatim if non-None)

### `ComparisonRecord` (pydantic model)

A typed snapshot of one shadow-run turn:

| Field | Type | Notes |
|---|---|---|
| `tenant_id` | str | |
| `conversation_id` | str | |
| `turn_index` | int | from caller |
| `current_message` | str | |
| `legacy_summary` | dict | freeform projection of legacy decision (intent, action, message_text, rescue, degrade) |
| `v3_outcome_kind` | str | `decision` or `degrade` |
| `v3_decision` | dict \| None | `PolicyDecisionV3.model_dump()` if successful |
| `v3_degrade` | dict \| None | `DegradeVerdict.model_dump()` if degraded |
| `v3_latency_ms` | float | wall-clock, async |
| `v3_attempts` | int | 1 or 2 |
| `policy_version` | str | from `PolicyTurnInput.policy_version` |
| `pack_id` | str | |
| `pack_version` | int | |
| `captured_at` | datetime | UTC |
| `notes` | str | freeform |

### `ArtifactSink` (Protocol)

```python
class ArtifactSink(Protocol):
    async def emit(self, record: ComparisonRecord) -> None: ...
```

The default sink is in-memory list (for tests/dry-run). Production sink
will write to a JSONL file or Postgres table; out of scope for B.1.

### `shadow_runner.run_shadow(...)`

```python
async def run_shadow(
    *,
    ctx: LegacyTurnContext,
    legacy_summary: dict,
    invoker: PolicyCoreV3Invoker,
    sink: ArtifactSink,
    turn_index: int = 0,
    notes: str = "",
) -> ComparisonRecord
```

Behavior:
1. Build `PolicyTurnInput` from `ctx`.
2. Measure wall-clock time around `invoker.invoke(...)`.
3. Translate result (decision or degrade) into a `ComparisonRecord`.
4. Call `sink.emit(record)`.
5. Return the record (also for callers that want to log it inline).

`run_shadow` never raises into the caller. Any internal exception is
caught, translated into a `ComparisonRecord` with `v3_outcome_kind = "degrade"`,
`v3_degrade.degrade_reason = "provider_error"`, and the trace included in
`notes`. This guarantees rule §1: shadow never affects the hot path.

---

## 4. Wiring plan (Phase B.2, NOT this session)

In `consultant_runtime`, after the legacy decision is computed and **before**
the customer reply is sent, insert:

```python
if settings.policy_core_v3_enabled:
    asyncio.create_task(
        shadow_runner.run_shadow(
            ctx=legacy_to_shadow_ctx(...),
            legacy_summary=legacy_summary_from(decision),
            invoker=shadow_invoker,
            sink=shadow_sink,
            turn_index=turn_index,
        )
    )
```

This is one block, fully gated by the flag, fire-and-forget. It does not
await the v3 result.

The `legacy_to_shadow_ctx(...)` projector and the `shadow_invoker` /
`shadow_sink` singletons are constructed at runtime startup. They are out
of scope for B.1.

---

## 5. Acceptance criteria for B.1 (this session)

1. `python3 -m py_compile` succeeds on all new files.
2. `pytest truffles-api/tests/policy_core_v3_shadow/ -q` passes.
3. The new module imports nothing from `app.services`, `app.core`,
   `app.adapters` (static guard test).
4. `scripts/policy_core_v3_shadow_dryrun.py` runs end-to-end on the
   `packs/beauty_salon_v1/` example with a mock LLM and prints a JSON
   `ComparisonRecord` to stdout.
5. No file in `truffles-api/app/services/`, `truffles-api/app/core/`, or
   `truffles-api/app/main.py` is modified.
6. `decision_ledger_guard`, `tool_inventory_guard`,
   `single_semantic_owner_guard` return OK.
7. A Decision Ledger entry records the PoC and lists do-not-repeat items.

---

## 6. Acceptance criteria for B.2 / B.3 (later sessions)

- B.2: one-block hook in `consultant_runtime` behind the feature flag,
  with a real `legacy_to_shadow_ctx` projector and a JSONL sink. Demo
  data converted into `packs/beauty_salon_v1/pack.yaml`.
- B.3: shadow-run executed against the owner-approved internal pilot
  corpus; comparison artifact reviewed; ledger entry recording either
  cutover gate satisfaction or the next mechanism repair.

---

## 7. Do-not-repeat (binding)

- Do not let the shadow path block or affect the customer reply.
- Do not introduce scenario-specific code anywhere in shadow modules.
- Do not import legacy `intent_service`, `consultant_runtime`, or any
  `pack_runtime_*_adapter` into the shadow module.
- Do not use the shadow path as a "second chance" rescue for legacy
  failures. It is observation only.
- Do not silently absorb v3 errors as success. Errors become typed
  `DegradeVerdict` records in the artifact.
- Do not remove the static independence guard test.
