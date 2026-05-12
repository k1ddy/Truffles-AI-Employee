"""Real-data assertions for `packs/beauty_salon_v1/`.

Spec: SPECS/PACK_V1.md section 8 (Phase B reference content).

Source: truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml.
"""
from __future__ import annotations

import pathlib

from app.pack_v1 import load_pack


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


def test_real_salon_business_summary_mentions_address_and_hours() -> None:
    pack = load_pack(PACK)
    summary = pack.business.summary
    assert "Mira" in summary
    assert "Алматы" in summary
    assert "9:00" in summary or "9:00–21:00" in summary


def test_real_salon_required_services_present() -> None:
    pack = load_pack(PACK)
    expected = {
        "manicure",
        "pedicure",
        "haircut",
        "coloring",
        "brows_lashes",
        "facial_care",
        "depilation",
    }
    actual = {s.id for s in pack.services}
    assert expected <= actual, f"missing required services: {expected - actual}"


def test_real_salon_specialists_link_to_real_services() -> None:
    pack = load_pack(PACK)
    service_ids = {s.id for s in pack.services}
    expected_links = {
        "aigerim": {"manicure", "pedicure"},
        "madina": {"haircut", "coloring"},
        "dinara": {"brows_lashes"},
        "asem": {"facial_care"},
    }
    by_id = {sp.id: set(sp.service_ids) for sp in pack.specialists}
    for sp_id, must_include in expected_links.items():
        assert sp_id in by_id, f"specialist {sp_id} missing"
        assert must_include <= by_id[sp_id], (
            f"specialist {sp_id} missing services: {must_include - by_id[sp_id]}"
        )


def test_real_salon_aliases_cover_common_user_phrases() -> None:
    pack = load_pack(PACK)
    by_id = {s.id: set(s.aliases) for s in pack.services}
    # сценарии из SALON_TRUTH.yaml
    assert "брови" in by_id["brows_lashes"]
    assert "ресницы" in by_id["brows_lashes"]
    assert "стрижка" in by_id["haircut"]
    assert "покраска" in by_id["coloring"]
    assert "маникюр" in by_id["manicure"]
    assert "педикюр" in by_id["pedicure"]


def test_real_salon_rules_match_legacy_policy() -> None:
    pack = load_pack(PACK)
    assert pack.rules.bot_can_confirm is False
    assert "service" in pack.rules.required_for_booking
    assert "phone" in pack.rules.required_for_booking
    assert "name" in pack.rules.required_for_booking
    for topic in ("medical", "refund", "complaint", "legal", "cancel", "reschedule"):
        assert topic in pack.rules.escalate_topics


def test_real_salon_tools_cover_minimum_capabilities() -> None:
    pack = load_pack(PACK)
    tool_ids = {t.id for t in pack.tools}
    assert {"calendar.book_slot", "calendar.get_booking", "handoff.create"} <= tool_ids
