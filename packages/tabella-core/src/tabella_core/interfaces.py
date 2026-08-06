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

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
