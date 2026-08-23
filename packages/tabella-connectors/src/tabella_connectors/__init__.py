"""Built-in Tabella connectors. Importing this package registers them.

- sqlite — reference implementation, zero-setup demos/tests
- postgres (alias: postgresql) — psycopg 3
- file (alias: s3) — CSV/Parquet on local disk or S3, via pyarrow
- api (aliases: https, http) — placeholder registration for API-backed
  assets: declared-contract schema, no introspection, no serving
"""

from tabella_connectors import api, files, postgres, sqlite  # noqa: F401  (register on import)

__all__ = ["api", "files", "postgres", "sqlite"]
