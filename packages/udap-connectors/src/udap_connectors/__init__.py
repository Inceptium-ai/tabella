"""Built-in UDAP connectors. Importing this package registers them.

v1 cut: sqlite (reference). Postgres and S3/files land in M1.
"""

from udap_connectors import sqlite  # noqa: F401  (registers SQLiteConnector)

__all__ = ["sqlite"]
