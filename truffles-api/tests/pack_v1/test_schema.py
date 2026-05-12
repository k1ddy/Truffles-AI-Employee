"""Schema validation tests for PackV1."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.pack_v1 import (
    PackBusiness,
    PackRulesV1,
    PackService,
    PackSpecialist,
    PackToolContract,
    PackV1,
)


def _minimal_kwargs(**overrides):
    base = dict(
        pack_id="x_v1",
        pack_version=1,
        vertical="x",
        locale="ru-KZ",
        business=PackBusiness(name="X", summary="x"),
        rules=PackRulesV1(
            bot_can_confirm=False,
            required_for_booking=["service", "datetime", "name", "phone"],
            identity_for_lookup=["name_or_phone"],
            escalate_topics=["medical"],
        ),
        capabilities=["FACT", "BOOKING"],
        services=[PackService(id="s1", name="S1")],
        tools=[
            PackToolContract(
                id="t1",
                description="d",
                args_schema={"x": "text"},
                requires_capability="BOOKING",
            )
        ],
    )
    base.update(overrides)
    return base


def test_minimal_pack_validates() -> None:
    PackV1(**_minimal_kwargs())


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        PackV1.model_validate(
            {**{k: getattr(v, "model_dump", lambda: v)() if hasattr(v, "model_dump") else v
                for k, v in _minimal_kwargs().items()},
             "pack_id": "x_v1", "extra_thing": "no"}
        )


def test_empty_services_rejected() -> None:
    with pytest.raises(ValidationError):
        PackV1(**_minimal_kwargs(services=[]))


def test_duplicate_service_ids_rejected() -> None:
    with pytest.raises(ValidationError):
        PackV1(
            **_minimal_kwargs(
                services=[PackService(id="s1", name="A"), PackService(id="s1", name="B")]
            )
        )


def test_specialist_unknown_service_rejected() -> None:
    with pytest.raises(ValidationError):
        PackV1(
            **_minimal_kwargs(
                specialists=[PackSpecialist(id="sp1", name="Sp", service_ids=["nope"])]
            )
        )


def test_tool_capability_must_be_in_pack_capabilities() -> None:
    with pytest.raises(ValidationError):
        PackV1(
            **_minimal_kwargs(
                capabilities=["FACT"],
                tools=[
                    PackToolContract(
                        id="t1",
                        description="d",
                        args_schema={"x": "text"},
                        requires_capability="BOOKING",
                    )
                ],
            )
        )


def test_capability_value_is_closed() -> None:
    with pytest.raises(ValidationError):
        PackV1(**_minimal_kwargs(capabilities=["FACT", "DANCE"]))
