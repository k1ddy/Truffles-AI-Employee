"""Demo salon adapter module resolved by slug-based runtime discovery."""

from __future__ import annotations

from app.services import pack_runtime_demo_adapter as _demo_adapter

for _name in _demo_adapter.__all__:
    globals()[_name] = getattr(_demo_adapter, _name)

__all__ = list(_demo_adapter.__all__)

del _demo_adapter
