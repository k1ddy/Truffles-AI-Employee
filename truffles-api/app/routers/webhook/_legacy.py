"""Legacy webhook adapter: re-export decision orchestrator symbols."""

from __future__ import annotations

from . import decision as _decision

for _name, _value in _decision.__dict__.items():
    if _name.startswith("__"):
        continue
    globals()[_name] = _value

del _decision

__all__ = [name for name in globals() if not name.startswith("__")]
