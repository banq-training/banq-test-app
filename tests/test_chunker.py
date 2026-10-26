import pytest

from src.vendor_assurance.chunker import chunk_document


def test_chunks_respect_boundary_and_overlap() -> None:
    tokens = [f"word-{number}" for number in range(25)]
    chunks = chunk_document(" ".join(tokens), max_tokens=10, overlap_tokens=3)

    assert all(len(chunk.split()) <= 10 for chunk in chunks)
    assert chunks[0].split()[-3:] == chunks[1].split()[:3]
    assert chunks[1].split()[-3:] == chunks[2].split()[:3]
    assert chunks[-1].split()[-1] == "word-24"


def test_invalid_overlap_is_rejected() -> None:
    with pytest.raises(ValueError):
        chunk_document("some text", max_tokens=10, overlap_tokens=10)


def test_no_redundant_trailing_chunk() -> None:
    chunks = chunk_document(" ".join(str(number) for number in range(10)), max_tokens=5, overlap_tokens=2)

    assert chunks == ["0 1 2 3 4", "3 4 5 6 7", "6 7 8 9"]


def test_short_document_is_one_chunk() -> None:
    assert chunk_document("only a few words", max_tokens=50, overlap_tokens=10) == ["only a few words"]


def test_empty_document_has_no_chunks() -> None:
    assert chunk_document("   \n  ", max_tokens=10, overlap_tokens=2) == []
