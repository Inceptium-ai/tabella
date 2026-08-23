"""Tests for the deployment tooling: the Lambda registrar handler and
`tabella init` sandbox generation — all offline (fake S3, no docker start)."""

import json

import pytest
import yaml
from tabella_cli.lambda_handler import handler, register_manifest_file
from tabella_cli.sandbox import init_sandbox
from tabella_core.manifest import dump_manifest_yaml


class FakeS3:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = dict(objects)
        self.puts: list[tuple[str, str, bytes]] = []

    def get_object(self, Bucket, Key):
        import io

        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.puts.append((Bucket, Key, Body))


@pytest.fixture
def s3_event():
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "intake"},
                    "object": {"key": "manifests/customers.yaml"},
                }
            }
        ]
    }


def test_handler_registers_and_writes_descriptor(
    tmp_path, monkeypatch, customers_manifest, s3_event
):
    monkeypatch.chdir(tmp_path)  # keep /tmp catalog writes contained per-test
    fake = FakeS3({"manifests/customers.yaml": dump_manifest_yaml(customers_manifest).encode()})
    result = handler(s3_event, s3_client=fake)

    assert result["registered"][0]["asset"] == "sales.customers"
    assert result["registered"][0]["applied"] == []  # no backends enabled by default
    (bucket, key, body) = fake.puts[0]
    assert (bucket, key) == ("intake", "catalog/sales.customers.json")
    descriptor = json.loads(body)
    assert descriptor["schema"]["primary_key"] == ["id"]


def test_handler_raises_on_contract_violation(tmp_path, monkeypatch, customers_manifest, s3_event):
    monkeypatch.chdir(tmp_path)
    customers_manifest.contract.fields[0].name = "not_a_real_field"
    fake = FakeS3({"manifests/customers.yaml": dump_manifest_yaml(customers_manifest).encode()})
    with pytest.raises(RuntimeError, match="1 manifest\\(s\\) failed"):
        handler(s3_event, s3_client=fake)
    assert fake.puts == []  # nothing written for the failed manifest


def test_register_manifest_file_accepts_json(tmp_path, customers_manifest):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(customers_manifest.to_json_dict()))
    result = register_manifest_file(path, catalog_dir=tmp_path / "catalog")
    assert result.descriptor.id == "sales.customers"


def test_init_sandbox_writes_valid_compose(tmp_path):
    code = init_sandbox(tmp_path / "sandbox", start=False)
    assert code == 0
    compose = yaml.safe_load((tmp_path / "sandbox" / "docker-compose.yml").read_text())
    services = set(compose["services"])
    assert {"openmetadata", "om-mysql", "om-opensearch", "postgres", "minio"} <= services
    assert compose["services"]["postgres"]["image"].startswith("pgvector/")
    assert "OM_VERSION" in (tmp_path / "sandbox" / ".env").read_text()
