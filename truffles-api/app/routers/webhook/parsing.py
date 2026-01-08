"""Normalize/validate webhook payloads (payload, instanceId, metadata)."""

from . import _legacy as _legacy

_EXPORTS = {
    name: value for name, value in _legacy.__dict__.items() if not name.startswith("__")
}
globals().update(_EXPORTS)
__all__ = sorted(_EXPORTS)
