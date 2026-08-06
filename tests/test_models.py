import json
from pathlib import Path

import jsonschema
import yaml
from udap_core.manifest import dump_manifest_yaml, load_manifest
from udap_core.models import AssetDescriptor, OnboardingManifest

SCHEMAS = Path(__file__).parent.parent / "spec" / "schemas"


def test_manifest_yaml_round_trip(tmp_path, customers_manifest):
    path = tmp_path / "customers.yaml"
    path.write_text(dump_manifest_yaml(customers_manifest))
    loaded = load_manifest(path)
    assert loaded == customers_manifest
    assert loaded.asset_id == "sales.customers"


def test_manifest_json_form_submission(tmp_path, customers_manifest):
    path = tmp_path / "customers.json"
    path.write_text(json.dumps(customers_manifest.to_json_dict()))
    assert load_manifest(path) == customers_manifest


def test_manifest_validates_against_spec_schema(customers_manifest):
    schema = json.loads((SCHEMAS / "onboarding-manifest.schema.json").read_text())
    jsonschema.validate(customers_manifest.to_json_dict(), schema)


def test_manifest_defaults():
    data = yaml.safe_load(
        """
        udap_version: 0.1.0
        asset: {name: Events Log, domain: Platform Ops}
        source: {connector: sqlite, uri: sqlite:///x.db, native_name: events}
        """
    )
    manifest = OnboardingManifest.model_validate(data)
    assert manifest.asset_id == "platform-ops.events-log"
    assert manifest.enablement.api and manifest.enablement.mcp
    assert manifest.access.read_roles == ["*"]
    assert not manifest.enablement.vectorization.enabled


def test_descriptor_schema_alias_round_trip(customers_manifest, demo_db):
    from udap_core.connectors import get_connector

    schema = get_connector("sqlite").introspect(demo_db, "customers")
    descriptor = AssetDescriptor(
        id="sales.customers",
        name="customers",
        domain="sales",
        source=customers_manifest.source,
        schema=schema,
    )
    dumped = descriptor.to_json_dict()
    assert "schema" in dumped and "asset_schema" not in dumped
    assert AssetDescriptor.model_validate(dumped) == descriptor
