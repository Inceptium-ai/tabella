"""OpenMetadata catalog backend: provision + enrich, in two modes.

    direct  — Tabella creates the technical entities itself (no Glue needed):
              classification/tags -> domain -> service -> database -> schema
              (= source.name) -> table, then enriches.
    ingest  — the entity is produced by an OM ingestion pipeline (typically
              from Glue, which the governance backend registered first). If
              settings.pipeline_fqn is set, Tabella triggers it; either way it
              polls for the table FQN until the entity appears, then enriches.

Enrichment is identical in both modes: JSON Patch of tags, domain, PII column
labels, description, and custom properties onto the entity, then the data
contract (created against the table id).

Built against the vendored OM 1.12.x schemas (see ../../reference/README.md);
not yet validated against a live server — that happens with deploy/sandbox.
"""

from __future__ import annotations

import time
from urllib.parse import quote

from tabella_core.interfaces import CatalogBackend
from tabella_core.models import AssetDescriptor

from tabella_catalog_om import mapping
from tabella_catalog_om.client import OpenMetadataClient
from tabella_catalog_om.settings import OMSettings


class IngestTimeout(RuntimeError):
    pass


class OpenMetadataCatalog(CatalogBackend):
    name = "openmetadata"

    def __init__(
        self,
        client: OpenMetadataClient | None = None,
        settings: OMSettings | None = None,
        *,
        sleep=time.sleep,
    ):
        self.client = client or OpenMetadataClient()
        self.settings = settings or OMSettings()
        self._sleep = sleep

    def upsert_asset(self, descriptor: AssetDescriptor) -> None:
        if self.settings.mode == "direct":
            table = self._provision_direct(descriptor)
        else:
            table = self._provision_ingest(descriptor)
        self._enrich(descriptor, table)

    # ---------- provisioning ----------

    def _provision_direct(self, descriptor: AssetDescriptor) -> dict:
        settings = self.settings
        self.client.put(
            "/v1/services/databaseServices", mapping.service_payload(descriptor, settings)
        )
        self.client.put(
            "/v1/databases",
            {"name": settings.database, "service": mapping.fqn(settings.service)},
        )
        self.client.put(
            "/v1/databaseSchemas",
            {
                "name": descriptor.source.name,
                "database": mapping.fqn(settings.service, settings.database),
            },
        )
        return self.client.put("/v1/tables", mapping.table_payload(descriptor, settings))

    def _provision_ingest(self, descriptor: AssetDescriptor) -> dict:
        if self.settings.pipeline_fqn:
            pipeline = self.client.get(
                f"/v1/services/ingestionPipelines/name/{quote(self.settings.pipeline_fqn)}"
            )
            self.client.post(f"/v1/services/ingestionPipelines/trigger/{pipeline['id']}")
        return self._poll_for_table(descriptor)

    def _poll_for_table(self, descriptor: AssetDescriptor) -> dict:
        fqn = mapping.table_fqn(descriptor, self.settings)
        deadline = time.monotonic() + self.settings.poll_timeout
        while True:
            table = self.client.get_optional(f"/v1/tables/name/{quote(fqn)}")
            if table is not None:
                return table
            if time.monotonic() >= deadline:
                raise IngestTimeout(
                    f"Table '{fqn}' did not appear in OpenMetadata within "
                    f"{self.settings.poll_timeout:.0f}s — check the ingestion pipeline"
                )
            self._sleep(self.settings.poll_interval)

    # ---------- enrichment (shared) ----------

    def _enrich(self, descriptor: AssetDescriptor, table: dict) -> None:
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
        domain = self.client.put("/v1/domains", mapping.domain_payload(descriptor))
        domain_ref = {"id": domain["id"], "type": "domain"}

        ops = mapping.enrichment_ops(descriptor, table, domain_ref)
        self.client.patch(f"/v1/tables/{table['id']}", ops)

        if descriptor.contract.fields:
            self.client.put(
                "/v1/dataContracts",
                mapping.contract_payload(descriptor.contract, table["id"], descriptor),
            )
