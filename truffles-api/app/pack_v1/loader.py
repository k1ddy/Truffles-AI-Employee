"""Pure PackV1 loader.

Spec: SPECS/PACK_V1.md section 5.

No DB, no network, no LLM. File path → validated `PackV1` or `PackLoadError`.
"""
from __future__ import annotations

import pathlib

import yaml
from pydantic import ValidationError

from .errors import PackLoadError
from .schema import PackV1


def load_pack(path: pathlib.Path | str) -> PackV1:
    """Load and validate a pack manifest from `<pack_dir>/pack.yaml`.

    Accepts either the directory or the manifest path itself for ergonomics.
    """
    p = pathlib.Path(path)
    if p.is_dir():
        manifest = p / "pack.yaml"
    else:
        manifest = p

    if not manifest.exists():
        raise PackLoadError("pack.yaml not found", path=str(manifest))
    if not manifest.is_file():
        raise PackLoadError("pack.yaml is not a regular file", path=str(manifest))

    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        raise PackLoadError(f"cannot read pack manifest: {exc}", path=str(manifest)) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PackLoadError(f"yaml parse error: {exc}", path=str(manifest)) from exc

    if not isinstance(data, dict):
        raise PackLoadError(
            f"pack.yaml top-level must be a mapping, got {type(data).__name__}",
            path=str(manifest),
        )

    try:
        pack = PackV1.model_validate(data)
    except ValidationError as exc:
        raise PackLoadError(f"schema validation failed: {exc}", path=str(manifest)) from exc

    # Verify referenced knowledge sources exist on disk (if any).
    pack_dir = manifest.parent
    for source in pack.knowledge_sources:
        candidate = pack_dir / source
        if not candidate.exists():
            raise PackLoadError(
                f"knowledge_sources entry not found: {source}",
                path=str(manifest),
            )

    return pack
