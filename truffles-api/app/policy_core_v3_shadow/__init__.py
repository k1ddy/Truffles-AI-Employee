"""Shadow-run for Policy-Core v3 — observation-only side-by-side execution.

Status: PoC, not wired into runtime.
Spec: SPECS/SHADOW_RUN_V3.md

The shadow path runs Policy-Core v3 in parallel with the legacy
intent_service for the same turn. It never affects the customer reply.
Output is captured as a typed `ComparisonRecord` for offline analysis.

Public surface:
- `LegacyTurnContext` — minimum bridge from legacy state to v3 inputs.
- `to_policy_turn_input` — pure builder.
- `SyncToAsyncLLMAdapter` — wraps a sync LLM provider into an async LLMCallable.
- `ComparisonRecord`, `InMemoryArtifactSink` — typed comparison record + default sink.
- `run_shadow` — the orchestration entrypoint.
"""

from .comparison_artifact import ArtifactSink, ComparisonRecord, InMemoryArtifactSink
from .divergence import Divergence, compute_divergence
from .jsonl_sink import JsonlArtifactSink
from .legacy_projector import project_legacy_decision
from .legacy_summary import LegacySummary
from .llm_adapter import SyncLLMProvider, SyncLLMResponse, SyncToAsyncLLMAdapter
from .shadow_runner import run_shadow
from .turn_input_builder import LegacyTurnContext, to_policy_turn_input

__all__ = [
    "ArtifactSink",
    "ComparisonRecord",
    "Divergence",
    "InMemoryArtifactSink",
    "JsonlArtifactSink",
    "LegacySummary",
    "LegacyTurnContext",
    "SyncLLMProvider",
    "SyncLLMResponse",
    "SyncToAsyncLLMAdapter",
    "compute_divergence",
    "project_legacy_decision",
    "run_shadow",
    "to_policy_turn_input",
]
