from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.turn_planner import SemanticFrame


class ConversationProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "conversation_projection.v1"
    projection_version: str = "v1"
    conversation_id: str | None = None
    last_turn_id: str | None = None
    current_semantic_decision_ref: str | None = None
    active_capability: str | None = None
    semantic_slots: dict[str, str] = Field(default_factory=dict)
    missing_information: dict[str, Any] = Field(default_factory=dict)
    active_workflow_ref: str | None = None
    pending_handoff_state: dict[str, Any] = Field(default_factory=dict)
    last_reply_ref: str | None = None
    compatibility_view_refs: dict[str, str] = Field(default_factory=dict)
    semantic_frame: SemanticFrame = Field(default_factory=SemanticFrame)
    semantic_contract: dict[str, Any] = Field(default_factory=dict)
    pending_question_contract: dict[str, Any] = Field(default_factory=dict)
    current_goal: str | None = None
    booking_state: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def apply_journal_events(
        cls,
        existing: ConversationProjectionV1 | None,
        events: list[dict[str, Any]] | list[BaseModel],
    ) -> ConversationProjectionV1:
        projection = existing.model_copy(deep=True) if isinstance(existing, cls) else cls()
        for raw_event in events:
            payload = getattr(raw_event, "payload", None)
            if not isinstance(payload, dict):
                continue
            projection_state = payload.get("projection_state")
            if isinstance(projection_state, dict):
                projection = cls.model_validate(projection_state)
        return projection


__all__ = ["ConversationProjectionV1"]
