from app.services import pack_query_backend_service as backend_service


def test_backend_service_runtime_local_mode_is_fail_closed(monkeypatch) -> None:
    backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "runtime_local")
    lookup = backend_service.resolve_backend_candidates(
        query_text="чистка зубов",
        client_slug="dental_pack",
    )
    assert lookup.available is False
    assert lookup.unavailable_reason == "runtime_local_mode"
    assert lookup.candidates == []


def test_backend_service_returns_driver_error_reason(monkeypatch) -> None:
    backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "backend_primary")
    monkeypatch.setenv("PACK_QUERY_BACKEND_DRIVER", "broken")

    def _broken_driver(**_kwargs):
        raise RuntimeError("boom")

    backend_service.register_backend_driver("broken", _broken_driver)
    try:
        lookup = backend_service.resolve_backend_candidates(
            query_text="чистка зубов",
            client_slug="dental_pack",
        )
    finally:
        backend_service.clear_backend_driver_registry()

    assert lookup.available is False
    assert lookup.unavailable_reason == "driver_error:RuntimeError"


def test_backend_service_normalizes_driver_payload() -> None:
    backend_service.clear_backend_driver_registry()
    backend_service.register_backend_driver(
        "ok",
        lambda **_kwargs: {
            "meta": {
                "engine": "pack_query_backend.custom",
                "engine_version": "1.0.0",
                "method": "rrf",
            },
            "candidates": [
                {
                    "canonical_name": "Профессиональная чистка зубов",
                    "score": 0.89,
                    "dense_score": 0.91,
                    "sparse_score": 0.77,
                    "rerank_bonus": 0.05,
                    "matched_alias": "чистка зубов",
                }
            ],
        },
    )
    try:
        lookup = backend_service.resolve_backend_candidates(
            query_text="чистка зубов",
            client_slug="dental_pack",
            explicit_mode="backend_primary",
            explicit_driver="ok",
        )
    finally:
        backend_service.clear_backend_driver_registry()

    assert lookup.available is True
    assert len(lookup.candidates) == 1
    row = lookup.candidates[0]
    assert row.canonical_name == "Профессиональная чистка зубов"
    assert row.score == 0.89
    assert row.dense_score == 0.91
    assert row.sparse_score == 0.77
    assert row.rerank_bonus == 0.05
    assert row.matched_alias == "чистка зубов"
    assert lookup.meta.get("engine") == "pack_query_backend.custom"
