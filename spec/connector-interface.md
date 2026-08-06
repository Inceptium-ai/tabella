# Tabella Connector Interface — v0.1.0

A **connector** binds a class of physical sources (SQLite, Postgres, S3/files,
a SaaS API…) to Tabella. Connectors have three responsibilities:

1. **Enumerate** — list the assets available at a source URI.
2. **Introspect** — extract one asset's logical schema in canonical types.
3. **Fetch** — return records for a registered asset with filters/pagination.

Everything else (manifests, cataloging, governance, artifact generation) is
connector-agnostic.

## Contract

A connector registers under a URI **scheme** (`sqlite`, `postgres`, `s3`).
`source.connector` in manifests/descriptors names the scheme that serves it.

```python
class Connector(ABC):
    scheme: ClassVar[str]

    def list_assets(self, uri: str) -> list[str]:
        """Native names of assets at `uri` (tables, prefixes, files)."""

    def introspect(self, uri: str, native_name: str) -> AssetSchema:
        """Extract the logical schema of one asset in canonical types."""

    def fetch(
        self,
        descriptor: AssetDescriptor,
        *,
        filters: Mapping[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FetchResult:  # (records: list[dict], total: int | None)
        """Return records for a registered asset."""
```

`discover` (drafting onboarding manifests) and `register` (verification +
descriptor production) are framework operations composed from these three
primitives — connectors never produce manifests or descriptors themselves.

## Requirements

- **Canonical types.** Native types map to the canonical set defined by the
  Asset Descriptor spec; unmappable types become `unknown`, never a
  passthrough of the native name.
- **Safe querying.** `fetch` MUST reject filters on fields not in the
  descriptor schema and MUST use parameterized queries — descriptor content is
  data, never SQL.
- **Policy-blind.** Connectors do not enforce `access` policy; serving layers
  do. Connectors enforce only physical correctness.
- **No credentials in URIs.** Secrets resolve at connect time from the
  environment/secret store, keyed by the URI.

## Registration

```python
from tabella_core.connectors import Connector, register

@register
class PostgresConnector(Connector):
    scheme = "postgres"
    ...
```

Third-party packages may expose connectors via the `tabella.connectors`
entry-point group; the CLI loads them automatically.
