"""Built-in Tabella connectors. Importing this package registers them.

- sqlite — reference implementation, zero-setup demos/tests
- postgres (alias: postgresql) — psycopg 3
- file (alias: s3) — CSV/Parquet on local disk or S3, via pyarrow
"""

from tabella_connectors import files, postgres, sqlite  # noqa: F401  (register on import)

__all__ = ["files", "postgres", "sqlite"]
