# OpenMetadata API reference (vendored)

Trimmed copy of the OpenMetadata JSON Schemas the Tabella backend builds
against — so the integration can be developed and reviewed without running an
OpenMetadata server (it is heavy: server + MySQL + Elasticsearch).

- **Source:** https://github.com/open-metadata/OpenMetadataStandards
- **Commit:** `7c1629b925e20928d6e50e7fe829a7e9c20dc918` (2026-04-23, tracks the OM 1.12.x line)
- Only the schemas used by `tabella-catalog-om` are vendored, unmodified.

## Endpoints used

Hierarchy standard (identical with or without Glue):
`{service}.{database}.{source.name}.{asset name}` — the logical source is the
OM database schema, matching OM's own Glue-connector semantics.

**Provisioning — `direct` mode** (`createOrUpdate` PUTs):

| Call | Endpoint | Request schema |
|---|---|---|
| Ensure service | `PUT /api/v1/services/databaseServices` | `createDatabaseService.json` |
| Ensure database | `PUT /api/v1/databases` | `createDatabase.json` |
| Ensure schema (= source) | `PUT /api/v1/databaseSchemas` | `createDatabaseSchema.json` |
| Create table (technical only) | `PUT /api/v1/tables` | `createTable.json` |

**Provisioning — `ingest` mode** (entity produced by an OM ingestion pipeline,
typically from Glue):

| Call | Endpoint |
|---|---|
| Resolve pipeline (optional) | `GET /api/v1/services/ingestionPipelines/name/{fqn}` |
| Trigger pipeline (optional) | `POST /api/v1/services/ingestionPipelines/trigger/{id}` |
| Poll for entity | `GET /api/v1/tables/name/{fqn}` (404 until ingested) |

**Enrichment — every mode** (business metadata layered on the entity):

| Call | Endpoint |
|---|---|
| Ensure classification/tags | `PUT /api/v1/classifications`, `PUT /api/v1/tags` |
| Ensure domain (need its id) | `PUT /api/v1/domains` |
| Enrich table | `PATCH /api/v1/tables/{id}` (`application/json-patch+json`: tags, domains, description, extension, per-column PII tags) |
| Upsert contract | `PUT /api/v1/dataContracts` (`entity` ref needs the table id) |

**Vocabulary registration** (governance registry → OM; properties must exist
on the entity type before `extension` patches may carry them):

| Call | Endpoint |
|---|---|
| Ensure classification/tags | `PUT /api/v1/classifications`, `PUT /api/v1/tags` |
| Resolve entity type id | `GET /api/v1/metadata/types/name/{entityType}?category=entityType` |
| Resolve field type id | `GET /api/v1/metadata/types/name/{string\|enum}?category=field` |
| Register custom property | `PUT /api/v1/metadata/types/{entityTypeId}` (createCustomProperty: `name`, `propertyType` ref; `customPropertyConfig.config.values` for enum) |

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
(tracked in M1 follow-up). Items only a live server can confirm: databaseService
serviceType enum values, custom-property type definitions required before
`extension` PATCHes are accepted, the exact ingestionPipelines trigger route,
JSON Patch validation details (tagLabel required fields), and the
custom-property registration route/payload (`metadata/types` ids + enum
`customPropertyConfig` shape).
