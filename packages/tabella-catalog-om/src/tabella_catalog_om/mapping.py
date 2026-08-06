"""Descriptor -> OpenMetadata payload mapping.

Shapes follow the vendored request schemas (reference/schemas). The OM entity
hierarchy is service -> database -> schema -> table; FQN segments containing
dots are quoted per OM rules.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from tabella_core.models import AssetDescriptor, Contract, FieldDef, FieldType

TABELLA_CLASSIFICATION = "Tabella"
PII_TAG = "PII.Sensitive"

# canonical type -> OM column dataType (entity/data/table.json#dataType)
_OM_TYPES = {
    FieldType.string: "STRING",
    FieldType.integer: "INT",
    FieldType.number: "DOUBLE",
    FieldType.boolean: "BOOLEAN",
    FieldType.date: "DATE",
    FieldType.datetime: "DATETIME",
    FieldType.json: "JSON",
    FieldType.binary: "BINARY",
    FieldType.unknown: "UNKNOWN",
}

# connector scheme -> OM databaseService serviceType; anything unmapped is a
# metadata-only CustomDatabase service.
_SERVICE_TYPES = {
    "postgres": "Postgres",
    "mysql": "Mysql",
    "sqlite": "SQLite",
}


def quote_fqn_part(part: str) -> str:
    return f'"{part}"' if "." in part else part


def fqn(*parts: str) -> str:
    return ".".join(quote_fqn_part(p) for p in parts)


def service_name(descriptor: AssetDescriptor) -> str:
    return f"tabella-{descriptor.source.connector}"


def database_name(descriptor: AssetDescriptor) -> str:
    """Deterministic database segment derived from the source URI path."""
    path = urlparse(descriptor.source.uri).path.strip("/")
    last = path.rsplit("/", 1)[-1]
    stem = last.rsplit(".", 1)[0] if "." in last else last
    return stem or "default"


def _tag_label(tag_fqn: str) -> dict[str, str]:
    return {"tagFQN": tag_fqn}


def table_tags(descriptor: AssetDescriptor) -> list[str]:
    """Tabella-classification tag names applied to the table (sans FQN prefix)."""
    return [*descriptor.tags, descriptor.classification.value]


def column_payload(field: FieldDef, primary_key: list[str]) -> dict[str, Any]:
    col: dict[str, Any] = {"name": field.name, "dataType": _OM_TYPES[field.type]}
    if field.description:
        col["description"] = field.description
    if field.name in primary_key:
        col["constraint"] = "PRIMARY_KEY"
    elif not field.nullable:
        col["constraint"] = "NOT_NULL"
    if field.pii:
        col["tags"] = [_tag_label(PII_TAG)]
    return col


def table_payload(descriptor: AssetDescriptor, schema_fqn: str) -> dict[str, Any]:
    pk = descriptor.asset_schema.primary_key
    return {
        "name": descriptor.source.native_name,
        "displayName": descriptor.name,
        "description": descriptor.description,
        "databaseSchema": schema_fqn,
        "columns": [column_payload(f, pk) for f in descriptor.asset_schema.fields],
        "tags": [
            _tag_label(f"{TABELLA_CLASSIFICATION}.{t}") for t in table_tags(descriptor)
        ],
        "domains": [descriptor.domain],
        **(
            {"extension": dict(descriptor.custom_properties)}
            if descriptor.custom_properties
            else {}
        ),
    }


def service_payload(descriptor: AssetDescriptor) -> dict[str, Any]:
    return {
        "name": service_name(descriptor),
        "serviceType": _SERVICE_TYPES.get(descriptor.source.connector, "CustomDatabase"),
        "description": f"Tabella-managed {descriptor.source.connector} source",
    }


def domain_payload(descriptor: AssetDescriptor) -> dict[str, Any]:
    return {
        "name": descriptor.domain,
        "domainType": "Aggregate",
        "description": f"Tabella domain '{descriptor.domain}'",
    }


def contract_payload(
    contract: Contract, table_id: str, descriptor: AssetDescriptor
) -> dict[str, Any]:
    columns = []
    for spec in contract.fields:
        col: dict[str, Any] = {
            "name": spec.name,
            "dataType": _OM_TYPES[spec.type] if spec.type else "UNKNOWN",
        }
        if spec.required:
            col["constraint"] = "NOT_NULL"
        if spec.pii:
            col["tags"] = [_tag_label(PII_TAG)]
        columns.append(col)
    return {
        "name": f"{descriptor.id}-contract",
        "description": f"Tabella contract for {descriptor.id}, verified at registration",
        "entity": {"id": table_id, "type": "table"},
        "schema": columns,
    }
