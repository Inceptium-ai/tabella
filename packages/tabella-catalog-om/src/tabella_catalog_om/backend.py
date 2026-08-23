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

    # ---------- vocabulary registration (governance registry -> OM) ----------
    # OM only accepts pre-registered metadata: a tag must exist in a
    # classification before a tagLabel can reference it, and a custom property
    # must be registered on the entity type before an /extension patch may
    # carry it (an unknown property 400s the whole all-or-nothing patch).

    def ensure_tags(
        self, tags: list[str], *, classification: str = mapping.TABELLA_CLASSIFICATION
    ) -> None:
        """Create/refresh a classification and its tags (createOrUpdate)."""
        self.client.put(
            "/v1/classifications",
            {"name": classification, "description": "Tags managed by Tabella"},
        )
        for tag in tags:
            self.client.put(
                "/v1/tags",
                {
                    "classification": classification,
                    "name": tag,
                    "description": f"Tabella tag '{tag}'",
                },
            )

    def register_custom_properties(self, entity_type: str, properties: list[dict]) -> None:
        """Register custom properties on an OM entity type (table,
        databaseSchema, domain, ...).

        Each property: {"name": str, "kind": "text"|"select",
                        "options": [...] (select only), "description": str?}.
        Registration is additive on OM's side — existing properties are
        updated, never removed here.
        """
        entity = self.client.get(
            f"/v1/metadata/types/name/{quote(entity_type)}", params={"category": "entityType"}
        )
        type_ids: dict[str, str] = {}

        def field_type_id(om_type: str) -> str:
            if om_type not in type_ids:
                found = self.client.get(
                    f"/v1/metadata/types/name/{om_type}", params={"category": "field"}
                )
                type_ids[om_type] = found["id"]
            return type_ids[om_type]

        for prop in properties:
            select = prop.get("kind") == "select"
            payload: dict = {
                "name": prop["name"],
                "description": prop.get("description") or f"Tabella property '{prop['name']}'",
                "propertyType": {
                    "id": field_type_id("enum" if select else "string"),
                    "type": "type",
                },
            }
            if select:
                payload["customPropertyConfig"] = {
                    "config": {"values": list(prop.get("options") or []), "multiSelect": False}
                }
            self.client.put(f"/v1/metadata/types/{entity['id']}", payload)

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
