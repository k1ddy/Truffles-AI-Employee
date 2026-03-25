from app.services.knowledge_registry_service import _split_into_chunks


def test_split_into_chunks_respects_max(monkeypatch):
    monkeypatch.setenv("QDRANT_CHUNK_CHARS", "200")
    text = "a" * 450
    chunks = _split_into_chunks(
        text,
        doc_name="doc",
        doc_id="id",
        client_slug="client",
        branch_id=None,
        knowledge_tag=None,
    )
    assert len(chunks) == 3
    assert all(len(chunk["content"]) <= 200 for chunk in chunks)
    assert chunks[0]["metadata"]["section_index"] == 0
    assert chunks[1]["metadata"].get("chunk_index") == 1
