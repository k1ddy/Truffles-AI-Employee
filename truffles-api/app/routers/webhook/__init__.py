"""Re-export webhook symbols for import compatibility."""

from . import _legacy as _legacy
from .http import router as router

_EXPORTS = {
    name: value for name, value in _legacy.__dict__.items() if not name.startswith("__")
}
_EXPORTS["router"] = router

globals().update(_EXPORTS)
__all__ = sorted(_EXPORTS)
