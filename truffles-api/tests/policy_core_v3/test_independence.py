"""Static guard: policy_core_v3 must not import from legacy layers.

Spec acceptance criterion 3: independence guarantee.
"""
from __future__ import annotations

import pathlib


def test_no_legacy_imports() -> None:
    pkg = pathlib.Path(__file__).resolve().parents[2] / "app" / "policy_core_v3"
    assert pkg.is_dir(), pkg
    forbidden = ("app.services", "app.core", "app.adapters")
    offenders: list[tuple[str, str]] = []
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in forbidden:
            if f"from {token}" in text or f"import {token}" in text:
                offenders.append((py.name, token))
    assert not offenders, f"forbidden imports found: {offenders}"
