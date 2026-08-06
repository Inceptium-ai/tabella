# tabella-connectors

Built-in Tabella connectors (see `../../spec/connector-interface.md`):

| Scheme | Source | Notes |
|---|---|---|
| `sqlite` | SQLite files | Reference implementation; zero-setup demos/tests |
| `postgres` / `postgresql` | PostgreSQL | psycopg 3; credentials via libpq env (PGUSER/PGPASSWORD), never URIs; native names are `schema.table` |
| `file` / `s3` | CSV + Parquet on local disk or S3 | pyarrow filesystems; native names are paths relative to the base URI; v0.1 filters in memory |

Live-postgres tests are gated behind `TABELLA_TEST_PG_URI`.
