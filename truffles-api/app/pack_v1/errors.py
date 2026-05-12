"""PackV1 loader errors."""
from __future__ import annotations


class PackLoadError(Exception):
    """Raised when a pack file cannot be parsed or violates the schema."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.path:
            return f"{self.args[0]} (path={self.path})"
        return str(self.args[0])
