"""RAG vectorization and semantic search (spec/ai-artifact-manifest.md, part 2)."""

from tabella_enable.rag.embeddings import embedding_provider_from_env
from tabella_enable.rag.pipeline import vectorize_asset
from tabella_enable.rag.search import SearchService
from tabella_enable.rag.store import vector_store_from_env

__all__ = [
    "SearchService",
    "embedding_provider_from_env",
    "vector_store_from_env",
    "vectorize_asset",
]
