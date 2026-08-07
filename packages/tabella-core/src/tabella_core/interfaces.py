"""Pluggable backend interfaces: catalog, governance, embeddings.

Reference adapters: tabella-catalog-om (OpenMetadata, M1), tabella-governance-aws
(Glue + Lake Formation, M3), pgvector embeddings (tabella-enable, M2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tabella_core.models import AssetDescriptor


class CatalogBackend(ABC):
    """Mirrors descriptors into a metadata catalog (entity, tags, domain,
    custom properties, contract)."""

    name: str

    @abstractmethod
    def upsert_asset(self, descriptor: AssetDescriptor) -> None: ...


class GovernanceBackend(ABC):
    """Registers assets with a governance system and applies access policy
    (e.g. AWS Glue registration + Lake Formation grants)."""

    name: str

    @abstractmethod
    def apply(self, descriptor: AssetDescriptor) -> None: ...


class EmbeddingProvider(ABC):
    """Embeds text chunks for RAG vectorization."""

    name: str
    model: str
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(ABC):
    """Stores and searches embedded chunks per asset collection.

    Reference backends: local JSON files (dev/tests, no infra) and pgvector
    (production). Re-vectorizing an asset MUST replace its collection
    idempotently.
    """

    name: str

    @abstractmethod
    def replace_collection(
        self, collection: str, chunks: list[dict], dimensions: int
    ) -> None:
        """Chunks are dicts: {id, record_ref, content, metadata, embedding}."""

    @abstractmethod
    def search(
        self, collection: str, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """Returns chunk dicts (sans embedding) with an added `score`."""
