from fastapi import Request

from app.services.console_router_utils import (
    dedupe_list,
    parse_bool_param,
    parse_env_bool,
    parse_env_csv_set,
    parse_env_int,
    parse_uuid_param,
    reject_unknown_query_params,
    request_with_query_params,
    validate_limit,
)


def test_request_with_query_params_ignores_none_values() -> None:
    async def receive() -> dict[str, str]:
        return {"type": "http.request"}

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/console/v1/test",
            "headers": [],
            "query_string": b"old=1",
            "scheme": "http",
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "root_path": "",
            "http_version": "1.1",
        },
        receive=receive,
    )

    updated = request_with_query_params(request, {"a": 1, "b": None, "c": "ok"})

    assert updated.query_params.get("a") == "1"
    assert updated.query_params.get("c") == "ok"
    assert "b" not in updated.query_params


def test_parse_env_bool_accepts_common_values(monkeypatch) -> None:
    monkeypatch.setenv("TEST_BOOL", "yes")
    assert parse_env_bool("TEST_BOOL", default=False) is True

    monkeypatch.setenv("TEST_BOOL", "off")
    assert parse_env_bool("TEST_BOOL", default=True) is False

    monkeypatch.setenv("TEST_BOOL", "invalid")
    assert parse_env_bool("TEST_BOOL", default=True) is True


def test_parse_env_csv_set_trims_and_filters(monkeypatch) -> None:
    monkeypatch.setenv("TEST_CSV", "alpha, beta, ,gamma")
    assert parse_env_csv_set("TEST_CSV", default={"default"}) == {"alpha", "beta", "gamma"}

    monkeypatch.delenv("TEST_CSV", raising=False)
    assert parse_env_csv_set("TEST_CSV", default={"default"}) == {"default"}


def test_parse_env_int_clamps_to_bounds(monkeypatch) -> None:
    monkeypatch.setenv("TEST_INT", "999")
    assert parse_env_int("TEST_INT", default=10, min_value=1, max_value=50) == 50

    monkeypatch.setenv("TEST_INT", "-7")
    assert parse_env_int("TEST_INT", default=10, min_value=1, max_value=50) == 1

    monkeypatch.setenv("TEST_INT", "invalid")
    assert parse_env_int("TEST_INT", default=10, min_value=1, max_value=50) == 10


def test_dedupe_list_preserves_order() -> None:
    assert dedupe_list(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_reject_unknown_query_params_raises_for_unexpected_key() -> None:
    async def receive() -> dict[str, str]:
        return {"type": "http.request"}

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/console/v1/test",
            "headers": [],
            "query_string": b"known=1&extra=2",
            "scheme": "http",
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "root_path": "",
            "http_version": "1.1",
        },
        receive=receive,
    )

    try:
        reject_unknown_query_params(request, {"known"}, error_factory=ValueError)
    except ValueError as exc:
        assert str(exc) == "Unknown query parameter(s): extra"
    else:
        raise AssertionError("Expected ValueError")


def test_validate_limit_uses_configurable_bounds() -> None:
    validate_limit(5, min_value=1, max_value=10, error_factory=ValueError)

    try:
        validate_limit(0, min_value=1, max_value=10, error_factory=ValueError)
    except ValueError as exc:
        assert str(exc) == "limit must be between 1 and 10"
    else:
        raise AssertionError("Expected ValueError")


def test_parse_uuid_param_handles_none_and_invalid() -> None:
    assert parse_uuid_param("branch_id", None, error_factory=ValueError) is None
    value = parse_uuid_param("branch_id", "123e4567-e89b-12d3-a456-426614174000", error_factory=ValueError)
    assert str(value) == "123e4567-e89b-12d3-a456-426614174000"

    for raw in ("", "not-a-uuid"):
        try:
            parse_uuid_param("branch_id", raw, error_factory=ValueError)
        except ValueError as exc:
            assert str(exc) == "Invalid branch_id"
        else:
            raise AssertionError("Expected ValueError")


def test_parse_bool_param_parses_true_false_and_default() -> None:
    assert parse_bool_param("include_ready", None, default=True, error_factory=ValueError) is True
    assert parse_bool_param("include_ready", "true", error_factory=ValueError) is True
    assert parse_bool_param("include_ready", "false", error_factory=ValueError) is False

    try:
        parse_bool_param("include_ready", "yes", error_factory=ValueError)
    except ValueError as exc:
        assert str(exc) == "Invalid include_ready"
    else:
        raise AssertionError("Expected ValueError")
