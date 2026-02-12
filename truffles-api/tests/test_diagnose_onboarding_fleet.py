from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

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
