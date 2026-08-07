"""Semantic search service: embed the query, search the asset's collection."""

from __future__ import annotations

from typing import Any

from tabella_core.interfaces import EmbeddingProvider, VectorStore
from tabella_core.models import AssetDescriptor

from tabella_enable.rag.pipeline import collection_name


class SearchService:
    def __init__(self, embedder: EmbeddingProvider, store: VectorStore):
        self.embedder = embedder
        self.store = store

    def search(
        self, descriptor: AssetDescriptor, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        (query_embedding,) = self.embedder.embed([query])
        return self.store.search(collection_name(descriptor), query_embedding, top_k)
