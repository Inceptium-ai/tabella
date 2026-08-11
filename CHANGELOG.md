# Changelog

## 0.1.0 — 2026-08-11

Initial release of the Tabella open framework.

- **Standards v0.1**: Onboarding Manifest, Asset Descriptor, Connector
  Interface, Access Layer Contract, AI Artifact Manifests (+ JSON Schemas).
- **Registration pipeline**: manifest-driven (YAML/JSON) with automated
  discovery drafting; contract verification with violation reports; PII
  propagation; logical-source-driven hierarchy
  (`{service}.{database}.{source}.{asset}`).
- **Connectors**: SQLite, PostgreSQL, files/S3 (CSV + Parquet).
- **Catalog backend**: OpenMetadata — `direct` entity creation or
  `ingest` (Glue → OM pipeline → poll → enrich) with a shared JSON Patch
  enrichment path and data-contract publication.
- **Governance backend**: AWS Glue registration (database = logical source).
- **AI enablement**: generated REST access layers, MCP-aligned tool
  manifests, live MCP server (stdio), RAG vectorization
  (document/fixed/semantic chunking; hash + OpenAI-compatible embeddings;
  local + pgvector stores), semantic search endpoints.
- **CLI**: `register`, `discover`, `validate`, `serve`, `tools`, `vectorize`,
  `mcp`.
