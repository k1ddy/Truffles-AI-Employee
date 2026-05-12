"""Static independence guard for policy_core_v3_corpus."""
from __future__ import annotations

import pathlib


def test_corpus_has_no_legacy_imports() -> None:
    pkg = pathlib.Path(__file__).resolve().parents[2] / "app" / "policy_core_v3_corpus"
    assert pkg.is_dir(), pkg
    forbidden = ("app.services", "app.core", "app.adapters")
    offenders: list[tuple[str, str]] = []
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in forbidden:
            if f"from {token}" in text or f"import {token}" in text:
                offenders.append((py.name, token))
    assert not offenders, f"forbidden imports found: {offenders}"
