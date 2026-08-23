"""AWS Lambda entry point for the reference deployment (deploy/aws).

Flow: a spec-compliant onboarding manifest JSON lands in the intake bucket
(`manifests/` prefix) -> S3 ObjectCreated invokes this handler -> the manifest
is validated and registered (contract verification, Glue governance, OM
catalog per environment config) -> the resulting Asset Descriptor is written
back to the catalog prefix.

Environment:
    TABELLA_CATALOG_BUCKET   descriptor output bucket (default: event bucket)
    TABELLA_CATALOG_PREFIX   descriptor output prefix (default: catalog/)
    TABELLA_ENABLE_GLUE      "true" to apply the Glue governance backend
    TABELLA_ENABLE_OM        "true" to mirror into OpenMetadata
    TABELLA_OM_TOKEN_SECRET_ARN
                             Secrets Manager secret holding the OM JWT; loaded
                             once per container into TABELLA_OM_TOKEN
    TABELLA_OM_HOST / TABELLA_OM_MODE / ...   as documented in tabella-catalog-om

Failures raise after processing all records, so Lambda's retry/DLQ semantics
apply; per-record outcomes are logged either way.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote_plus

import tabella_connectors  # noqa: F401  (registers built-in connectors)
from tabella_core.manifest import load_manifest
from tabella_core.pipeline import register

_TOKEN_LOADED = False


def _load_om_token() -> None:
    """Fetch the OM JWT from Secrets Manager once per container."""
    global _TOKEN_LOADED
    secret_arn = os.environ.get("TABELLA_OM_TOKEN_SECRET_ARN")
    if _TOKEN_LOADED or not secret_arn or os.environ.get("TABELLA_OM_TOKEN"):
        _TOKEN_LOADED = True
        return
    import boto3

    value = boto3.client("secretsmanager").get_secret_value(SecretId=secret_arn)
    os.environ["TABELLA_OM_TOKEN"] = value["SecretString"]
    _TOKEN_LOADED = True


def build_backends() -> tuple[list, list]:
    """(catalog_backends, governance_backends) from environment flags."""
    catalog, governance = [], []
    if os.environ.get("TABELLA_ENABLE_GLUE", "").lower() == "true":
        from tabella_governance_aws import GlueGovernance

        governance.append(GlueGovernance())
    if os.environ.get("TABELLA_ENABLE_OM", "").lower() == "true":
        _load_om_token()
        from tabella_catalog_om import OpenMetadataCatalog

        catalog.append(OpenMetadataCatalog())
    return catalog, governance


def register_manifest_file(
    path: str | Path,
    *,
    catalog_dir: str | Path = "/tmp/tabella-catalog",  # noqa: S108 (Lambda scratch space)
    catalog_backends: list | None = None,
    governance_backends: list | None = None,
):
    """Validate + register one manifest file; returns the RegistrationResult."""
    manifest = load_manifest(path)
    return register(
        manifest,
        catalog_dir,
        catalog_backends=catalog_backends,
        governance_backends=governance_backends,
    )


def handler(event, context=None, *, s3_client=None):
    import boto3

    s3 = s3_client or boto3.client("s3")
    catalog_backends, governance_backends = build_backends()
    catalog_prefix = os.environ.get("TABELLA_CATALOG_PREFIX", "catalog/")

    outcomes, errors = [], []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        out_bucket = os.environ.get("TABELLA_CATALOG_BUCKET", bucket)
        try:
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            name = Path(key).name or "manifest.yaml"
            if not name.endswith((".json", ".yaml", ".yml")):
                name += ".yaml"
            local = Path("/tmp") / name  # noqa: S108 (Lambda scratch space)
            local.write_bytes(body)
            result = register_manifest_file(
                local,
                catalog_backends=catalog_backends,
                governance_backends=governance_backends,
            )
            descriptor_key = f"{catalog_prefix}{result.descriptor.id}.json"
            s3.put_object(
                Bucket=out_bucket,
                Key=descriptor_key,
                Body=json.dumps(result.descriptor.to_json_dict(), indent=2).encode(),
                ContentType="application/json",
            )
            outcome = {
                "manifest": key,
                "asset": result.descriptor.id,
                "descriptor": f"s3://{out_bucket}/{descriptor_key}",
                "applied": [*result.governance_backends, *result.catalog_backends],
            }
            print(json.dumps({"level": "info", "registered": outcome}))
            outcomes.append(outcome)
        except Exception as exc:  # log every record before deciding to raise
            print(json.dumps({"level": "error", "manifest": key, "error": str(exc)}))
            errors.append({"manifest": key, "error": str(exc)})

    if errors:
        raise RuntimeError(f"{len(errors)} manifest(s) failed: {json.dumps(errors)}")
    return {"registered": outcomes}
