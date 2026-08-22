# Tabella Roadmap — Framework Enhancements

Where the open framework goes next. The near-term milestones (AWS validation
batch, Terraform reference deployment, docs site) are tracked in the
[README](../README.md#roadmap); this document covers the **spec and framework
enhancements** planned beyond them, informed by production data-onboarding
experience. The open-core rule governs what lands here: *anything a single
engineer needs to make one asset flow is open.*

Feedback welcome — open an issue against any section.

---

## Spec v0.2 proposals

### 1. Asset groups — governance inheritance in the manifest

Today one manifest registers one asset, and governance metadata (tags,
classification, access policy, SLAs) repeats per manifest. In practice,
assets arrive in **groups that share governance**: the tables of one system,
the exports of one team, a batch of files with identical classification.

v0.2 proposes multi-asset manifests with a group level:

```yaml
asset_group:
  domain: sales
  owner: sales-data@example.com
  classification: internal
  tags: [crm]
  access: {read_roles: [sales]}
assets:
  - name: customers
    native_name: public.customers
    contract: ...
  - name: orders
    native_name: public.orders
```

Group-level values are defaults; per-asset values override. Registration
stays per-asset under the hood (one descriptor each), so the Asset Descriptor
spec is unchanged — this is manifest-level ergonomics plus a `group`
back-reference for lineage.

### 2. Stewardship & operational vocabulary

The descriptor's business metadata today is `owner`, `domain`, `tags`,
`classification`, and free-form `custom_properties`. Real governance
programs consistently need a richer, *structured* vocabulary:

| Proposed field | Meaning |
|---|---|
| `steward` | Person/team accountable for metadata quality (distinct from `owner`) |
| `publisher` | Entity that makes the asset available |
| `custodian` | Organizational element that maintains it |
| `consumers` | Known downstream applications/assets (app-level) |
| `stakeholders` | Org-level groups that rely on the asset |
| `access_instructions` | How a human actually gets access — feeds descriptions and contract terms |
| `alert_contacts` | Who to notify on incidents/drift |
| `volume_metrics` | Ingest volume / record counts / size at rest (structured) |

All optional; all mirrored to catalog backends (OpenMetadata custom
properties / Glue parameters) like existing metadata.

### 3. Contract SLA block

The contract spec currently covers field-level expectations. v0.2 adds an
`sla` section that flows into published Data Contracts:

```yaml
contract:
  fields: [...]
  sla:
    refresh_frequency: daily     # hourly | daily | weekly | ...
    retention: P7Y               # ISO-8601 duration
    availability: "99.5"
```

Mapped onto OpenMetadata Data Contract `sla` fields; `access_instructions`
(above) maps to the contract's terms-of-use. Field-level quality rules remain
a later increment.

### 4. Source location vs. access URI

For assets cataloged from snapshots or via gateways, *where the data really
lives* differs from *how Tabella reads it*. Proposal: optional
`source.location` (the authoritative system, documentation-only) alongside
`source.uri` (what connectors consume) — surfaced into the catalog's native
location fields.

---

## Connector roadmap

- **MySQL, Snowflake, BigQuery** — conventional additions to the existing
  three-method contract.
- **Schema-file connector** — catalog a live system (Cassandra,
  Elasticsearch, and similar) from a **schema snapshot file** in object
  storage when the live cluster isn't reachable from where Tabella runs
  (air-gapped or segmented networks). Introspection reads the snapshot;
  `source.location` documents the real system.
- **API assets** — treat REST/GraphQL endpoints as first-class assets
  (catalog hierarchy: service → collection → endpoint), extending the asset
  model beyond tables and files.

---

## Framework enhancements

- **Environment awareness** — a lightweight environment tag (`dev`/`prod`)
  threaded through catalog naming, so one manifest registers cleanly into
  multiple environments.
- **Metadata backfill primitive** — a fill-what's-missing, never-overwrite
  enrichment mode for assets that already exist in the catalog (today
  re-registration replaces; backfill respects manual edits made in the
  catalog UI).
- **Predicate pushdown for the files connector** — column/row filtering
  before load for CSV/Parquet.
- **Richer query filters** in the access-layer contract (ranges, `in`,
  full-text) beyond v0.1's equality filters.

---

## Explicit non-goals for the framework

These belong to the [commercial platform](https://github.com/Inceptium-ai/tabella#open-core)
per the open-core rule — listed so contributors know where the line is:
scheduled crawling and drift detection, approval workflows, async
registration orchestration with per-asset status tracking, the onboarding
portal UI, compliance/utilization dashboards, RBAC/SSO, and multi-tenancy.
