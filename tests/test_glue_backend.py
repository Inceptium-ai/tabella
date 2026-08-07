"""Glue governance backend tests with a recording fake client.

Shapes follow boto3 Glue create_database/create_table/update_table; live
validation against AWS happens with the M3 reference deployment.
"""

import pytest
from tabella_core.pipeline import register
from tabella_governance_aws import GlueGovernance
from tabella_governance_aws.glue import table_input


class _AlreadyExists(Exception):
    pass


class _NotFound(Exception):
    pass


class FakeGlue:
    class exceptions:
        AlreadyExistsException = _AlreadyExists
        EntityNotFoundException = _NotFound

    def __init__(self, *, existing_dbs=(), existing_tables=()):
        self.dbs = set(existing_dbs)
        self.tables = dict.fromkeys(existing_tables)
        self.calls = []

    def create_database(self, DatabaseInput):
        self.calls.append(("create_database", DatabaseInput))
        if DatabaseInput["Name"] in self.dbs:
            raise _AlreadyExists()
        self.dbs.add(DatabaseInput["Name"])

    def get_table(self, DatabaseName, Name):
        self.calls.append(("get_table", DatabaseName, Name))
        if (DatabaseName, Name) not in self.tables:
            raise _NotFound()
        return {"Table": {"Name": Name}}

    def create_table(self, DatabaseName, TableInput):
        self.calls.append(("create_table", DatabaseName, TableInput))
        self.tables[(DatabaseName, TableInput["Name"])] = TableInput

    def update_table(self, DatabaseName, TableInput):
        self.calls.append(("update_table", DatabaseName, TableInput))
        self.tables[(DatabaseName, TableInput["Name"])] = TableInput


@pytest.fixture
def descriptor(tmp_path, customers_manifest):
    return register(customers_manifest, tmp_path / "catalog").descriptor


def test_creates_database_and_table_under_source(descriptor):
    glue = FakeGlue()
    GlueGovernance(glue).apply(descriptor)
    assert ("retail", "customers") in glue.tables
    names = [c[0] for c in glue.calls]
    assert names == ["create_database", "get_table", "create_table"]


def test_reapply_updates_existing_table(descriptor):
    glue = FakeGlue(existing_dbs=["retail"], existing_tables=[("retail", "customers")])
    GlueGovernance(glue).apply(descriptor)
    names = [c[0] for c in glue.calls]
    assert names == ["create_database", "get_table", "update_table"]


def test_table_input_shape(descriptor):
    payload = table_input(descriptor)
    assert payload["Name"] == "customers"
    columns = {c["Name"]: c["Type"] for c in payload["StorageDescriptor"]["Columns"]}
    assert columns["id"] == "bigint"
    assert columns["email"] == "string"
    assert columns["created_at"] == "timestamp"
    assert payload["Parameters"]["tabella:id"] == "sales.customers"
    assert payload["Parameters"]["tabella:domain"] == "sales"
    assert payload["Parameters"]["tabella:classification"] == "internal"
