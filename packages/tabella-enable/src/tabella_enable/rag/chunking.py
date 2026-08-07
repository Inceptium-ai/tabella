"""Chunking strategies for RAG vectorization.

- `document`: one chunk per record — right for short records (tickets, rows).
- `fixed`: character windows with 10% overlap.
- `semantic`: sentence-boundary packing up to chunk_size (v0.1 approximation
  of semantic chunking; embedding-based splitting is a later refinement).
"""

from __future__ import annotations

import re

from tabella_core.models import ChunkingStrategy

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, strategy: ChunkingStrategy, chunk_size: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if strategy == ChunkingStrategy.document or len(text) <= chunk_size:
        return [text]
    if strategy == ChunkingStrategy.semantic:
        return _pack_sentences(text, chunk_size)
    return _fixed_windows(text, chunk_size)


def _fixed_windows(text: str, chunk_size: int) -> list[str]:
    overlap = max(chunk_size // 10, 1)
    step = chunk_size - overlap
    return [text[start : start + chunk_size] for start in range(0, len(text), step)]


def _pack_sentences(text: str, chunk_size: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(text):
        if current and len(current) + len(sentence) + 1 > chunk_size:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks
