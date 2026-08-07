"""Descriptor -> OpenMetadata payload mapping.

Two payload families:

- **Provisioning** (direct mode only): technical entities — service, database,
  schema (= logical source name), table with columns/constraints. No business
  metadata here, so direct mode and ingestion-produced entities look alike.
- **Enrichment** (every mode): JSON Patch operations layering business
  metadata — tags, PII labels, domain, description, custom properties — onto
  an existing table entity, plus the data-contract payload.

Hierarchy standard: {service}.{database}.{source.name}.{asset name}.
FQN segments containing dots are quoted per OM rules.
"""

from __future__ import annotations

from typing import Any

from tabella_core.models import AssetDescriptor, Contract, FieldDef, FieldType

from tabella_catalog_om.settings import OMSettings

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
    "postgresql": "Postgres",
    "mysql": "Mysql",
    "sqlite": "SQLite",
}


def quote_fqn_part(part: str) -> str:
    return f'"{part}"' if "." in part else part


def fqn(*parts: str) -> str:
    return ".".join(quote_fqn_part(p) for p in parts)


def table_fqn(descriptor: AssetDescriptor, settings: OMSettings) -> str:
    return fqn(settings.service, settings.database, descriptor.source.name, descriptor.name)


def schema_fqn(descriptor: AssetDescriptor, settings: OMSettings) -> str:
    return fqn(settings.service, settings.database, descriptor.source.name)


def _tag_label(tag_fqn: str) -> dict[str, str]:
    return {
        "tagFQN": tag_fqn,
        "labelType": "Manual",
        "state": "Confirmed",
        "source": "Classification",
    }


def table_tags(descriptor: AssetDescriptor) -> list[str]:
    """Tabella-classification tag names applied to the table (sans FQN prefix)."""
    return [*descriptor.tags, descriptor.classification.value]


# ---------- provisioning (direct mode) ----------


def column_payload(field: FieldDef, primary_key: list[str]) -> dict[str, Any]:
    col: dict[str, Any] = {"name": field.name, "dataType": _OM_TYPES[field.type]}
    if field.description:
        col["description"] = field.description
    if field.name in primary_key:
        col["constraint"] = "PRIMARY_KEY"
    elif not field.nullable:
        col["constraint"] = "NOT_NULL"
    return col


def service_payload(descriptor: AssetDescriptor, settings: OMSettings) -> dict[str, Any]:
    return {
        "name": settings.service,
        "serviceType": _SERVICE_TYPES.get(descriptor.source.connector, "CustomDatabase"),
        "description": "Tabella-managed data sources",
    }


def table_payload(descriptor: AssetDescriptor, settings: OMSettings) -> dict[str, Any]:
    pk = descriptor.asset_schema.primary_key
    return {
        "name": descriptor.name,
        "displayName": descriptor.name,
        "databaseSchema": schema_fqn(descriptor, settings),
        "columns": [column_payload(f, pk) for f in descriptor.asset_schema.fields],
    }


def domain_payload(descriptor: AssetDescriptor) -> dict[str, Any]:
    return {
        "name": descriptor.domain,
        "domainType": "Aggregate",
        "description": f"Tabella domain '{descriptor.domain}'",
    }


# ---------- enrichment (every mode) ----------


def enrichment_ops(
    descriptor: AssetDescriptor, current: dict[str, Any], domain_ref: dict[str, Any]
) -> list[dict[str, Any]]:
    """JSON Patch ops layering business metadata onto the current table entity."""

    def set_op(field_name: str, value: Any) -> dict[str, Any]:
        op = "replace" if current.get(field_name) is not None else "add"
        return {"op": op, "path": f"/{field_name}", "value": value}

    ops = [
        set_op(
            "tags",
            [_tag_label(f"{TABELLA_CLASSIFICATION}.{t}") for t in table_tags(descriptor)],
        ),
        set_op("domains", [domain_ref]),
    ]
    if descriptor.description:
        ops.append(set_op("description", descriptor.description))
    if descriptor.custom_properties:
        ops.append(set_op("extension", dict(descriptor.custom_properties)))

    pii_fields = {f.name for f in descriptor.asset_schema.fields if f.pii}
    for index, column in enumerate(current.get("columns", [])):
        if column["name"] in pii_fields:
            op = "replace" if column.get("tags") else "add"
            ops.append(
                {"op": op, "path": f"/columns/{index}/tags", "value": [_tag_label(PII_TAG)]}
            )
    return ops


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
