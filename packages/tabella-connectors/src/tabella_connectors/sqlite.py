"""SQLite connector — the reference connector implementation.

URI form: `sqlite:///relative/or/absolute/path.db`
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tabella_core.connectors import Connector, FetchResult, register
from tabella_core.models import (
    AssetDescriptor,
    AssetSchema,
    FieldDef,
    FieldType,
    ForeignKey,
    slug,
)

_TYPE_MAP: list[tuple[re.Pattern[str], FieldType]] = [
    (re.compile(r"INT", re.I), FieldType.integer),
    (re.compile(r"CHAR|CLOB|TEXT", re.I), FieldType.string),
    (re.compile(r"BLOB", re.I), FieldType.binary),
    (re.compile(r"REAL|FLOA|DOUB|NUMERIC|DECIMAL", re.I), FieldType.number),
    (re.compile(r"BOOL", re.I), FieldType.boolean),
    (re.compile(r"DATETIME|TIMESTAMP", re.I), FieldType.datetime),
    (re.compile(r"DATE", re.I), FieldType.date),
    (re.compile(r"JSON", re.I), FieldType.json),
]


def _canonical_type(declared: str) -> FieldType:
    for pattern, ftype in _TYPE_MAP:
        if pattern.search(declared or ""):
            return ftype
    return FieldType.unknown


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@register
class SQLiteConnector(Connector):
    scheme = "sqlite"

    def _path(self, uri: str) -> Path:
        if not uri.startswith("sqlite:///"):
            raise ValueError(f"Invalid sqlite URI (expected sqlite:///path): {uri!r}")
        return Path(uri[len("sqlite:///") :])

    def _connect(self, uri: str) -> sqlite3.Connection:
        path = self._path(uri)
        if not path.exists():
            raise FileNotFoundError(f"SQLite database not found: {path}")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_assets(self, uri: str) -> list[str]:
        with self._connect(uri) as conn:
            return [
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master"
                    " WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]

    def introspect(self, uri: str, native_name: str) -> AssetSchema:
        source_slug = slug(self._path(uri).stem)
        with self._connect(uri) as conn:
            if native_name not in self.list_assets(uri):
                raise KeyError(f"No table '{native_name}' in {uri}")
            fields, pk = [], []
            for col in conn.execute(f"PRAGMA table_info({_quote(native_name)})"):
                fields.append(
                    FieldDef(
                        name=col["name"],
                        type=_canonical_type(col["type"]),
                        nullable=not col["notnull"] and not col["pk"],
                    )
                )
                if col["pk"]:
                    pk.append(col["name"])
            fks: dict[int, ForeignKey] = {}
            for fk in conn.execute(f"PRAGMA foreign_key_list({_quote(native_name)})"):
                entry = fks.setdefault(
                    fk["id"],
                    ForeignKey(
                        fields=[],
                        ref_asset=f"{source_slug}.{slug(fk['table'])}",
                        ref_fields=[],
                    ),
                )
                entry.fields.append(fk["from"])
                entry.ref_fields.append(fk["to"])
            return AssetSchema(fields=fields, primary_key=pk, foreign_keys=list(fks.values()))

    def fetch(
        self,
        descriptor: AssetDescriptor,
        *,
        filters: Mapping[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FetchResult:
        filters = dict(filters or {})
        for field in filters:
            if descriptor.asset_schema.field(field) is None:
                raise KeyError(field)
        table = _quote(descriptor.source.native_name)
        where, params = "", list(filters.values())
        if filters:
            where = " WHERE " + " AND ".join(f"{_quote(name)} = ?" for name in filters)
        with self._connect(descriptor.source.uri) as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM {table}{where} LIMIT ? OFFSET ?", [*params, limit, offset]
            ).fetchall()
        return FetchResult(records=[dict(r) for r in rows], total=total)
