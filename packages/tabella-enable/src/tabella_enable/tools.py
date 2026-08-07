"""AI tool manifest generator (spec/ai-artifact-manifest.md, part 1)."""

from __future__ import annotations

import re
from typing import Any

from tabella_core.models import TABELLA_SPEC_VERSION, AssetDescriptor, Classification, FieldType

_JSON_TYPES = {
    FieldType.string: "string",
    FieldType.integer: "integer",
    FieldType.number: "number",
    FieldType.boolean: "boolean",
    FieldType.date: "string",
    FieldType.datetime: "string",
    FieldType.json: "string",
}


def _tool_name(asset_id: str) -> str:
    return "query_" + re.sub(r"[^a-zA-Z0-9_-]", "_", asset_id)


def build_tool(descriptor: AssetDescriptor, *, include_pii_filters: bool = False) -> dict[str, Any]:
    filterable = [
        f
        for f in descriptor.asset_schema.fields
        if f.type in _JSON_TYPES and (include_pii_filters or not f.pii)
    ]
    properties: dict[str, Any] = {
        f.name: {
            "type": _JSON_TYPES[f.type],
            **({"description": f.description} if f.description else {}),
        }
        for f in filterable
    }
    properties["limit"] = {"type": "integer", "default": 100}
    properties["offset"] = {"type": "integer", "default": 0}

    about = f" ({descriptor.description})" if descriptor.description else ""
    return {
        "name": _tool_name(descriptor.id),
        "description": (
            f"Query the '{descriptor.name}' asset{about}. "
            f"Equality filters on: {', '.join(f.name for f in filterable) or 'none'}. "
            "Returns records as JSON objects."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        },
        "asset": descriptor.id,
        "endpoint": {"method": "GET", "path": f"/assets/{descriptor.id}/records"},
    }


def build_manifest(
    catalog: list[AssetDescriptor],
    *,
    include_restricted: bool = False,
    include_pii_filters: bool = False,
) -> dict[str, Any]:
    included = [
        d
        for d in catalog
        if d.enablement.mcp
        and (include_restricted or d.classification != Classification.restricted)
    ]
    tools = [build_tool(d, include_pii_filters=include_pii_filters) for d in included]
    tools += [build_search_tool(d) for d in included if d.enablement.vectorization.enabled]
    return {"tabella_version": TABELLA_SPEC_VERSION, "tools": tools}


def build_search_tool(descriptor: AssetDescriptor) -> dict[str, Any]:
    about = f" ({descriptor.description})" if descriptor.description else ""
    return {
        "name": "search_" + re.sub(r"[^a-zA-Z0-9_-]", "_", descriptor.id),
        "description": (
            f"Semantic search over the '{descriptor.name}' asset{about}. "
            "Pass a natural-language query; returns the most relevant text "
            "chunks with citation metadata and similarity scores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query"},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "asset": descriptor.id,
        "endpoint": {"method": "POST", "path": f"/assets/{descriptor.id}/search"},
    }
