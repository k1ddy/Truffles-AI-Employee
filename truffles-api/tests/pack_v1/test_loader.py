"""Loader tests for PackV1: real example pack and error paths."""
from __future__ import annotations

import pathlib

import pytest

from app.pack_v1 import PackLoadError, load_pack


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE_PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


def test_loads_example_pack() -> None:
    pack = load_pack(EXAMPLE_PACK)
    assert pack.pack_id == "beauty_salon_v1"
    assert pack.locale == "ru-KZ"
    assert pack.rules.bot_can_confirm is False
    assert "phone" in pack.rules.required_for_booking
    service_ids = {s.id for s in pack.services}
    assert {"brows_lashes", "manicure", "haircut"} <= service_ids
    tool_ids = {t.id for t in pack.tools}
    assert "calendar.book_slot" in tool_ids
    assert "handoff.create" in tool_ids


def test_loads_from_yaml_path_directly() -> None:
    pack = load_pack(EXAMPLE_PACK / "pack.yaml")
    assert pack.pack_id == "beauty_salon_v1"


def test_missing_file(tmp_path) -> None:
    with pytest.raises(PackLoadError) as exc:
        load_pack(tmp_path)
    assert "not found" in str(exc.value)


def test_yaml_parse_error(tmp_path) -> None:
    (tmp_path / "pack.yaml").write_text(":\n: : :", encoding="utf-8")
    with pytest.raises(PackLoadError) as exc:
        load_pack(tmp_path)
    assert "yaml parse error" in str(exc.value)


def test_top_level_must_be_mapping(tmp_path) -> None:
    (tmp_path / "pack.yaml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(PackLoadError):
        load_pack(tmp_path)


def test_schema_validation_error(tmp_path) -> None:
    (tmp_path / "pack.yaml").write_text("pack_id: x\n", encoding="utf-8")
    with pytest.raises(PackLoadError) as exc:
        load_pack(tmp_path)
    assert "schema validation failed" in str(exc.value)


def test_missing_knowledge_source(tmp_path) -> None:
    (tmp_path / "pack.yaml").write_text(
        """
pack_id: x_v1
pack_version: 1
vertical: x
locale: ru-KZ
business:
  name: X
  summary: x
rules:
  bot_can_confirm: false
  required_for_booking: [service]
  identity_for_lookup: [name_or_phone]
  escalate_topics: []
capabilities: [FACT]
services:
  - id: s1
    name: S1
tools:
  - id: t1
    description: d
    args_schema: {x: text}
knowledge_sources:
  - missing.md
""",
        encoding="utf-8",
    )
    with pytest.raises(PackLoadError) as exc:
        load_pack(tmp_path)
    assert "knowledge_sources" in str(exc.value)


def test_loader_is_pure(monkeypatch) -> None:
    """Load twice; result must be equal and side-effect-free."""
    a = load_pack(EXAMPLE_PACK)
    b = load_pack(EXAMPLE_PACK)
    assert a.model_dump() == b.model_dump()
