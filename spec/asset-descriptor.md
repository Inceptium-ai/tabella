# UDAP Asset Descriptor — v0.1.0

The Asset Descriptor is the cataloged record of a registered asset: the merge
of what the owner declared (Onboarding Manifest) with what UDAP introspected
from the source (schema, types). Every downstream artifact — catalog entries,
governance grants, generated APIs, MCP tools, RAG indexes — is derived from
descriptors and is regenerable from them.

A catalog is a set of descriptors. The reference implementation stores them as
`<id>.json` files; catalog backends (OpenMetadata) mirror them as entities.

Normative schema: [`schemas/asset-descriptor.schema.json`](schemas/asset-descriptor.schema.json).

## Example

```json
{
  "udap_version": "0.1.0",
  "id": "sales.customers",
  "name": "customers",
  "description": "Customer master records for the retail business",
  "owner": "sales-data@example.com",
  "domain": "sales",
  "tags": ["crm", "master-data"],
  "classification": "internal",
  "source": {"connector": "postgres", "uri": "postgres://analytics-db.internal:5432/retail", "native_name": "public.customers"},
  "schema": {
    "fields": [
      {"name": "id", "type": "integer", "nullable": false},
      {"name": "email", "type": "string", "nullable": false, "pii": true},
      {"name": "country", "type": "string", "semantic_tags": ["iso-3166-alpha2"]}
    ],
    "primary_key": ["id"],
    "foreign_keys": []
  },
  "access": {"read_roles": ["sales", "analytics"], "row_limit": 1000},
  "enablement": {"api": true, "mcp": true, "vectorization": {"enabled": false}},
  "custom_properties": {"cost_center": "4211"},
  "lineage": []
}
```

## Fields

| Field | Type | Req | Notes |
|---|---|---|---|
| `udap_version` | string | ✓ | Spec version (semver) |
| `id` | string | ✓ | `<domain>.<name>` slugged, `[a-z0-9_.-]+`; stable across re-registration |
| `name` | string | ✓ | Asset name |
| `description` | string \| null | | AI-enriched when absent |
| `owner` | string \| null | | Owning team/person |
| `domain` | string | ✓ | Business domain |
| `tags` | string[] | | Catalog tags |
| `classification` | enum | ✓ | `public` \| `internal` \| `confidential` \| `restricted` |
| `source` | object | ✓ | `connector`, `uri`, `native_name` |
| `schema` | object | ✓ | Introspected logical schema (below) |
| `access` | object | | `read_roles`, `row_limit` |
| `enablement` | object | | `api`, `mcp`, `vectorization` profile |
| `custom_properties` | object | | String map, propagated to catalog backends |
| `lineage` | string[] | | Descriptor ids this asset derives from |

### `schema`

- `fields[]`: `name`, `type` (canonical: `string`, `integer`, `number`,
  `boolean`, `date`, `datetime`, `json`, `binary`, `unknown`), `nullable`,
  `description`, `semantic_tags[]`, `pii`.
- `primary_key`: field names.
- `foreign_keys[]`: `{fields, ref_asset, ref_fields}` — `ref_asset` is a
  descriptor id, keeping relationships portable across sources.

Canonical types abstract over source-native types; connectors own the mapping.
This is what makes generated APIs and tool schemas uniform across sources.

## Rules

1. Descriptors MUST validate against the JSON Schema.
2. `id` MUST be stable across re-registration — regeneration is an update.
3. Consumers MUST ignore unknown fields (forward compatibility).
4. Descriptors MUST NOT contain credentials.
5. `pii` marking flows outward: catalog backends receive it as a tag/label,
   and generators treat PII fields specially (excluded from tool filters by
   default).
