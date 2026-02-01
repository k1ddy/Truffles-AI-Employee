from pathlib import Path

import yaml

from app.services.knowledge_validation import build_payload_checksum
from app.services.pack_compiler_service import compile_pack_payload, inject_compiled_artifacts


def _load_demo_payload() -> dict:
    path = Path(__file__).resolve().parents[1] / "app/knowledge/demo_salon/SALON_TRUTH.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_pack_compiler_outputs_compiled_artifacts() -> None:
    payload = _load_demo_payload()
    compiled = compile_pack_payload(payload)

    assert compiled.get("schema_version") == "compiled_pack.v1"
    assert isinstance(compiled.get("hash"), str)
    assert isinstance(compiled.get("pack_index"), dict)
    assert compiled.get("signal_graph", {}).get("schema_version") == "signal_graph.v1"
    assert compiled.get("policy_bundle", {}).get("schema_version") == "policy_bundle.v1"

    effective = compiled.get("effective_pack")
    assert isinstance(effective, dict)
    assert isinstance(effective.get("client_pack"), dict)


def test_payload_checksum_ignores_compiled_artifacts() -> None:
    payload = _load_demo_payload()
    checksum = build_payload_checksum(payload)
    compiled = compile_pack_payload(payload)
    payload_with_compiled = inject_compiled_artifacts(payload, compiled)

    assert build_payload_checksum(payload_with_compiled) == checksum
