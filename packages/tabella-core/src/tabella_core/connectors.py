"""Connector SDK: base contract and scheme registry (spec/connector-interface.md)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar, NamedTuple

from tabella_core.models import AssetDescriptor, AssetSchema


class FetchResult(NamedTuple):
    records: list[dict[str, Any]]
    total: int | None


class Connector(ABC):
    scheme: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()

    def source_name(self, uri: str) -> str:
        """Default logical source name derived from the URI (last path segment,
        extension stripped). Discovery drafts use this; owners override it in
        the manifest."""
        from urllib.parse import urlparse

        from tabella_core.models import slug

        parsed = urlparse(uri)
        path = parsed.path.strip("/")
        last = path.rsplit("/", 1)[-1] if path else (parsed.netloc or self.scheme)
        stem = last.rsplit(".", 1)[0] if "." in last else last
        return slug(stem or self.scheme)

    @abstractmethod
    def list_assets(self, uri: str) -> list[str]: ...

    @abstractmethod
    def introspect(self, uri: str, native_name: str) -> AssetSchema: ...

    @abstractmethod
    def fetch(
        self,
        descriptor: AssetDescriptor,
        *,
        filters: Mapping[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FetchResult: ...


_REGISTRY: dict[str, type[Connector]] = {}


def register(cls: type[Connector]) -> type[Connector]:
    _REGISTRY[cls.scheme] = cls
    for alias in cls.aliases:
        _REGISTRY[alias] = cls
    return cls


def get_connector(scheme: str) -> Connector:
    try:
        return _REGISTRY[scheme]()
    except KeyError:
        raise KeyError(
            f"No connector registered for scheme '{scheme}' (available: {sorted(_REGISTRY)})"
        ) from None


def scheme_of(uri: str) -> str:
    scheme, sep, _ = uri.partition("://")
    if not sep:
        raise ValueError(f"Not a source URI (expected '<scheme>://...'): {uri!r}")
    return scheme
