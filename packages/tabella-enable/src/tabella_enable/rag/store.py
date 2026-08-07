"""Vector store backends.

- `local` — one JSON file per collection under a directory; pure-python cosine
  search. Zero infrastructure: dev, tests, small catalogs.
- `pgvector` — production backend (psycopg, lazy import). Built against the
  pgvector SQL surface; live validation happens in the AWS test batch along
  with OM/Glue.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from tabella_core.interfaces import VectorStore


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


class LocalVectorStore(VectorStore):
    name = "local"

    def __init__(self, directory: str | Path = ".tabella/vectors"):
        self.directory = Path(directory)

    def _path(self, collection: str) -> Path:
        return self.directory / f"{collection}.json"

    def replace_collection(
        self, collection: str, chunks: list[dict], dimensions: int
    ) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self._path(collection).write_text(
            json.dumps({"dimensions": dimensions, "chunks": chunks}) + "\n"
        )

    def search(
        self, collection: str, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        path = self._path(collection)
        if not path.exists():
            raise KeyError(f"No vector collection '{collection}' (run `tabella vectorize`)")
        chunks = json.loads(path.read_text())["chunks"]
        scored = sorted(
            chunks, key=lambda c: cosine(c["embedding"], query_embedding), reverse=True
        )[:top_k]
        return [
            {**{k: v for k, v in c.items() if k != "embedding"},
             "score": round(cosine(c["embedding"], query_embedding), 6)}
            for c in scored
        ]


class PgVectorStore(VectorStore):
    """pgvector backend. Collection = one table `tabella_vec_<slug>`.

    Requires the `vector` extension. Not yet validated against a live
    database — exercised in the AWS test batch.
    """

    name = "pgvector"

    def __init__(self, uri: str | None = None):
        self.uri = uri or os.environ.get("TABELLA_VECTOR_PG_URI", "")
        if not self.uri:
            raise ValueError("PgVectorStore requires TABELLA_VECTOR_PG_URI")

    def _connect(self):
        import psycopg  # lazy

        return psycopg.connect(self.uri)

    @staticmethod
    def _table(collection: str) -> str:
        safe = "".join(c if c.isalnum() else "_" for c in collection)
        return f"tabella_vec_{safe}"

    def replace_collection(
        self, collection: str, chunks: list[dict], dimensions: int
    ) -> None:
        table = self._table(collection)
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.execute(
                f'CREATE TABLE "{table}" (id text PRIMARY KEY, record_ref text,'
                f" content text, metadata jsonb, embedding vector({dimensions}))"
            )
            with conn.cursor() as cur:
                cur.executemany(
                    f'INSERT INTO "{table}" VALUES (%s, %s, %s, %s, %s)',  # noqa: S608
                    [
                        (
                            c["id"],
                            c["record_ref"],
                            c["content"],
                            json.dumps(c["metadata"]),
                            str(c["embedding"]),
                        )
                        for c in chunks
                    ],
                )

    def search(
        self, collection: str, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        table = self._table(collection)
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT id, record_ref, content, metadata,'  # noqa: S608
                f" 1 - (embedding <=> %s::vector) AS score"
                f' FROM "{table}" ORDER BY embedding <=> %s::vector LIMIT %s',
                (str(query_embedding), str(query_embedding), top_k),
            ).fetchall()
        return [
            {
                "id": r[0],
                "record_ref": r[1],
                "content": r[2],
                "metadata": r[3],
                "score": round(float(r[4]), 6),
            }
            for r in rows
        ]


def vector_store_from_env() -> VectorStore:
    backend = os.environ.get("TABELLA_VECTOR_BACKEND", "local")
    if backend == "local":
        return LocalVectorStore(os.environ.get("TABELLA_VECTOR_DIR", ".tabella/vectors"))
    if backend == "pgvector":
        return PgVectorStore()
    raise ValueError(f"Unknown TABELLA_VECTOR_BACKEND: {backend!r} (local|pgvector)")
