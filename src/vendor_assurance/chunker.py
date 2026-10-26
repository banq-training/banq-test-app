"""Split large reports into manageable, overlapping text chunks."""

import re
from collections.abc import Iterator


def chunk_document(text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> list[str]:
    """Return whitespace-tokenized chunks with a stable overlap.

    These tokens are whitespace-delimited words, not a model-specific token count.
    Overlap helps retain evidence across adjacent chunks; it cannot guarantee that
    every complete sentence fits inside a chunk.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be between zero and max_tokens - 1")

    token_matches = list(re.finditer(r"\S+", text))
    if not token_matches:
        return []

    step = max_tokens - overlap_tokens
    chunks = []
    for start in range(0, len(token_matches), step):
        end = min(start + max_tokens, len(token_matches))
        chunks.append(text[token_matches[start].start() : token_matches[end - 1].end()])
        # Stop once a chunk reaches the end, otherwise the overlap emits a trailing
        # fragment that the previous chunk already covers.
        if end == len(token_matches):
            break
    return chunks


def iter_chunks(text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> Iterator[str]:
    """Yield the same materialized chunks as chunk_document, without streaming I/O."""
    yield from chunk_document(text, max_tokens, overlap_tokens)
