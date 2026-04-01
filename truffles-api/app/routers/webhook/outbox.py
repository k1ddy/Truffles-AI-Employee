"""Compatibility shim for durable outbox execution helpers."""

from __future__ import annotations

from app.services.outbox_runtime_service import (
    ChatFlowAdapter,
    ProviderGatewayAdapter,
    _classify_transport_degradation,
    _coerce_outbox_created_at,
    _ensure_rag_meta_defaults,
    _find_message_by_conversation_created_at,
    _find_message_by_message_id,
    _get_outbox_window_merge_seconds,
    _handle_enqueue_only_accept,
    _prepare_skip_persist,
    _process_outbox_rows,
    _split_outbox_batches,
)

__all__ = [
    "ChatFlowAdapter",
    "ProviderGatewayAdapter",
    "_classify_transport_degradation",
    "_coerce_outbox_created_at",
    "_ensure_rag_meta_defaults",
    "_find_message_by_conversation_created_at",
    "_find_message_by_message_id",
    "_get_outbox_window_merge_seconds",
    "_handle_enqueue_only_accept",
    "_prepare_skip_persist",
    "_process_outbox_rows",
    "_split_outbox_batches",
]
