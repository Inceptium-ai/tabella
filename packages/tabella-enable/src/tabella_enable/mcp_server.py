"""Live MCP server over a Tabella catalog (stdio transport).

Tools are generated from the catalog exactly per the tool-manifest spec:
`query_<asset>` (equality filters + pagination) for every MCP-enabled asset,
plus `search_<asset>` (semantic search) for vectorized assets when a search
service is configured.

The tool listing and dispatch are pure functions (`catalog_tools`,
`call_catalog_tool`) so they are testable without an MCP client; the stdio
wiring in `run_stdio` is a thin shell over the official `mcp` SDK.
"""

from __future__ import annotations

import json
from typing import Any

from tabella_core.connectors import get_connector
from tabella_core.models import AssetDescriptor

from tabella_enable.tools import build_manifest

_RESERVED = {"limit", "offset"}


def catalog_tools(
    catalog: list[AssetDescriptor], *, with_search: bool
) -> list[dict[str, Any]]:
    manifest = build_manifest(catalog)
    tools = manifest["tools"]
    if not with_search:
        tools = [t for t in tools if not t["name"].startswith("search_")]
    return tools


def call_catalog_tool(
    catalog: list[AssetDescriptor],
    name: str,
    arguments: dict[str, Any],
    *,
    search=None,
) -> dict[str, Any]:
    by_tool = {t["name"]: t for t in catalog_tools(catalog, with_search=search is not None)}
    if name not in by_tool:
        raise KeyError(f"Unknown tool: {name}")
    asset_id = by_tool[name]["asset"]
    descriptor = next(d for d in catalog if d.id == asset_id)

    if name.startswith("search_"):
        results = search.search(
            descriptor, arguments["query"], int(arguments.get("top_k", 5))
        )
        return {"data": results, "asset": asset_id}

    limit = min(int(arguments.get("limit", 100)), descriptor.access.row_limit)
    offset = int(arguments.get("offset", 0))
    filters = {k: v for k, v in arguments.items() if k not in _RESERVED}
    connector = get_connector(descriptor.source.connector)
    records, total = connector.fetch(descriptor, filters=filters, limit=limit, offset=offset)
    return {
        "data": records,
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "asset": asset_id,
    }


async def run_stdio(catalog: list[AssetDescriptor], *, search=None) -> None:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    server = Server("tabella")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["input_schema"],
            )
            for t in catalog_tools(catalog, with_search=search is not None)
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        try:
            result = call_catalog_tool(catalog, name, arguments or {}, search=search)
        except Exception as exc:
            result = {"error": str(exc)}
        return [types.TextContent(type="text", text=json.dumps(result, default=str))]

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
