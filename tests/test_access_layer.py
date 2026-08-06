import pytest
from fastapi.testclient import TestClient
from tabella_core.pipeline import register
from tabella_core.store import load_catalog
from tabella_enable.rest import build_app


@pytest.fixture
def client(tmp_path, customers_manifest):
    register(customers_manifest, tmp_path / "catalog")
    return TestClient(build_app(load_catalog(tmp_path / "catalog")))


def test_list_and_get_asset(client):
    listed = client.get("/assets").json()["data"]
    assert [a["id"] for a in listed] == ["sales.customers"]
    full = client.get("/assets/sales.customers").json()
    assert full["schema"]["primary_key"] == ["id"]


def test_records_with_equality_filter(client):
    body = client.get("/assets/sales.customers/records", params={"country": "FR"}).json()
    assert [r["full_name"] for r in body["data"]] == ["Blaise Pascal"]
    assert body["pagination"]["total"] == 1
    assert body["asset"] == "sales.customers"


def test_integer_filter_coercion(client):
    body = client.get("/assets/sales.customers/records", params={"id": "2"}).json()
    assert body["data"][0]["email"] == "b@example.com"


def test_unknown_field_is_400(client):
    resp = client.get("/assets/sales.customers/records", params={"countr": "FR"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unknown_field"


def test_missing_asset_is_404(client):
    resp = client.get("/assets/sales.nope/records")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "asset_not_found"


def test_limit_capped_at_row_limit(tmp_path, customers_manifest):
    customers_manifest.access.row_limit = 2
    register(customers_manifest, tmp_path / "catalog")
    client = TestClient(build_app(load_catalog(tmp_path / "catalog")))
    body = client.get("/assets/sales.customers/records", params={"limit": 999}).json()
    assert body["pagination"]["limit"] == 2
    assert len(body["data"]) == 2


def test_api_disabled_asset_not_served(tmp_path, customers_manifest):
    customers_manifest.enablement.api = False
    register(customers_manifest, tmp_path / "catalog")
    client = TestClient(build_app(load_catalog(tmp_path / "catalog")))
    assert client.get("/assets").json()["data"] == []
    assert client.get("/assets/sales.customers").status_code == 404
