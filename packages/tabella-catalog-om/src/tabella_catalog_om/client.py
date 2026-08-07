"""Thin OpenMetadata REST client.

Endpoints and payload shapes follow the vendored schemas in ../../reference/
(OM 1.12.x line). Auth is a JWT bearer token (an OM bot token).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

DEFAULT_HOST = "http://localhost:8585"


class OpenMetadataError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: str):
        super().__init__(f"OpenMetadata {method} {path} failed ({status}): {body[:400]}")
        self.status = status


class OpenMetadataClient:
    """createOrUpdate-style access to the OM REST API."""

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        host = (host or os.environ.get("TABELLA_OM_HOST", DEFAULT_HOST)).rstrip("/")
        token = token or os.environ.get("TABELLA_OM_TOKEN", "")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(
            base_url=f"{host}/api", headers=headers, timeout=30.0, transport=transport
        )

    def put(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._http.put(path, json=payload)
        if resp.status_code >= 400:
            raise OpenMetadataError("PUT", path, resp.status_code, resp.text)
        return resp.json()

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self._http.post(path, json=payload or {})
        if resp.status_code >= 400:
            raise OpenMetadataError("POST", path, resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self._http.get(path, params=params)
        if resp.status_code >= 400:
            raise OpenMetadataError("GET", path, resp.status_code, resp.text)
        return resp.json()

    def get_optional(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """GET that returns None on 404 (used for FQN polling)."""
        resp = self._http.get(path, params=params)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise OpenMetadataError("GET", path, resp.status_code, resp.text)
        return resp.json()

    def patch(self, path: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
        """JSON Patch (RFC 6902) — OM's enrichment surface."""
        resp = self._http.patch(
            path,
            content=json.dumps(operations),
            headers={"Content-Type": "application/json-patch+json"},
        )
        if resp.status_code >= 400:
            raise OpenMetadataError("PATCH", path, resp.status_code, resp.text)
        return resp.json()

    def close(self) -> None:
        self._http.close()
