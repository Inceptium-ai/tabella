"""Models for the Tabella spec artifacts: Onboarding Manifest and Asset Descriptor.

Serialized forms always use the spec's field names (`schema`, not
`asset_schema`): dump with `to_json_dict()`.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

TABELLA_SPEC_VERSION = "0.1.0"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "-", text.lower()).strip("-")


class FieldType(StrEnum):
    string = "string"
    integer = "integer"
    number = "number"
    boolean = "boolean"
    date = "date"
    datetime = "datetime"
    json = "json"
    binary = "binary"
    unknown = "unknown"


class Classification(StrEnum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class FieldDef(BaseModel):
    name: str
    type: FieldType = FieldType.unknown
    nullable: bool = True
    description: str | None = None
    semantic_tags: list[str] = Field(default_factory=list)
    pii: bool = False


class ForeignKey(BaseModel):
    fields: list[str]
    ref_asset: str
    ref_fields: list[str]


class AssetSchema(BaseModel):
    fields: list[FieldDef]
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKey] = Field(default_factory=list)

    def field(self, name: str) -> FieldDef | None:
        return next((f for f in self.fields if f.name == name), None)


class SourceRef(BaseModel):
    connector: str
    uri: str
    native_name: str


class AccessPolicy(BaseModel):
    read_roles: list[str] = Field(default_factory=lambda: ["*"])
    row_limit: int = 1000


class ChunkingStrategy(StrEnum):
    semantic = "semantic"
    fixed = "fixed"
    document = "document"


class VectorizationProfile(BaseModel):
    enabled: bool = False
    content_fields: list[str] = Field(default_factory=list)
    chunking: ChunkingStrategy = ChunkingStrategy.fixed
    chunk_size: int = 512
    embedding_model: str | None = None


class EnablementProfile(BaseModel):
    api: bool = True
    mcp: bool = True
    vectorization: VectorizationProfile = Field(default_factory=VectorizationProfile)


class ContractField(BaseModel):
    name: str
    type: FieldType | None = None
    required: bool = False
    pii: bool = False


class Contract(BaseModel):
    fields: list[ContractField] = Field(default_factory=list)


class AssetMeta(BaseModel):
    name: str
    description: str | None = None
    owner: str | None = None
    domain: str
    tags: list[str] = Field(default_factory=list)
    classification: Classification = Classification.internal


class OnboardingManifest(BaseModel):
    """The registration entry artifact (spec/onboarding-manifest.md)."""

    tabella_version: str = TABELLA_SPEC_VERSION
    asset: AssetMeta
    source: SourceRef
    contract: Contract = Field(default_factory=Contract)
    access: AccessPolicy = Field(default_factory=AccessPolicy)
    enablement: EnablementProfile = Field(default_factory=EnablementProfile)
    custom_properties: dict[str, str] = Field(default_factory=dict)

    @property
    def asset_id(self) -> str:
        return f"{slug(self.asset.domain)}.{slug(self.asset.name)}"

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")


class AssetDescriptor(BaseModel):
    """The cataloged asset record (spec/asset-descriptor.md)."""

    model_config = ConfigDict(populate_by_name=True)

    tabella_version: str = TABELLA_SPEC_VERSION
    id: str = Field(pattern=r"^[a-z0-9_.-]+$")
    name: str
    description: str | None = None
    owner: str | None = None
    domain: str
    tags: list[str] = Field(default_factory=list)
    classification: Classification = Classification.internal
    source: SourceRef
    asset_schema: AssetSchema = Field(alias="schema")
    contract: Contract = Field(default_factory=Contract)
    access: AccessPolicy = Field(default_factory=AccessPolicy)
    enablement: EnablementProfile = Field(default_factory=EnablementProfile)
    custom_properties: dict[str, str] = Field(default_factory=dict)
    lineage: list[str] = Field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "classification": self.classification.value,
            "tags": self.tags,
        }
