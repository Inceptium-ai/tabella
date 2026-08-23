"""Request-shape tests for the OpenMetadata backend, against a mocked transport.

Covers both provisioning modes (direct, ingest) and the shared enrichment
phase. Payloads are pinned to the vendored OM 1.12.x schemas — live-server
validation happens when deploy/sandbox lands.
"""

import json

import httpx
import pytest
from tabella_catalog_om import (
    IngestTimeout,
    OMSettings,
    OpenMetadataCatalog,
    OpenMetadataClient,
    OpenMetadataError,
)
from tabella_catalog_om.mapping import table_fqn
from tabella_core.pipeline import register

TABLE_ID = "11111111-2222-3333-4444-555555555555"
DOMAIN_ID = "99999999-8888-7777-6666-555555555555"


def _settings(**overrides):
    defaults = dict(
        mode="direct", service="tabella", database="default",
        pipeline_fqn=None, poll_timeout=1.0, poll_interval=0.0,
    )
    return OMSettings(**{**defaults, **overrides})


def _descriptor(tmp_path, manifest):
    return register(manifest, tmp_path / "catalog").descriptor


class Recorder:
    """Mock OM server: records calls, answers PUT/PATCH with id-stamped bodies."""

    def __init__(self, table_lookup_misses: int = 0):
        self.calls: list[tuple[str, str, object]] = []
        self._misses = table_lookup_misses

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, request.url.path, body))
        path = request.url.path
        if request.method == "GET" and "/v1/tables/name/" in path:
            if self._misses > 0:
                self._misses -= 1
                return httpx.Response(404, text="not found")
            return httpx.Response(
                200,
                json={"id": TABLE_ID, "columns": [{"name": "id"}, {"name": "email"},
                                                  {"name": "full_name"}, {"name": "country"},
                                                  {"name": "created_at"}]},
            )
        if request.method == "GET" and "/v1/services/ingestionPipelines/name/" in path:
            return httpx.Response(200, json={"id": "pipe-1"})
        if request.method == "GET" and "/v1/metadata/types/name/" in path:
            type_name = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"id": f"type-{type_name}", "name": type_name})
        entity_id = DOMAIN_ID if path.endswith("/v1/domains") else TABLE_ID
        payload = body if isinstance(body, dict) else {}
        return httpx.Response(200, json={"id": entity_id, **payload})

    def paths(self):
        return [p for _, p, _ in self.calls]

    def by_path(self, path):
        return [b for _, p, b in self.calls if p == path]


def _run(descriptor, recorder, settings):
    client = OpenMetadataClient(
        host="http://om.test", token="t", transport=httpx.MockTransport(recorder)
    )
    OpenMetadataCatalog(client, settings, sleep=lambda s: None).upsert_asset(descriptor)


