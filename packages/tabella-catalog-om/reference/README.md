# OpenMetadata API reference (vendored)

Trimmed copy of the OpenMetadata JSON Schemas the Tabella backend builds
against — so the integration can be developed and reviewed without running an
OpenMetadata server (it is heavy: server + MySQL + Elasticsearch).

- **Source:** https://github.com/open-metadata/OpenMetadataStandards
- **Commit:** `7c1629b925e20928d6e50e7fe829a7e9c20dc918` (2026-04-23, tracks the OM 1.12.x line)
- Only the schemas used by `tabella-catalog-om` are vendored, unmodified.

## Endpoints used (all `createOrUpdate` via PUT unless noted)

| Call | Endpoint | Request schema |
|---|---|---|
| Ensure classification | `PUT /api/v1/classifications` | `createClassification.json` |
| Ensure tag | `PUT /api/v1/tags` | `createTag.json` |
| Ensure domain | `PUT /api/v1/domains` | `createDomain.json` |
| Ensure service | `PUT /api/v1/services/databaseServices` | `createDatabaseService.json` |
| Ensure database | `PUT /api/v1/databases` | `createDatabase.json` |
| Ensure schema | `PUT /api/v1/databaseSchemas` | `createDatabaseSchema.json` |
| Upsert table | `PUT /api/v1/tables` | `createTable.json` |
| Upsert contract | `PUT /api/v1/dataContracts` | `createDataContract.json` |

## Shapes that drive the mapping

- `createTable` requires `name`, `columns[]`, `databaseSchema` (FQN), and
  accepts `tags[]` (tagLabel: `{tagFQN}`), `domains[]` (FQNs), `extension`
  (custom properties object), `description`.
- `column` requires `name` + `dataType` (86-value enum incl. `STRING`, `INT`,
  `DOUBLE`, `BOOLEAN`, `DATE`, `DATETIME`, `JSON`, `BINARY`, `UNKNOWN`);
  per-column `tags[]` carry PII labels; `constraint` carries
  `PRIMARY_KEY` / `NOT_NULL` / `NULL`.
- `createDataContract` requires `name` + `entity` (an `entityReference`,
  which requires **`id` + `type`** — so the contract is created *after* the
  table upsert returns its id). Its `schema` is an array of `column`s: the
  declared contract fields go there verbatim.
- OM entity hierarchy is `service → database → schema → table`; each level's
  FQN is dot-joined and quoted per OM rules.

## Status

The backend is implemented against these schemas but has **not** run against
a live OpenMetadata server yet — request shapes are unit-tested with a mocked
HTTP transport. Live validation happens when the `deploy/sandbox` stack lands
(tracked in M1 follow-up).
