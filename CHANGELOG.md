# Changelog

## 0.1.2 — 2026-08-23

- **Vocabulary registration API** on the OpenMetadata backend:
  `ensure_tags()` (classification + tags, createOrUpdate) and
  `register_custom_properties()` (custom properties on entity types, text →
  string / select → enum with config values) — OM requires both to be
  pre-registered before tagLabels or `extension` patches may reference them.

## 0.1.1 — 2026-08-23

- **Declared-schema registration**: connectors may declare
  `introspectable = False`; registration then derives the asset schema from
  the manifest's contract instead of introspecting the source — placeholder
  catalog entries that still carry shape, ownership, and PII markings.
- **api connector** (aliases `https`, `http`): registers API-backed assets as
  placeholders — endpoint URI + native path recorded for cataloging; data
  access stays with the source system.

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
