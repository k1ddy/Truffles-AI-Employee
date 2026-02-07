from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PackDecision:
    action: str
    response: str
    intent: str | None = None
    collect: list[str] | None = None
    meta: dict[str, Any] | None = None


# Backward compatibility alias for existing imports.
DemoSalonDecision = PackDecision


__all__ = ["PackDecision", "DemoSalonDecision"]
