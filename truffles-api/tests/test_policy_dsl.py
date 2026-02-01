import pytest

from app.services.pack_compiler_service import PackCompilerError, compile_pack_payload


def test_policy_dsl_rejects_missing_sections() -> None:
    payload = {
        "client_pack": {
            "policy": {
                "payment_info": {"keywords": ["pay"]},
            }
        }
    }

    with pytest.raises(PackCompilerError) as exc:
        compile_pack_payload(payload)

    assert exc.value.errors
