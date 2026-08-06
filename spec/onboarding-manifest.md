# Tabella Onboarding Manifest — v0.1.0

The Onboarding Manifest is how an asset enters Tabella. It is the machine form of
the "data onboarding form": the asset's owner (or an automated discovery run)
declares what the asset is, where it lives, how it's classified and governed,
and which AI-enablement artifacts it should get.

- **YAML** is the human entry format (`tabella register onboarding.yaml`).
- **JSON** is the API/form format — an onboarding portal submits the exact
  same schema as JSON.
- `tabella discover <uri>` emits **draft manifests** for review; discovery never
  bypasses the manifest. Registration is always manifest-driven.

Normative schema: [`schemas/onboarding-manifest.schema.json`](schemas/onboarding-manifest.schema.json).

## Example

```yaml
tabella_version: 0.1.0
asset:
  name: customers
  description: Customer master records for the retail business
  owner: sales-data@example.com
  domain: sales
  tags: [crm, master-data]
  classification: internal
source:
  connector: postgres
  uri: postgres://analytics-db.internal:5432/retail
  native_name: public.customers
contract:
  fields:
    - name: id
      type: integer
      required: true
    - name: email
      type: string
      required: true
      pii: true
access:
  read_roles: ["sales", "analytics"]
  row_limit: 1000
enablement:
  api: true
  mcp: true
  vectorization:
    enabled: false
custom_properties:
  cost_center: "4211"
```

## Sections

### `asset` (required)

| Field | Req | Notes |
|---|---|---|
| `name` | ✓ | Asset name within its domain |
| `description` | | What the asset is; written for humans *and* AI agents |
| `owner` | | Owning team/person (email or handle) |
| `domain` | ✓ | Business domain (e.g. `sales`, `finance`) — drives the asset id `<domain>.<name>` and catalog domain assignment |
| `tags` | | Free-form catalog tags |
| `classification` | ✓ | `public` \| `internal` \| `confidential` \| `restricted` |

### `source` (required)

Physical binding: `connector` (registry scheme, e.g. `postgres`, `sqlite`,
`s3`), `uri`, `native_name` (table / object prefix / file path within the
source). Credentials MUST NOT appear in `uri`; connectors resolve secrets from
the environment or a secret store.

### `contract` (optional)

The owner's declared expectations of the asset — verified against the
introspected schema at registration time:

- `fields[]`: `name` (req), `type` (canonical type, see Asset Descriptor),
  `required` (bool → field must exist and be non-nullable), `pii` (bool —
  marks the field as PII in the catalog and excludes it from generated tool
  filters by default).

Registration **fails with a contract violation report** if a declared field is
missing or its type/nullability contradicts the source. Richer contract terms
(quality rules, freshness SLOs) are planned for v0.2.

### `access` (optional)

`read_roles` (default `["*"]`) and `row_limit` (default 1000) — enforced by
whatever serves the generated access layer.

### `enablement` (optional)

Which AI-enablement artifacts to produce:

- `api` (default `true`) — standardized REST access layer
- `mcp` (default `true`) — MCP tool exposure
- `vectorization` — RAG profile: `enabled`, `content_fields[]`, `chunking`
  (`semantic` \| `fixed` \| `document`), `chunk_size`, `embedding_model`

### `custom_properties` (optional)

String-keyed map propagated to the catalog backend as custom properties
(OpenMetadata custom attributes, Glue table parameters, …).

## Registration semantics

`tabella register <manifest>`:

1. Validate the manifest against the JSON Schema.
2. Introspect the source via the connector; verify the `contract`.
3. Produce/refresh the **Asset Descriptor** (id `<domain>.<name>`, slugged).
4. Upsert into the catalog backend (OpenMetadata: entity, tags, domain,
   custom properties, contract).
5. Apply the governance backend (e.g. AWS Glue registration + Lake Formation
   permissions).
6. Generate enablement artifacts per the `enablement` profile.

Re-registering the same `<domain>.<name>` is an **update**, never a duplicate.
