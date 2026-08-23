"""Declared-schema registration through the api connector (placeholder assets)."""

import pytest
from tabella_core.connectors import get_connector, scheme_of
from tabella_core.models import (
    AssetMeta,
    Contract,
    ContractField,
    EnablementProfile,
    FieldType,
    OnboardingManifest,
    SourceRef,
)
from tabella_core.pipeline import register


def api_manifest(**overrides):
    manifest = OnboardingManifest(
        asset=AssetMeta(
            name="users",
            domain="identity",
            owner="platform@example.com",
            tags=["api"],
        ),
        source=SourceRef(
            connector="api",
            name="userservice",
            uri="https://api.example.com",
            native_name="/v1/users",
        ),
        contract=Contract(
            fields=[
                ContractField(name="id", type=FieldType.integer, required=True),
                ContractField(name="email", type=FieldType.string, required=True, pii=True),
                ContractField(name="display_name"),
            ]
        ),
        enablement=EnablementProfile(api=False, mcp=False),
    )
    for key, value in overrides.items():
        setattr(manifest, key, value)
    return manifest


def test_scheme_resolution():
    assert scheme_of("https://api.example.com") == "https"
    connector = get_connector("https")
    assert connector.scheme == "api"
    assert connector.introspectable is False
    assert connector.source_name("https://api.example.com:8443/base") == "api.example.com"


def test_register_builds_schema_from_contract(tmp_path):
    result = register(api_manifest(), tmp_path)
    schema = result.descriptor.asset_schema
    assert [f.name for f in schema.fields] == ["id", "email", "display_name"]
    email = schema.field("email")
    assert email.pii is True
    assert email.nullable is False
    assert schema.field("display_name").nullable is True
    assert schema.field("display_name").type == FieldType.unknown
    assert result.descriptor.source.native_name == "/v1/users"
    assert (tmp_path / "identity.users.json").is_file()


def test_register_without_contract_is_pure_placeholder(tmp_path):
    manifest = api_manifest(contract=Contract(fields=[]))
    result = register(manifest, tmp_path)
    assert result.descriptor.asset_schema.fields == []


def test_fetch_refuses(tmp_path):
    manifest = api_manifest()
    connector = get_connector("api")
    with pytest.raises(NotImplementedError):
        connector.fetch(register(manifest, tmp_path).descriptor)
