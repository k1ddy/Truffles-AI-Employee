from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "ops" / "diagnose.py",
        base.parents[2] / "ops" / "diagnose.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip(
            "ops/diagnose.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("diagnose_script", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_parse_branch_domain_pairs_accepts_key_equals_domain():
    mapping = _module._parse_branch_domain_pairs(
        [
            "main=beauty",
            "b7f75692-951e-421a-aae6-f5db97394799=beauty",
            " BRANCH_A = clinic ",
        ]
    )
    assert mapping["main"] == "beauty"
    assert mapping["b7f75692-951e-421a-aae6-f5db97394799"] == "beauty"
    assert mapping["branch_a"] == "clinic"


def test_parse_branch_domain_pairs_rejects_invalid_token():
    with pytest.raises(SystemExit):
        _module._parse_branch_domain_pairs(["beauty-only"])


def test_onboarding_quality_smoke_domains_pass_for_contract_v2():
    imports = _module._onboarding_quality_imports()
    for domain_slug in ("beauty", "clinic", "legal", "ecom"):
        row = _module._onboarding_quality_evaluate_domain(domain_slug, imports=imports)
        assert row["status"] == "pass"
        assert row["missing_required_fields"] == []
        assert row["intake_missing_fields"] == []
        assert row["integrity_missing"] == []


def test_onboarding_quality_compare_baseline_detects_regression():
    current = {
        "domains": [
            {
                "domain_slug": "beauty",
                "status": "fail",
                "required_fields_checksum": "new",
                "missing_required_fields": ["x"],
            }
        ]
    }
    baseline = {
        "domains": [
            {
                "domain_slug": "beauty",
                "status": "pass",
                "required_fields_checksum": "old",
                "missing_required_fields": [],
            }
        ]
    }
    regressions = _module._onboarding_quality_compare_baseline(current, baseline)
    assert "beauty:status" in regressions
    assert "beauty:required_fields_checksum" in regressions
    assert "beauty:missing_required_fields" in regressions


def _complete_beauty_payload() -> dict:
    return {
        "client_pack": {
            "business": {"name": "Demo Salon"},
            "location": {"city": "Almaty", "address": {"full": "Abay 10"}},
            "operations": {"hours": {"days": ["mon", "tue"], "open": "09:00", "close": "21:00"}},
            "catalog": {"summary": "Nails and lashes"},
            "communication": {"languages": ["ru", "kk"]},
            "services_catalog": {
                "services": [{"name": "Маникюр", "price": 12000, "duration_minutes": 60}]
            },
            "service_duration_estimates": [{"service": "Маникюр", "duration_minutes": 60}],
            "booking": {
                "collect_fields": ["service", "time", "name", "phone"],
                "bot_can_confirm": True,
            },
            "guest_policy": {"allowed": "yes"},
            "safety": {"medical_note": "consult specialist"},
            "pricing": {"price_from_reason": "depends on scope"},
            "quality": {"expectations_photo": "reference required"},
            "price_list": [{"category": "Nails", "items": [{"name": "Маникюр", "price": 12000}]}],
            "policy": {
                "hard_law": {"intent": "hard_law", "keywords": ["law"]},
                "payment_info": {"intent": "payment", "keywords": ["pay"]},
                "reschedule": {"intent": "reschedule", "keywords": ["move"]},
                "cancel": {"intent": "cancel", "keywords": ["cancel"]},
                "medical": {"intent": "medical", "keywords": ["medical"]},
                "legal": {"intent": "legal", "keywords": ["legal"]},
                "complaint": {"intent": "complaint", "keywords": ["complaint"]},
                "discounts": {"intent": "discounts", "keywords": ["discount"]},
                "guard_topics": {"refund": ["refund", "возврат"]},
            },
        },
        "domain_pack": {
            "ood_anchors": {
                "in_domain": ["маникюр"],
                "out_of_domain": ["кредит"],
                "strict_in": ["салон"],
            }
        },
    }


def test_onboarding_pack_quality_resolve_require_booking_modes():
    assert _module._onboarding_pack_quality_resolve_require_booking("auto") is None
    assert _module._onboarding_pack_quality_resolve_require_booking("true") is True
    assert _module._onboarding_pack_quality_resolve_require_booking("false") is False


def test_onboarding_pack_quality_matrix_to_dict_includes_dimensions_and_regressions():
    matrix = SimpleNamespace(
        status="fail",
        infra_valid=True,
        semantic_valid=False,
        required_fields_count=10,
        missing_fields_count=2,
        critical_missing_fields_count=1,
        integrity_missing_count=1,
        missing_fields=["a", "b"],
        critical_missing_fields=["a"],
        integrity_missing=["reference_pack_domain"],
        dimensions=[SimpleNamespace(id="pack_compile", status="fail", required=True, details=["error"])],
        regressions=["status"],
        comparison_blocked=False,
        comparison_block_reason=None,
    )

    result = _module._onboarding_pack_quality_matrix_to_dict(matrix)

    assert result["status"] == "fail"
    assert result["missing_fields_count"] == 2
    assert result["dimensions"][0]["id"] == "pack_compile"
    assert result["regressions"] == ["status"]


def test_onboarding_pack_quality_helpers_produce_pass_for_complete_payload():
    imports = _module._onboarding_quality_imports()
    payload = imports["build_intake_payload"](
        client_data_json=_complete_beauty_payload(),
        client_data_text=None,
    )
    summary = imports["build_intake_pack_quality_summary"](
        payload,
        domain_slug="beauty",
        require_booking=True,
    )

    compile_data = _module._onboarding_pack_quality_compile_to_dict(summary.compile)
    quality_data = _module._onboarding_pack_quality_matrix_to_dict(summary.quality_matrix)

    assert compile_data["status"] == "pass"
    assert quality_data["status"] == "pass"
    assert quality_data["missing_fields_count"] == 0
