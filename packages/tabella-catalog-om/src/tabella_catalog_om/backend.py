"""OpenMetadata catalog backend: mirrors Asset Descriptors into OM.

Order of operations per upsert (all idempotent createOrUpdate PUTs):

    classification + tags -> domain -> service -> database -> schema
    -> table (columns, tags, domain, custom properties)
    -> data contract (needs the table id from the previous response)

Built against the vendored OM 1.12.x schemas (see ../../reference/README.md);
not yet validated against a live server — that happens with deploy/sandbox.
"""

from __future__ import annotations

from tabella_core.interfaces import CatalogBackend
from tabella_core.models import AssetDescriptor

from tabella_catalog_om import mapping
from tabella_catalog_om.client import OpenMetadataClient


class OpenMetadataCatalog(CatalogBackend):
    name = "openmetadata"

    def __init__(self, client: OpenMetadataClient | None = None):
        self.client = client or OpenMetadataClient()

    def upsert_asset(self, descriptor: AssetDescriptor) -> None:
        self._ensure_tags(descriptor)
        self._ensure_domain(descriptor)
        schema_fqn = self._ensure_hierarchy(descriptor)
        table = self.client.put(
            "/v1/tables", mapping.table_payload(descriptor, schema_fqn)
        )
        if descriptor.contract.fields:
            self.client.put(
                "/v1/dataContracts",
                mapping.contract_payload(descriptor.contract, table["id"], descriptor),
            )

    def _ensure_tags(self, descriptor: AssetDescriptor) -> None:
        self.client.put(
            "/v1/classifications",
            {
                "name": mapping.TABELLA_CLASSIFICATION,
                "description": "Tags managed by Tabella registration",
            },
        )
        for tag in mapping.table_tags(descriptor):
            self.client.put(
                "/v1/tags",
                {
                    "classification": mapping.TABELLA_CLASSIFICATION,
                    "name": tag,
                    "description": f"Tabella tag '{tag}'",
                },
            )

    def _ensure_domain(self, descriptor: AssetDescriptor) -> None:
        self.client.put("/v1/domains", mapping.domain_payload(descriptor))

    def _ensure_hierarchy(self, descriptor: AssetDescriptor) -> str:
        """Ensure service -> database -> schema; returns the schema FQN."""
        service = mapping.service_name(descriptor)
        database = mapping.database_name(descriptor)
        self.client.put("/v1/services/databaseServices", mapping.service_payload(descriptor))
        self.client.put(
            "/v1/databases",
            {"name": database, "service": mapping.fqn(service)},
        )
        self.client.put(
            "/v1/databaseSchemas",
            {"name": "default", "database": mapping.fqn(service, database)},
        )
        return mapping.fqn(service, database, "default")
