import jsonschema
from udap_core.models import Classification
from udap_core.pipeline import register
from udap_enable.tools import build_manifest


def _descriptor(tmp_path, manifest):
    return register(manifest, tmp_path / "catalog").descriptor


def test_tool_manifest_shape(tmp_path, customers_manifest):
    d = _descriptor(tmp_path, customers_manifest)
    manifest = build_manifest([d])
    (tool,) = manifest["tools"]
    assert tool["name"] == "query_sales_customers"
    assert tool["endpoint"]["path"] == "/assets/sales.customers/records"
    jsonschema.Draft202012Validator.check_schema(tool["input_schema"])


def test_pii_fields_excluded_from_filters(tmp_path, customers_manifest):
    d = _descriptor(tmp_path, customers_manifest)
    props = build_manifest([d])["tools"][0]["input_schema"]["properties"]
    assert "email" not in props and "full_name" not in props
    assert "country" in props and "limit" in props


def test_restricted_assets_excluded_by_default(tmp_path, customers_manifest):
    customers_manifest.asset.classification = Classification.restricted
    d = _descriptor(tmp_path, customers_manifest)
    assert build_manifest([d])["tools"] == []
    assert len(build_manifest([d], include_restricted=True)["tools"]) == 1


def test_mcp_disabled_asset_excluded(tmp_path, customers_manifest):
    customers_manifest.enablement.mcp = False
    d = _descriptor(tmp_path, customers_manifest)
    assert build_manifest([d])["tools"] == []
