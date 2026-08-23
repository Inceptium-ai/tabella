"""API-endpoint connector: placeholder registration for assets that live
behind an API rather than a crawlable store.

An API source can't be introspected, so registration derives the schema from
the manifest's declared contract (`introspectable = False` — see
tabella_core.pipeline). The catalog entry records what the asset is, its
shape as declared, ownership, and where it actually lives (the endpoint URI +
native path); serving the data stays with the source system.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from tabella_core.connectors import Connector, FetchResult, register
from tabella_core.models import AssetDescriptor, AssetSchema, slug


@register
class ApiConnector(Connector):
    scheme = "api"
    aliases = ("https", "http")
    introspectable = False

    def source_name(self, uri: str) -> str:
        host = urlparse(uri).netloc.split(":")[0]
        return slug(host or "api")

    def list_assets(self, uri: str) -> list[str]:
        # Endpoints are declared in manifests, not enumerated from the source.
        return []

    def introspect(self, uri: str, native_name: str) -> AssetSchema:
        # Defensive: registration never calls this (introspectable = False).
        return AssetSchema(fields=[])

    def fetch(
        self,
        descriptor: AssetDescriptor,
        *,
        filters: Mapping[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FetchResult:
        raise NotImplementedError(
            "API assets are cataloged as placeholders; access the data through "
            f"the source endpoint ({descriptor.source.uri})."
        )
