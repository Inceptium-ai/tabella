# Tabella

[![PyPI](https://img.shields.io/pypi/v/tabella-cli)](https://pypi.org/project/tabella-cli/)
[![CI](https://github.com/Inceptium-ai/tabella/actions/workflows/ci.yml/badge.svg)](https://github.com/Inceptium-ai/tabella/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tabella-core)](https://pypi.org/project/tabella-core/)

**Tabella makes enterprise data AI-ready.** Open framework and standards for
onboarding, cataloging, governing, and AI-enabling enterprise data.

*Tabella — from the Latin for a small tablet of records: the place where
scattered information becomes a trusted, usable register.*

Modern enterprises run hundreds of disconnected data sources, and every AI use
case stalls on the same questions: *what data exists, who owns it, can we use
it, and how do we access it?* Tabella is the automation layer that answers them.
An organization deploys the stack, sends out onboarding manifests (or forms),
and gets every asset **cataloged, tagged, domain-assigned, contract-verified,
governed — plus an AI enablement layer** (standardized APIs, MCP tools, RAG
indexes) generated automatically per asset.

```
Onboard ────► Catalog ─────► Govern ─────► Enable ─────► Serve ────► Observe
manifest      OpenMetadata   Glue/LF or    RAG indexes,  REST APIs,   metrics,
(YAML/JSON,   entities,      pluggable     MCP tools     MCP tools,   compliance,
or discovery  tags, domains, backends                    semantic     utilization
 drafts)      contracts                                  search       [platform]
```

Based on the whitepaper *Unified Data Access Platform (UDAP): Automating Data
Discovery, Normalization, and AI-Ready Access Across the Enterprise* —
Tabella is the productization of that architecture.

## How it works

Assets enter through the **Onboarding Manifest** — the machine form of a data
onboarding form. A human writes YAML, a portal submits the same schema as
JSON, or `tabella discover` drafts manifests from a live source for review:

```yaml
asset:
  name: customers
  domain: sales
  owner: sales-data@example.com
  classification: internal
source:
  connector: postgres
  uri: postgres://analytics-db.internal:5432/retail
  native_name: public.customers
contract:
  fields:
    - {name: id, type: integer, required: true}
    - {name: email, type: string, required: true, pii: true}
enablement:
  api: true
  mcp: true
```

`tabella register` then introspects the source, **verifies the contract** (a
declared-but-missing field fails registration with a violation report),
produces a portable **Asset Descriptor**, mirrors it into the catalog and
governance backends, and generates the enablement artifacts. Everything
downstream is derived and regenerable; PII markings flow into the catalog and
out of AI tool filters automatically.

## Install

```bash
pip install tabella-cli        # the CLI + the full framework
# or pick pieces: tabella-core, tabella-connectors, tabella-catalog-om,
#                 tabella-governance-aws, tabella-enable
```

Or work from source (below) for development.

## Quickstart

```bash
uv sync
uv run python examples/quickstart/make_demo_db.py
uv run tabella register examples/quickstart/customers.yaml examples/quickstart/orders.yaml
uv run tabella serve catalog/           # GET /assets/sales.customers/records?country=DE
uv run tabella tools catalog/ -o tools.json   # MCP-aligned tool manifest
```

See [examples/quickstart](examples/quickstart/README.md).

## The standards

Everything interoperates through five small specs in [`spec/`](spec/):

| Spec | Artifact |
|---|---|
| [Onboarding Manifest](spec/onboarding-manifest.md) | How assets are registered (YAML/JSON + JSON Schema) |
| [Asset Descriptor](spec/asset-descriptor.md) | The portable cataloged-asset record |
| [Connector Interface](spec/connector-interface.md) | Enumerate / introspect / fetch plugin contract |
| [Access Layer Contract](spec/access-layer-contract.md) | Conventions every generated API follows |
| [AI Artifact Manifests](spec/ai-artifact-manifest.md) | MCP tool manifest + RAG index manifest |

## Repository layout

```
spec/                  The open standards + JSON Schemas
packages/
  tabella-core/           Spec models, connector SDK, backend interfaces, registration pipeline
  tabella-connectors/     Built-in connectors: sqlite, postgres, files/s3 (csv + parquet), api (placeholders)
  tabella-catalog-om/     OpenMetadata catalog backend (M1)
  tabella-governance-aws/ AWS Glue + Lake Formation governance backend (M3)
  tabella-enable/         Generators: REST access layer, MCP tools (RAG + MCP server in M2)
  tabella-cli/            The `tabella` CLI
deploy/
  sandbox/             Local OpenMetadata + Postgres + MinIO stack (M1)
  aws/                 Terraform reference deployment (M3)
examples/quickstart/   End-to-end walkthrough
```

## Open core

| | This repo (Apache-2.0) | Tabella Platform (commercial) |
|---|---|---|
| **What** | The standards and the framework: manifests, descriptors, connectors, catalog/governance adapters, generators, CLI, reference deployment | The end-to-end automation & management plane |
| **Includes** | Everything above | Onboarding portal (form UI emitting spec-compliant JSON), scheduled crawling & approval workflows, governance/compliance dashboards, utilization & performance metrics, RBAC/SSO, multi-tenancy, managed infra |

Artifacts are portable by design — the platform produces and consumes exactly
the specs in this repo. No lock-in.

## Roadmap

- [x] **M0** — Specs v0.1, core models + registration pipeline with contract
  verification, sqlite connector, REST access layer, MCP tool manifest, CLI
- [x] **M1 (code)** — OpenMetadata backend (direct + Glue-ingest modes, built
  against vendored 1.12.x API schemas, mock-tested), Glue governance backend,
  Postgres connector, files/S3 connector (CSV + Parquet)
- [x] **M2 (code)** — RAG vectorization (`tabella vectorize`: chunking →
  embeddings → local/pgvector stores), semantic search endpoints, live MCP
  server (`tabella mcp`, stdio)
- [x] **v0.1.0 published** — all six packages on PyPI with automated,
  tokenless releases (tag-triggered trusted publishing)
- [x] **M3 (code)** — AWS reference deployment authored: Terraform stack
  (S3 manifest intake → containerized registrar Lambda → Glue/OM →
  descriptors back to S3), `tabella init` sandbox bootstrap (OpenMetadata +
  pgvector + MinIO compose)
- [ ] **Live validation batch** — one deploy window: `tofu apply` the
  reference stack + sandbox against real OpenMetadata, Glue, pgvector
  (deferred to minimize cloud cost)
- [ ] **M4** — Docs site, trademark + domain clearance for Tabella, launch

Beyond the milestones: spec v0.2 proposals (asset groups, stewardship &amp; SLA
vocabulary, contract SLA) and the connector roadmap live in
[docs/ROADMAP.md](docs/ROADMAP.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
