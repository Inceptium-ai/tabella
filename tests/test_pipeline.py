import json
from pathlib import Path

import jsonschema
import pytest
from udap_core.models import ContractField, FieldType
from udap_core.pipeline import ContractViolation, discover, register

SCHEMAS = Path(__file__).parent.parent / "spec" / "schemas"


def test_register_produces_valid_descriptor(tmp_path, customers_manifest):
    result = register(customers_manifest, tmp_path / "catalog")
    d = result.descriptor
    assert d.id == "sales.customers"
    assert d.asset_schema.primary_key == ["id"]
    assert result.descriptor_path.name == "sales.customers.json"

    schema = json.loads((SCHEMAS / "asset-descriptor.schema.json").read_text())
    jsonschema.validate(json.loads(result.descriptor_path.read_text()), schema)


def test_contract_pii_propagates_to_schema(tmp_path, customers_manifest):
    d = register(customers_manifest, tmp_path / "catalog").descriptor
    assert d.asset_schema.field("email").pii
    assert d.asset_schema.field("full_name").pii
    assert not d.asset_schema.field("country").pii


def test_contract_violations_fail_registration(tmp_path, customers_manifest):
    customers_manifest.contract.fields += [
        ContractField(name="loyalty_tier", required=True),          # missing in source
        ContractField(name="country", type=FieldType.integer),      # wrong type
        ContractField(name="country", required=True),               # nullable in source
    ]
    with pytest.raises(ContractViolation) as exc:
        register(customers_manifest, tmp_path / "catalog")
    assert len(exc.value.problems) == 3
    assert "loyalty_tier" in str(exc.value)


def test_reregistration_is_update(tmp_path, customers_manifest):
    catalog = tmp_path / "catalog"
    register(customers_manifest, catalog)
    customers_manifest.asset.tags.append("updated")
    register(customers_manifest, catalog)
    assert len(list(catalog.glob("*.json"))) == 1
    assert "updated" in json.loads((catalog / "sales.customers.json").read_text())["tags"]


def test_discover_drafts_manifests(demo_db):
    drafts = discover(demo_db, domain="sales")
    assert [m.source.native_name for m in drafts] == ["customers", "orders"]
    schema = json.loads((SCHEMAS / "onboarding-manifest.schema.json").read_text())
    for m in drafts:
        jsonschema.validate(m.to_json_dict(), schema)
        assert m.asset.domain == "sales"
