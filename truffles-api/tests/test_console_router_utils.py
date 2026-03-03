from fastapi import Request

from app.services.console_router_utils import (
    dedupe_list,
    parse_env_bool,
    parse_env_csv_set,
    parse_env_int,
    request_with_query_params,
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
