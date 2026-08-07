"""End-to-end tests for the files connector (file:// scheme; s3:// shares the code)."""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from tabella_core.connectors import get_connector
from tabella_core.models import AssetMeta, FieldType, OnboardingManifest, SourceRef
from tabella_core.pipeline import discover, register


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "sales").mkdir()
    (tmp_path / "sales" / "customers.csv").write_text(
        "id,email,country,signup_score\n"
        "1,a@example.com,GB,0.9\n"
        "2,b@example.com,FR,0.4\n"
        "3,c@example.com,FR,0.7\n"
    )
    pq.write_table(
        pa.table(
            {
                "id": pa.array([1, 2], type=pa.int64()),
                "body": pa.array(["hello", "world"]),
                "created_at": pa.array([1700000000000, 1700000100000], type=pa.timestamp("ms")),
            }
        ),
        tmp_path / "tickets.parquet",
    )
    (tmp_path / "notes.txt").write_text("ignored")
    return f"file://{tmp_path}"


def test_list_assets_finds_csv_and_parquet_only(data_dir):
    assert get_connector("file").list_assets(data_dir) == [
        "sales/customers.csv",
        "tickets.parquet",
    ]


def test_s3_scheme_resolves_to_files_connector(data_dir):
    assert type(get_connector("s3")) is type(get_connector("file"))


def test_introspect_csv_types(data_dir):
    schema = get_connector("file").introspect(data_dir, "sales/customers.csv")
    types = {f.name: f.type for f in schema.fields}
    assert types == {
        "id": FieldType.integer,
        "email": FieldType.string,
        "country": FieldType.string,
        "signup_score": FieldType.number,
    }


def test_introspect_parquet_types(data_dir):
    schema = get_connector("file").introspect(data_dir, "tickets.parquet")
    types = {f.name: f.type for f in schema.fields}
    assert types == {
        "id": FieldType.integer,
        "body": FieldType.string,
        "created_at": FieldType.datetime,
    }


def test_missing_file_raises(data_dir):
    with pytest.raises(KeyError):
        get_connector("file").introspect(data_dir, "nope.csv")


def test_register_and_fetch_with_filters(tmp_path, data_dir):
    manifest = OnboardingManifest(
        asset=AssetMeta(name="customers", domain="sales"),
        source=SourceRef(
            connector="file", name="lake", uri=data_dir, native_name="sales/customers.csv"
        ),
    )
    descriptor = register(manifest, tmp_path / "catalog").descriptor
    records, total = get_connector("file").fetch(descriptor, filters={"country": "FR"})
    assert total == 2
    assert [r["id"] for r in records] == [2, 3]
    page, total = get_connector("file").fetch(
        descriptor, filters={"country": "FR"}, limit=1, offset=1
    )
    assert total == 2 and [r["id"] for r in page] == [3]
    with pytest.raises(KeyError):
        get_connector("file").fetch(descriptor, filters={"nope": 1})


def test_discover_drafts_file_manifests(data_dir):
    drafts = discover(data_dir, domain="sales")
    assert [m.source.native_name for m in drafts] == ["sales/customers.csv", "tickets.parquet"]
    assert all(m.source.connector == "file" for m in drafts)
