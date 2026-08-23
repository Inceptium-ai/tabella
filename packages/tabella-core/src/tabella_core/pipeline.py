"""The registration pipeline: manifest -> verified Asset Descriptor -> backends.

Local reference flow (spec/onboarding-manifest.md, "Registration semantics"):

    validate -> introspect -> verify contract -> descriptor -> local store
             -> catalog backend(s) -> governance backend(s)

Enablement artifact generation (APIs, tools, RAG) is performed by tabella-enable
generators over the resulting catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tabella_core.connectors import get_connector
from tabella_core.interfaces import CatalogBackend, GovernanceBackend
from tabella_core.models import (
    AssetDescriptor,
    AssetMeta,
    AssetSchema,
    Classification,
    FieldDef,
    FieldType,
    OnboardingManifest,
    SourceRef,
    slug,
)
from tabella_core.store import save_descriptor


class ContractViolation(Exception):
    def __init__(self, asset_id: str, problems: list[str]):
        self.asset_id = asset_id
        self.problems = problems
        super().__init__(
            f"Contract violations for '{asset_id}':\n  - " + "\n  - ".join(problems)
        )


def _verify_contract(manifest: OnboardingManifest, schema: AssetSchema) -> list[str]:
    problems = []
    for spec in manifest.contract.fields:
        actual = schema.field(spec.name)
        if actual is None:
            problems.append(f"declared field '{spec.name}' not found in source")
            continue
        if spec.type is not None and actual.type != spec.type:
            problems.append(
                f"field '{spec.name}': declared type {spec.type.value},"
                f" source has {actual.type.value}"
            )
        if spec.required and actual.nullable:
            problems.append(f"field '{spec.name}' declared required but is nullable in source")
    return problems


def _apply_contract_metadata(manifest: OnboardingManifest, schema: AssetSchema) -> None:
    for spec in manifest.contract.fields:
        actual = schema.field(spec.name)
        if actual and spec.pii:
            actual.pii = True


@dataclass
class RegistrationResult:
    descriptor: AssetDescriptor
    descriptor_path: Path
    catalog_backends: list[str] = field(default_factory=list)
    governance_backends: list[str] = field(default_factory=list)


def _schema_from_contract(manifest: OnboardingManifest) -> AssetSchema:
    """Declared-schema registration: for non-introspectable sources the
    contract IS the schema (a placeholder catalog entry that still knows its
    shape, ownership, and PII surface)."""
    return AssetSchema(
        fields=[
            FieldDef(
                name=spec.name,
                type=spec.type or FieldType.unknown,
                nullable=not spec.required,
                pii=spec.pii,
            )
            for spec in manifest.contract.fields
        ]
    )


def register(
    manifest: OnboardingManifest,
    catalog_dir: str | Path,
    *,
    catalog_backends: list[CatalogBackend] | None = None,
    governance_backends: list[GovernanceBackend] | None = None,
) -> RegistrationResult:
    connector = get_connector(manifest.source.connector)
    if connector.introspectable:
        schema = connector.introspect(manifest.source.uri, manifest.source.native_name)
        problems = _verify_contract(manifest, schema)
        if problems:
            raise ContractViolation(manifest.asset_id, problems)
        _apply_contract_metadata(manifest, schema)
    else:
        schema = _schema_from_contract(manifest)

    descriptor = AssetDescriptor(
        id=manifest.asset_id,
        name=manifest.asset.name,
        description=manifest.asset.description,
        owner=manifest.asset.owner,
        domain=manifest.asset.domain,
        tags=manifest.asset.tags,
        classification=manifest.asset.classification,
        source=manifest.source,
        schema=schema,
        contract=manifest.contract,
        access=manifest.access,
        enablement=manifest.enablement,
        custom_properties=manifest.custom_properties,
    )
    path = save_descriptor(descriptor, catalog_dir)

    result = RegistrationResult(descriptor=descriptor, descriptor_path=path)
    # Governance first: catalog backends in ingest mode (OM <- Glue ingestion)
    # depend on the governed asset already existing.
    for backend in governance_backends or []:
        backend.apply(descriptor)
        result.governance_backends.append(backend.name)
    for backend in catalog_backends or []:
        backend.upsert_asset(descriptor)
        result.catalog_backends.append(backend.name)
    return result


def discover(
    uri: str,
    *,
    connector_scheme: str | None = None,
    source_name: str | None = None,
    domain: str = "unassigned",
    classification: Classification = Classification.internal,
) -> list[OnboardingManifest]:
    """Draft one Onboarding Manifest per asset found at `uri`, for human review."""
    from tabella_core.connectors import scheme_of

    scheme = connector_scheme or scheme_of(uri)
    connector = get_connector(scheme)
    source = source_name or connector.source_name(uri)
    return [
        OnboardingManifest(
            asset=AssetMeta(
                name=slug(native_name),
                description=None,
                domain=domain,
                classification=classification,
            ),
            source=SourceRef(
                connector=scheme, name=source, uri=uri, native_name=native_name
            ),
        )
        for native_name in connector.list_assets(uri)
    ]