def test_direct_mode_provisions_then_enriches(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder()
    _run(descriptor, rec, _settings())
    paths = rec.paths()
    # provision: service -> database -> schema -> table
    assert paths[:4] == [
        "/api/v1/services/databaseServices",
        "/api/v1/databases",
        "/api/v1/databaseSchemas",
        "/api/v1/tables",
    ]
    # enrich: tags/domain ensured, then PATCH, then contract
    assert f"/api/v1/tables/{TABLE_ID}" in paths
    assert paths[-1] == "/api/v1/dataContracts"

    (schema,) = rec.by_path("/api/v1/databaseSchemas")
    assert schema == {"name": "retail", "database": "tabella.default"}
    (table,) = rec.by_path("/api/v1/tables")
    assert table["name"] == "customers"
    assert table["databaseSchema"] == "tabella.default.retail"
    assert "tags" not in table and "domains" not in table  # business metadata is enrichment's job


def test_enrichment_patch_ops(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder()
    _run(descriptor, rec, _settings())
    (ops,) = rec.by_path(f"/api/v1/tables/{TABLE_ID}")
    by_target = {op["path"]: op for op in ops}
    assert {t["tagFQN"] for t in by_target["/tags"]["value"]} == {"Tabella.crm", "Tabella.internal"}
    assert by_target["/domains"]["value"] == [{"id": DOMAIN_ID, "type": "domain"}]
    assert "/extension" not in by_target  # fixture has no custom properties
    pii_ops = [op for op in ops if op["path"].startswith("/columns/")]
    # email (index 1) and full_name (index 2)
    assert {op["path"] for op in pii_ops} == {"/columns/1/tags", "/columns/2/tags"}
    assert all(op["value"] == [
        {"tagFQN": "PII.Sensitive", "labelType": "Manual", "state": "Confirmed",
         "source": "Classification"}
    ] for op in pii_ops)


def test_ingest_mode_polls_then_enriches_without_creating(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder(table_lookup_misses=2)
    _run(descriptor, rec, _settings(mode="ingest"))
    paths = rec.paths()
    assert "/api/v1/tables" not in paths  # never creates the entity
    assert paths.count(f"/api/v1/tables/name/{table_fqn(descriptor, _settings())}") == 3
    assert f"/api/v1/tables/{TABLE_ID}" in paths  # enrichment PATCH
    assert paths[-1] == "/api/v1/dataContracts"


def test_ingest_mode_triggers_pipeline_when_configured(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder()
    _run(descriptor, rec, _settings(mode="ingest", pipeline_fqn="glue-nightly"))
    paths = rec.paths()
    assert paths[0] == "/api/v1/services/ingestionPipelines/name/glue-nightly"
    assert paths[1] == "/api/v1/services/ingestionPipelines/trigger/pipe-1"


def test_ingest_timeout_raises(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder(table_lookup_misses=10_000)
    with pytest.raises(IngestTimeout, match="did not appear"):
        _run(descriptor, rec, _settings(mode="ingest", poll_timeout=0.0))


def test_fqn_quotes_dotted_source_names(tmp_path, customers_manifest):
    customers_manifest.source.name = "ipaddress.com"
    descriptor = _descriptor(tmp_path, customers_manifest)
    assert table_fqn(descriptor, _settings()) == 'tabella.default."ipaddress.com".customers'


def test_contract_references_table_id(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder()
    _run(descriptor, rec, _settings())
    (contract,) = rec.by_path("/api/v1/dataContracts")
    assert contract["entity"] == {"id": TABLE_ID, "type": "table"}
    assert {c["name"] for c in contract["schema"]} == {"id", "email", "full_name"}


def test_no_contract_fields_skips_contract(tmp_path, customers_manifest):
    customers_manifest.contract.fields = []
    descriptor = _descriptor(tmp_path, customers_manifest)
    rec = Recorder()
    _run(descriptor, rec, _settings())
    assert "/api/v1/dataContracts" not in rec.paths()


def test_http_errors_surface_clearly(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    client = OpenMetadataClient(
        host="http://om.test",
        transport=httpx.MockTransport(lambda r: httpx.Response(401, text="unauthorized")),
    )
    with pytest.raises(OpenMetadataError, match="401"):
        OpenMetadataCatalog(client, _settings()).upsert_asset(descriptor)


# ---------- vocabulary registration (governance registry -> OM) ----------


def _catalog(recorder):
    client = OpenMetadataClient(
        host="http://om.test", token="t", transport=httpx.MockTransport(recorder)
    )
    return OpenMetadataCatalog(client, _settings(), sleep=lambda s: None)


def test_ensure_tags_creates_classification_then_tags():
    recorder = Recorder()
    _catalog(recorder).ensure_tags(["phi", "cui"])
    assert recorder.paths() == ["/api/v1/classifications", "/api/v1/tags", "/api/v1/tags"]
    (classification,) = recorder.by_path("/api/v1/classifications")
    assert classification["name"] == "Tabella"
    tag_bodies = recorder.by_path("/api/v1/tags")
    assert [t["name"] for t in tag_bodies] == ["phi", "cui"]
    assert all(t["classification"] == "Tabella" for t in tag_bodies)


def test_register_custom_properties_text_and_select():
    recorder = Recorder()
    _catalog(recorder).register_custom_properties(
        "table",
        [
            {"name": "steward", "kind": "text", "description": "Steward email"},
            {"name": "phi_category", "kind": "select", "options": ["demographic", "medical"]},
        ],
    )
    paths = recorder.paths()
    # entity type resolved once, each field type resolved once, one PUT per property
    assert paths.count("/api/v1/metadata/types/name/table") == 1
    assert paths.count("/api/v1/metadata/types/name/string") == 1
    assert paths.count("/api/v1/metadata/types/name/enum") == 1
    puts = recorder.by_path("/api/v1/metadata/types/type-table")
    assert len(puts) == 2
    text_prop, select_prop = puts
    assert text_prop["name"] == "steward"
    assert text_prop["description"] == "Steward email"
    assert text_prop["propertyType"] == {"id": "type-string", "type": "type"}
    assert select_prop["propertyType"] == {"id": "type-enum", "type": "type"}
    assert select_prop["customPropertyConfig"]["config"] == {
        "values": ["demographic", "medical"],
        "multiSelect": False,
    }


def test_register_custom_properties_caches_type_ids():
    recorder = Recorder()
    _catalog(recorder).register_custom_properties(
        "domain",
        [{"name": "a", "kind": "text"}, {"name": "b", "kind": "text"}],
    )
    assert recorder.paths().count("/api/v1/metadata/types/name/string") == 1
    assert len(recorder.by_path("/api/v1/metadata/types/type-domain")) == 2
