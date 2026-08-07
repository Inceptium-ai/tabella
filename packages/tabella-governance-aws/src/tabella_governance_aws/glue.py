"""AWS Glue governance backend.

Registers assets in the Glue Data Catalog following the source standard:
Glue database = descriptor.source.name (the logical source), Glue table =
descriptor.name. This is the same hierarchy the OpenMetadata backend uses, so
an OM ingestion pipeline pointed at this Glue catalog produces entities whose
FQNs Tabella can construct deterministically for enrichment.

Idempotent: databases tolerate AlreadyExists; tables are get-then-update-or-
create. Credentials/region come from the standard AWS environment.

Lake Formation permission grants (mapping descriptor.access.read_roles to LF
principals) require an org-specific principal mapping and are deliberately not
implemented yet — tracked for the platform/M3 follow-up.
"""

from __future__ import annotations

from typing import Any

from tabella_core.interfaces import GovernanceBackend
from tabella_core.models import AssetDescriptor, FieldType

# canonical type -> Glue/Athena type
_GLUE_TYPES = {
    FieldType.string: "string",
    FieldType.integer: "bigint",
    FieldType.number: "double",
    FieldType.boolean: "boolean",
    FieldType.date: "date",
    FieldType.datetime: "timestamp",
    FieldType.json: "string",
    FieldType.binary: "binary",
    FieldType.unknown: "string",
}


def table_input(descriptor: AssetDescriptor) -> dict[str, Any]:
    return {
        "Name": descriptor.name,
        "Description": descriptor.description or "",
        "TableType": "EXTERNAL_TABLE",
        "StorageDescriptor": {
            "Columns": [
                {"Name": f.name, "Type": _GLUE_TYPES[f.type]}
                for f in descriptor.asset_schema.fields
            ],
            "Location": descriptor.source.uri,
        },
        "Parameters": {
            **descriptor.custom_properties,
            "tabella:id": descriptor.id,
            "tabella:domain": descriptor.domain,
            "tabella:classification": descriptor.classification.value,
            "tabella:owner": descriptor.owner or "",
        },
    }


class GlueGovernance(GovernanceBackend):
    name = "aws"

    def __init__(self, glue_client=None):
        if glue_client is None:
            import boto3  # lazy: keep boto3 import cost off non-AWS paths

            glue_client = boto3.client("glue")
        self.glue = glue_client

    def apply(self, descriptor: AssetDescriptor) -> None:
        database = descriptor.source.name
        try:
            self.glue.create_database(
                DatabaseInput={
                    "Name": database,
                    "Description": f"Tabella source '{database}'",
                }
            )
        except self.glue.exceptions.AlreadyExistsException:
            pass

        payload = table_input(descriptor)
        try:
            self.glue.get_table(DatabaseName=database, Name=descriptor.name)
        except self.glue.exceptions.EntityNotFoundException:
            self.glue.create_table(DatabaseName=database, TableInput=payload)
        else:
            self.glue.update_table(DatabaseName=database, TableInput=payload)
