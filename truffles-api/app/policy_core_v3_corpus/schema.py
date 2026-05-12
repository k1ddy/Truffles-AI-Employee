"""Typed corpus schema for shadow-run replay.

Spec: SPECS/SHADOW_RUN_V3.md (Phase B.3).

JSONL format: one `CorpusDialog` per line.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict, Field

from app.policy_core_v3 import EvidenceItem, Turn
from app.policy_core_v3.schema import PolicyDecisionV3
from app.policy_core_v3_shadow import LegacySummary


class CorpusTurn(BaseModel):
    """One turn inside a dialog. Self-contained for replay."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int = Field(..., ge=0)
    current_message: str
    history: list[Turn] = Field(default_factory=list)
    state_slots: dict[str, Any] = Field(default_factory=dict)
    evidence_bundle: list[EvidenceItem] = Field(default_factory=list)
    legacy_summary: LegacySummary
    # Owner-pending oracle: what v3 SHOULD emit. Used by the oracle LLM stub.
    oracle_v3: PolicyDecisionV3 | None = None
    notes: str = ""


class CorpusDialog(BaseModel):
    """One messy dialog. Owner approval status tracked in `status`."""

    model_config = ConfigDict(extra="forbid")

    dialog_id: str
    locale: str = "ru-KZ"
    status: str = "draft"  # "draft" | "owner_approved" | "deprecated"
    notes: str = ""
    turns: list[CorpusTurn]


def load_corpus_jsonl(path: pathlib.Path | str) -> list[CorpusDialog]:
    """Read one CorpusDialog per JSONL line. Strict — raises on malformed lines."""
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    out: list[CorpusDialog] = []
    with p.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {lineno}: invalid JSON: {exc}") from exc
            try:
                dialog = CorpusDialog.model_validate(payload)
            except Exception as exc:
                raise ValueError(f"line {lineno}: schema error: {exc}") from exc
            out.append(dialog)
    return out


def iter_corpus_turns(dialogs: list[CorpusDialog]) -> Iterator[tuple[CorpusDialog, CorpusTurn]]:
    for d in dialogs:
        for t in d.turns:
            yield d, t
