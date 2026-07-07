"""Unit tests for document chunking."""

from rag.ingest import chunk_text


def test_chunking_splits_text():
    text = " ".join(str(i) for i in range(1000))
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(isinstance(c, str) for c in chunks)


def test_empty_text_returns_empty():
    assert chunk_text("") == []
