from app.services.knowledge_validation import get_required_fields_for_domain
from app.services.onboarding_blueprints import get_onboarding_blueprint, list_onboarding_blueprints
from app.services.reference_pack_integrity import build_required_fields_checksum


def test_blueprints_required_fields_profile_matches_domain_contract():
    for blueprint in list_onboarding_blueprints():
        expected_fields = get_required_fields_for_domain(domain_slug=blueprint.domain_slug)
        assert list(blueprint.required_fields_profile.fields) == expected_fields
        assert blueprint.required_fields_profile.checksum == build_required_fields_checksum(expected_fields)


def test_blueprints_readiness_weights_cover_core_dimensions():
    required_dimension_ids = {
        "go_no_go_contract",
        "delivery_health",
        "traffic_capability_alignment",
    }
    for blueprint in list_onboarding_blueprints():
        weights = dict(blueprint.readiness_weights)
        assert set(weights) == required_dimension_ids
        assert all(value > 0 for value in weights.values())


def test_legal_blueprint_excludes_booking_required_fields():
    legal = get_onboarding_blueprint("legal")
    assert legal is not None
    fields = set(legal.required_fields_profile.fields)
    assert "client_pack.booking.collect_fields" not in fields
    assert "client_pack.booking.bot_can_confirm" not in fields


def test_beauty_blueprint_keeps_booking_required_fields():
    beauty = get_onboarding_blueprint("beauty")
    assert beauty is not None
    fields = set(beauty.required_fields_profile.fields)
    assert "client_pack.booking.collect_fields" in fields
    assert "client_pack.booking.bot_can_confirm" in fields


def test_generic_blueprint_is_first_class_without_beauty_specific_fields():
    generic = get_onboarding_blueprint("generic")
    assert generic is not None
    assert generic.payload.domain_slug == "generic"
    assert generic.payload.channels.whatsapp is False
    fields = set(generic.required_fields_profile.fields)
    assert "client_pack.booking.collect_fields" in fields
    assert "client_pack.booking.bot_can_confirm" in fields
    assert "client_pack.guest_policy" not in fields
    assert "client_pack.safety.medical_note" not in fields
    assert "client_pack.pricing.price_from_reason" not in fields
    assert "client_pack.quality.expectations_photo" not in fields
