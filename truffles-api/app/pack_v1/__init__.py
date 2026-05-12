"""PackV1 — single declarative tenant pack contract.

Status: PoC, not wired into runtime.
Spec: SPECS/PACK_V1.md

Replaces the seven legacy `pack_runtime_*_adapter.py` modules with one
typed loader over `packs/<pack_id>/pack.yaml`.
"""

from .errors import PackLoadError
from .pack_view_adapter import to_pack_view
from .schema import (
    PackBusiness,
    PackBranch,
    PackContacts,
    PackRulesV1,
    PackService,
    PackSpecialist,
    PackToolContract,
    PackV1,
)
from .loader import load_pack

__all__ = [
    "PackBranch",
    "PackBusiness",
    "PackContacts",
    "PackLoadError",
    "PackRulesV1",
    "PackService",
    "PackSpecialist",
    "PackToolContract",
    "PackV1",
    "load_pack",
    "to_pack_view",
]
