from app.services.knowledge_validation import MINIMUM_DATA_CONTRACT_VERSION, get_required_fields_for_domain
from app.services.reference_pack_integrity import (
    REFERENCE_PACK_INTEGRITY_VERSION,
    REFERENCE_PACK_SCHEMA_VERSION,
    build_reference_pack_metadata,
    build_required_fields_checksum,
    evaluate_reference_pack_integrity,
)


def test_build_reference_pack_metadata_includes_integrity_bundle():
    metadata = build_reference_pack_metadata(
        domain_slug="beauty",
        metadata={"source": "manual"},
    )

    assert metadata["source"] == "manual"
    integrity = metadata["integrity"]
    assert integrity["version"] == REFERENCE_PACK_INTEGRITY_VERSION
    assert integrity["minimum_data_contract_version"] == MINIMUM_DATA_CONTRACT_VERSION
    assert integrity["required_fields"] == get_required_fields_for_domain(domain_slug="beauty")
    assert integrity["required_fields_checksum"] == build_required_fields_checksum(
        get_required_fields_for_domain(domain_slug="beauty")
    )


def test_evaluate_reference_pack_integrity_passes_for_generated_metadata():
    metadata = build_reference_pack_metadata(domain_slug="beauty")

    issues = evaluate_reference_pack_integrity(
        domain_slug="beauty",
        schema_version=REFERENCE_PACK_SCHEMA_VERSION,
        metadata=metadata,
    )

    assert issues == []


def test_evaluate_reference_pack_integrity_fails_for_legacy_schema_version():
    metadata = build_reference_pack_metadata(domain_slug="beauty")

    issues = evaluate_reference_pack_integrity(
        domain_slug="beauty",
        schema_version="v1",
        metadata=metadata,
    )

    assert "reference_pack_schema_version" in issues


def test_evaluate_reference_pack_integrity_fails_for_checksum_mismatch():
    metadata = build_reference_pack_metadata(domain_slug="beauty")
    metadata["integrity"]["required_fields_checksum"] = "broken"

    issues = evaluate_reference_pack_integrity(
        domain_slug="beauty",
        schema_version=REFERENCE_PACK_SCHEMA_VERSION,
        metadata=metadata,
    )

    assert "reference_pack_required_fields_checksum" in issues
