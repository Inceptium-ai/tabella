# Tabella Access Layer Contract — v0.1.0

Every access layer generated from a Tabella catalog follows the same conventions,
so a consumer (human or agent) that can use one Tabella API can use them all.
Only assets with `enablement.api: true` are served.

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /assets` | List asset summaries (`id`, `name`, `description`, `domain`, `classification`, `tags`) |
| `GET /assets/{id}` | Full Asset Descriptor |
| `GET /assets/{id}/records` | Query records |
| `POST /assets/{id}/search` | Semantic search (vectorized assets only, M2) |
| `GET /health` | Liveness |

## Querying records

`GET /assets/{id}/records` accepts:

- `limit` (default 100) and `offset` — `limit` is silently capped at the
  descriptor's `access.row_limit`.
- One query parameter per schema field for **equality filtering**, e.g.
  `?country=DE&active=true`. Values are coerced to the field's canonical type.
- Unknown filter fields → `400`.

Richer predicates (ranges, `in`, full-text) are planned for v0.2 via a
`filter` parameter; equality covers the generated-tool use case first.

## Response envelope

```json
{
  "data": [ { "id": 1, "country": "DE" } ],
  "pagination": { "limit": 100, "offset": 0, "total": 1234 },
  "asset": "sales.customers"
}
```

`total` MAY be `null` when counting is expensive.

## Errors

All errors use one shape:

```json
{ "error": { "code": "unknown_field", "message": "No field 'countr' in asset 'sales.customers'" } }
```

| HTTP | code |
|---|---|
| 404 | `asset_not_found` |
| 400 | `unknown_field`, `invalid_value` |
| 403 | `access_denied` |

## Governance hooks

The reference implementation serves descriptors as-is; enforcing
`access.read_roles` against a real identity provider, row-level policies,
audit logging, rate limiting, and utilization metrics are serving-layer
concerns (the commercial platform, or your own deployment) — but the contract
above is what any such deployment MUST preserve.
