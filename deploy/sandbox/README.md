# Local sandbox (M1)

A docker-compose stack for local end-to-end development:

- **OpenMetadata** (+ its MySQL/Elasticsearch dependencies) — catalog backend
- **PostgreSQL** — a real source to register (with pgvector for M2 RAG)
- **MinIO** — S3-compatible object storage for the files connector

`tabella init` will bootstrap this stack and point the CLI at it. Lands in M1.
