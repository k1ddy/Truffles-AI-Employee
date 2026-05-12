"""Adapter that exposes a `PackV1` as a `policy_core_v3.PackView`.

Spec: SPECS/PACK_V1.md section 6.

Pure, side-effect-free. Returns a `StaticPackView` instance built from the
already-validated `PackV1`.
"""
from __future__ import annotations

from app.policy_core_v3.pack_view import (
    PackRules,
    ServiceView,
    SpecialistView,
    StaticPackView,
)

from .schema import PackV1


def to_pack_view(pack: PackV1) -> StaticPackView:
    services = [
        ServiceView(
            id=s.id,
            name=s.name,
            aliases=tuple(s.aliases),
            duration_min=s.duration_min,
            price=s.price_display,
        )
        for s in pack.services
    ]
    specialists = [
        SpecialistView(
            id=sp.id,
            name=sp.name,
            service_ids=tuple(sp.service_ids),
        )
        for sp in pack.specialists
    ]
    rules = PackRules(
        bot_can_confirm=pack.rules.bot_can_confirm,
        required_for_booking=tuple(pack.rules.required_for_booking),
        identity_for_lookup=tuple(pack.rules.identity_for_lookup),
        escalate_topics=tuple(pack.rules.escalate_topics),
    )
    return StaticPackView(
        pack_id=pack.pack_id,
        services=services,
        specialists=specialists,
        rules=rules,
        business_summary=pack.business.summary,
    )
