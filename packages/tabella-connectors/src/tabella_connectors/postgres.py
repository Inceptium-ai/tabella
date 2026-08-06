"""PostgreSQL connector (psycopg 3).

URI form: `postgres://host[:port]/dbname` (or `postgresql://`). Credentials
come from libpq's usual environment (PGUSER/PGPASSWORD/pgpass), never the URI.
Asset native names are `schema.table`; a bare table name means `public`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from tabella_core.connectors import Connector, FetchResult, register
from tabella_core.models import (
    AssetDescriptor,
    AssetSchema,
    FieldDef,
    FieldType,
    ForeignKey,
    slug,
)

# information_schema.columns.data_type -> canonical
_TYPE_MAP: dict[str, FieldType] = {
    "smallint": FieldType.integer,
    "integer": FieldType.integer,
    "bigint": FieldType.integer,
    "numeric": FieldType.number,
    "real": FieldType.number,
    "double precision": FieldType.number,
    "money": FieldType.number,
    "character varying": FieldType.string,
    "character": FieldType.string,
    "text": FieldType.string,
    "uuid": FieldType.string,
    "boolean": FieldType.boolean,
    "date": FieldType.date,
    "timestamp without time zone": FieldType.datetime,
    "timestamp with time zone": FieldType.datetime,
    "time without time zone": FieldType.string,
    "json": FieldType.json,
    "jsonb": FieldType.json,
    "bytea": FieldType.binary,
}

_LIST_SQL = """
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
      AND table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name
"""

_COLUMNS_SQL = """
    SELECT column_name, data_type, is_nullable FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
"""

_PK_SQL = """
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = %s AND tc.table_name = %s
    ORDER BY kcu.ordinal_position
"""

_FK_SQL = """
    SELECT tc.constraint_name, kcu.column_name,
           ccu.table_schema AS ref_schema, ccu.table_name AS ref_table,
           ccu.column_name AS ref_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = %s AND tc.table_name = %s
    ORDER BY tc.constraint_name, kcu.ordinal_position
"""


def canonical_type(data_type: str) -> FieldType:
    return _TYPE_MAP.get(data_type.lower(), FieldType.unknown)


def split_native_name(native_name: str) -> tuple[str, str]:
    """`schema.table` -> (schema, table); bare table -> ('public', table)."""
    schema, sep, table = native_name.partition(".")
    return (schema, table) if sep else ("public", schema)


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@register
class PostgresConnector(Connector):
    scheme = "postgres"
    aliases = ("postgresql",)

    def _connect(self, uri: str):
        import psycopg  # lazy: keep import cost off non-postgres paths

        return psycopg.connect(uri)

    def _db_slug(self, uri: str) -> str:
        return slug(urlparse(uri).path.strip("/") or "postgres")

    def list_assets(self, uri: str) -> list[str]:
        with self._connect(uri) as conn:
            rows = conn.execute(_LIST_SQL).fetchall()
        return [f"{s}.{t}" for s, t in rows]

    def introspect(self, uri: str, native_name: str) -> AssetSchema:
        schema_name, table = split_native_name(native_name)
        db_slug = self._db_slug(uri)
        with self._connect(uri) as conn:
            cols = conn.execute(_COLUMNS_SQL, (schema_name, table)).fetchall()
            if not cols:
                raise KeyError(f"No table '{native_name}' in {uri}")
            pk = [r[0] for r in conn.execute(_PK_SQL, (schema_name, table)).fetchall()]
            fk_rows = conn.execute(_FK_SQL, (schema_name, table)).fetchall()

        fields = [
            FieldDef(
                name=name,
                type=canonical_type(data_type),
                nullable=is_nullable == "YES" and name not in pk,
            )
            for name, data_type, is_nullable in cols
        ]
        fks: dict[str, ForeignKey] = {}
        for constraint, column, ref_schema, ref_table, ref_column in fk_rows:
            entry = fks.setdefault(
                constraint,
                ForeignKey(
                    fields=[],
                    ref_asset=f"{db_slug}.{slug(f'{ref_schema}.{ref_table}')}",
                    ref_fields=[],
                ),
            )
            entry.fields.append(column)
            entry.ref_fields.append(ref_column)
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
        schema_name, table = split_native_name(descriptor.source.native_name)
        target = f"{quote_ident(schema_name)}.{quote_ident(table)}"
        where, params = "", list(filters.values())
        if filters:
            where = " WHERE " + " AND ".join(f"{quote_ident(name)} = %s" for name in filters)
        with self._connect(descriptor.source.uri) as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM {target}{where}", params).fetchone()[0]  # noqa: S608
            cur = conn.execute(
                f"SELECT * FROM {target}{where} LIMIT %s OFFSET %s",  # noqa: S608
                [*params, limit, offset],
            )
            names = [d.name for d in cur.description]
            records = [dict(zip(names, row, strict=True)) for row in cur.fetchall()]
        return FetchResult(records=records, total=total)
