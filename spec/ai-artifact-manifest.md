# Tabella AI Artifact Manifests — v0.1.0

Tabella's enablement layer turns registered assets into artifacts AI systems can
consume directly. Two artifact types are specified in v0.1:

1. **Tool manifest** (`tools.json`) — datasets as agent tools (MCP-aligned)
2. **RAG index manifest** (`rag.json`) — the declared state of vectorized
   content per asset

Both are derived from Asset Descriptors and are regenerable build artifacts.

---

## 1. Tool manifest

Maps each enabled asset (`enablement.mcp: true`) to a tool definition with a
JSON-Schema input contract — the same shape used by the Model Context Protocol
(MCP) and Anthropic/OpenAI tool-use APIs — plus the access-layer endpoint that
executes it.

```bash
tabella tools catalog/ -o tools.json
```

```json
{
  "tabella_version": "0.1.0",
  "tools": [
    {
      "name": "query_sales_customers",
      "description": "Query the 'customers' asset (Customer master records). Equality filters on: id, country. Returns records as JSON objects.",
      "input_schema": {
        "type": "object",
        "properties": {
          "country": {"type": "string"},
          "limit": {"type": "integer", "default": 100},
          "offset": {"type": "integer", "default": 0}
        },
        "additionalProperties": false
      },
      "asset": "sales.customers",
      "endpoint": {"method": "GET", "path": "/assets/sales.customers/records"}
    }
  ]
}
```

### Rules

- `name` MUST be unique and match `[a-zA-Z0-9_-]{1,128}` (MCP-compatible).
  Convention: `query_<id with '.' → '_'>`.
- `description` MUST state what the asset is and which fields are filterable —
  this is agent-facing prompt text; write it for a model.
- `input_schema` MUST be valid JSON Schema derived from canonical field types.
- Fields marked `pii` are excluded from filterable properties by default;
  generators MUST require an explicit flag to include them.
- `binary`/`unknown` fields are never filters.
- Assets with `classification: restricted` are excluded by default; explicit
  opt-in required.
- Assets with `vectorization.enabled` additionally get a `search_<id>` tool
  (natural-language query → semantic search endpoint).

---

## 2. RAG index manifest

Declares, per vectorized asset, how its content was (or should be) chunked,
embedded, and indexed — so any serving layer can answer semantic queries with
citation back to the source asset.

```json
{
  "tabella_version": "0.1.0",
  "indexes": [
    {
      "asset": "support.tickets",
      "content_fields": ["subject", "body"],
      "chunking": {"strategy": "semantic", "chunk_size": 512},
      "embedding": {"model": "text-embedding-3-small", "dimensions": 1536},
      "store": {"backend": "pgvector", "collection": "tabella_support_tickets"},
      "metadata_fields": ["id", "created_at"],
      "search_endpoint": {"method": "POST", "path": "/assets/support.tickets/search"}
    }
  ]
}
```

### Rules

- `content_fields` MUST be `string`-typed fields of the asset.
- `metadata_fields` are stored alongside vectors to enable filtered retrieval
  and citation back to source records.
- `store.backend` is an open, pluggable identifier (`pgvector` is the
  reference backend; `pinecone`, `weaviate`, `qdrant` are valid values).
- Re-running vectorization for an asset MUST replace its collection
  idempotently (registration is an update, and so is enablement).

The executable pipeline behind this manifest (`tabella vectorize`) ships in M2;
the manifest shape is specified now so catalog and platform layers can build
against it.
