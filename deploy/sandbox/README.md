# Local sandbox

Bootstrap with the CLI — it writes and starts the full local stack
(OpenMetadata + MySQL + OpenSearch, Postgres with pgvector, MinIO):

```bash
tabella init            # writes ./tabella-sandbox/ and runs docker compose up -d
tabella init --no-start # just write the files
```

Endpoints, credentials, and the env vars to wire Tabella against it are
printed on start (OpenMetadata takes a few minutes on first boot). Image tags
are pinned in the generated `.env` and get final verification during the
consolidated AWS/live validation window.
