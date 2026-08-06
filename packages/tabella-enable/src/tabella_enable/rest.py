"""Generated REST access layer (spec/access-layer-contract.md).

`build_app(catalog)` returns a FastAPI app serving every asset in the catalog
with `enablement.api: true` through the standard Tabella endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tabella_core.connectors import get_connector
from tabella_core.models import AssetDescriptor, FieldType

_RESERVED_PARAMS = {"limit", "offset"}
_UNFILTERABLE = {FieldType.binary, FieldType.unknown}


class _ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _coerce(value: str, ftype: FieldType) -> Any:
    try:
        if ftype == FieldType.integer:
            return int(value)
        if ftype == FieldType.number:
            return float(value)
        if ftype == FieldType.boolean:
            if value.lower() in ("true", "1"):
                return 1
            if value.lower() in ("false", "0"):
                return 0
            raise ValueError(value)
    except ValueError:
        raise _ApiError(400, "invalid_value", f"Invalid {ftype.value} value: {value!r}") from None
    return value


def build_app(catalog: list[AssetDescriptor]) -> FastAPI:
    served = [d for d in catalog if d.enablement.api]
    by_id = {d.id: d for d in served}
    app = FastAPI(title="Tabella Access Layer", version="0.1.0")

    @app.exception_handler(_ApiError)
    async def _handle(request: Request, exc: _ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    def _get(asset_id: str) -> AssetDescriptor:
        if asset_id not in by_id:
            raise _ApiError(404, "asset_not_found", f"No asset '{asset_id}'")
        return by_id[asset_id]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/assets")
    def list_assets() -> dict[str, Any]:
        return {"data": [d.summary() for d in served]}

    @app.get("/assets/{asset_id}")
    def get_asset(asset_id: str) -> dict[str, Any]:
        return _get(asset_id).to_json_dict()

    @app.get("/assets/{asset_id}/records")
    def query_records(
        asset_id: str, request: Request, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        descriptor = _get(asset_id)
        limit = max(1, min(limit, descriptor.access.row_limit))
        offset = max(0, offset)

        filters: dict[str, Any] = {}
        for name, value in request.query_params.items():
            if name in _RESERVED_PARAMS:
                continue
            field = descriptor.asset_schema.field(name)
            if field is None:
                raise _ApiError(400, "unknown_field", f"No field '{name}' in asset '{asset_id}'")
            if field.type in _UNFILTERABLE:
                raise _ApiError(400, "invalid_value", f"Field '{name}' is not filterable")
            filters[name] = _coerce(value, field.type)

        connector = get_connector(descriptor.source.connector)
        records, total = connector.fetch(descriptor, filters=filters, limit=limit, offset=offset)
        return {
            "data": records,
            "pagination": {"limit": limit, "offset": offset, "total": total},
            "asset": asset_id,
        }

    return app
