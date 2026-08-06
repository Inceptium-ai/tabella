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
