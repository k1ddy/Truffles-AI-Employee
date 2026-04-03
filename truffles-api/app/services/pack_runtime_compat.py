"""Compatibility-only raw semantic pack helpers.

This module isolates legacy pack semantic APIs away from the canonical
`pack_runtime_service` boundary. Live runtime code must not import this surface.
"""

from __future__ import annotations

from app.services.pack_runtime_default import _resolve_adapter
from app.services.pack_runtime_service import (
    _build_pack_query_truth_decision as get_pack_decision,
)
from app.services.pack_runtime_service import (
    _resolve_pack_query_price_item as get_pack_price_item,
)
from app.services.pack_runtime_service import (
    _build_pack_query_price_reply as get_pack_price_reply,
)
from app.services.pack_runtime_service import (
    _build_pack_query_service_decision as get_pack_service_decision,
)
from app.services.pack_runtime_service import (
    _resolve_pack_query_service_hint as get_pack_service_hint,
)
from app.services.pack_runtime_service import (
    _resolve_pack_query_semantic_match as semantic_service_match,
)
from app.services.pack_runtime_service import (
    _resolve_pack_query_master_intent as resolve_master_intent,
)


def semantic_question_type(
    text: str,
    *,
    include_kinds: set[str] | None = None,
    return_multi: bool = False,
    client_slug: str | None = "generic",
):
    return _resolve_adapter(client_slug)._pack_query_question_classifier(
        text,
        include_kinds=include_kinds,
        return_multi=return_multi,
        client_slug=client_slug,
    )


def phrase_match_intent(text: str, client_slug: str | None = "generic") -> set[str]:
    return _resolve_adapter(client_slug)._pack_query_phrase_intents(
        text,
        client_slug=client_slug,
    )


__all__ = [
    "get_pack_decision",
    "get_pack_price_item",
    "get_pack_price_reply",
    "get_pack_service_decision",
    "get_pack_service_hint",
    "phrase_match_intent",
    "resolve_master_intent",
    "semantic_question_type",
    "semantic_service_match",
]
