"""Postgres connector tests.

Pure-function coverage runs always; live-server tests are gated behind
TABELLA_TEST_PG_URI (set it to a reachable postgres:// URI to enable).
"""

import os

import pytest
from tabella_connectors.postgres import (
    PostgresConnector,
    canonical_type,
    quote_ident,
    split_native_name,
)
from tabella_core.connectors import get_connector
from tabella_core.models import FieldType

LIVE_URI = os.environ.get("TABELLA_TEST_PG_URI")


def test_registered_under_both_schemes():
    assert isinstance(get_connector("postgres"), PostgresConnector)
    assert isinstance(get_connector("postgresql"), PostgresConnector)


def test_canonical_type_mapping():
    assert canonical_type("integer") == FieldType.integer
    assert canonical_type("BIGINT") == FieldType.integer
    assert canonical_type("numeric") == FieldType.number
    assert canonical_type("character varying") == FieldType.string
    assert canonical_type("uuid") == FieldType.string
    assert canonical_type("timestamp with time zone") == FieldType.datetime
    assert canonical_type("jsonb") == FieldType.json
    assert canonical_type("bytea") == FieldType.binary
    assert canonical_type("tsvector") == FieldType.unknown


def test_split_native_name():
    assert split_native_name("public.customers") == ("public", "customers")
    assert split_native_name("customers") == ("public", "customers")
    assert split_native_name("analytics.events") == ("analytics", "events")


def test_quote_ident_escapes_quotes():
    assert quote_ident("plain") == '"plain"'
    assert quote_ident('we"ird') == '"we""ird"'


@pytest.mark.skipif(not LIVE_URI, reason="TABELLA_TEST_PG_URI not set")
def test_live_list_and_introspect():
    connector = get_connector("postgres")
    assets = connector.list_assets(LIVE_URI)
    assert assets, "expected at least one table in the live test database"
    schema = connector.introspect(LIVE_URI, assets[0])
    assert schema.fields
