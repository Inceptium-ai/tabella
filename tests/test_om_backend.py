"""Request-shape tests for the OpenMetadata backend, against a mocked transport.

These pin the payloads to the vendored OM 1.12.x schemas (packages/
tabella-catalog-om/reference/) — live-server validation happens when
deploy/sandbox lands.
"""

import json

import httpx
import pytest
from tabella_catalog_om import OpenMetadataCatalog, OpenMetadataClient, OpenMetadataError
from tabella_core.pipeline import register


@pytest.fixture
def om(tmp_path, customers_manifest):
    """Register the demo asset, then upsert it through a capturing OM client."""
    descriptor = register(customers_manifest, tmp_path / "catalog").descriptor
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append((request.url.path, payload))
        body = {"id": "11111111-2222-3333-4444-555555555555", **payload}
        return httpx.Response(200, json=body)

    client = OpenMetadataClient(
        host="http://om.test", token="t", transport=httpx.MockTransport(handler)
    )
    OpenMetadataCatalog(client).upsert_asset(descriptor)
    return descriptor, dict_by_path(calls), calls


def dict_by_path(calls):
    grouped: dict[str, list[dict]] = {}
    for path, payload in calls:
        grouped.setdefault(path, []).append(payload)
    return grouped


def test_call_order_ends_with_table_then_contract(om):
    _, _, calls = om
    paths = [p for p, _ in calls]
    assert paths.index("/api/v1/tables") == len(paths) - 2
    assert paths[-1] == "/api/v1/dataContracts"
    assert paths.index("/api/v1/services/databaseServices") < paths.index("/api/v1/databases")
    assert paths.index("/api/v1/databases") < paths.index("/api/v1/databaseSchemas")


def test_tags_and_classification_ensured(om):
    descriptor, by_path, _ = om
    assert by_path["/api/v1/classifications"][0]["name"] == "Tabella"
    tag_names = {t["name"] for t in by_path["/api/v1/tags"]}
    assert tag_names == {"crm", "internal"}


def test_table_payload_shape(om):
    descriptor, by_path, _ = om
    (table,) = by_path["/api/v1/tables"]
    assert table["name"] == "customers"
    assert table["databaseSchema"].startswith("tabella-sqlite.")
    assert table["domains"] == ["sales"]
    assert {t["tagFQN"] for t in table["tags"]} == {"Tabella.crm", "Tabella.internal"}

    cols = {c["name"]: c for c in table["columns"]}
    assert cols["id"]["dataType"] == "INT" and cols["id"]["constraint"] == "PRIMARY_KEY"
    assert cols["email"]["dataType"] == "STRING"
    assert cols["email"]["tags"] == [{"tagFQN": "PII.Sensitive"}]
    assert cols["created_at"]["dataType"] == "DATETIME"
    assert "tags" not in cols["country"]
    # createTable required fields per vendored schema
    assert {"name", "columns", "databaseSchema"} <= set(table)


def test_contract_references_table_id(om):
    descriptor, by_path, _ = om
    (contract,) = by_path["/api/v1/dataContracts"]
    assert contract["entity"] == {
        "id": "11111111-2222-3333-4444-555555555555",
        "type": "table",
    }
    assert contract["name"] == "sales.customers-contract"
    declared = {c["name"] for c in contract["schema"]}
    assert declared == {"id", "email", "full_name"}


def test_no_contract_fields_skips_contract(tmp_path, customers_manifest):
    customers_manifest.contract.fields = []
    descriptor = register(customers_manifest, tmp_path / "catalog").descriptor
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"id": "x", "name": "y"})

    client = OpenMetadataClient(host="http://om.test", transport=httpx.MockTransport(handler))
    OpenMetadataCatalog(client).upsert_asset(descriptor)
    assert "/api/v1/dataContracts" not in paths


def test_http_errors_surface_clearly(tmp_path, customers_manifest):
    descriptor = register(customers_manifest, tmp_path / "catalog").descriptor
    client = OpenMetadataClient(
        host="http://om.test",
        transport=httpx.MockTransport(lambda r: httpx.Response(401, text="unauthorized")),
    )
    with pytest.raises(OpenMetadataError, match="401"):
        OpenMetadataCatalog(client).upsert_asset(descriptor)
