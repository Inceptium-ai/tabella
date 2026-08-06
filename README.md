# UDAP — Unified Data Access Platform

**Open framework and standards for onboarding, cataloging, governing, and
AI-enabling enterprise data.**

> ⚠️ Working name. UDAP will be renamed before public launch.

Modern enterprises run hundreds of disconnected data sources, and every AI use
case stalls on the same questions: *what data exists, who owns it, can we use
it, and how do we access it?* UDAP is the automation layer that answers them.
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

Based on the whitepaper *Unified Data Access Platform: Automating Data
Discovery, Normalization, and AI-Ready Access Across the Enterprise*.

## How it works

Assets enter through the **Onboarding Manifest** — the machine form of a data
onboarding form. A human writes YAML, a portal submits the same schema as
JSON, or `udap discover` drafts manifests from a live source for review:

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

`udap register` then introspects the source, **verifies the contract** (a
declared-but-missing field fails registration with a violation report),
produces a portable **Asset Descriptor**, mirrors it into the catalog and
governance backends, and generates the enablement artifacts. Everything
downstream is derived and regenerable; PII markings flow into the catalog and
out of AI tool filters automatically.

## Quickstart

```bash
uv sync
uv run python examples/quickstart/make_demo_db.py
uv run udap register examples/quickstart/customers.yaml examples/quickstart/orders.yaml
uv run udap serve catalog/           # GET /assets/sales.customers/records?country=DE
uv run udap tools catalog/ -o tools.json   # MCP-aligned tool manifest
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
  udap-core/           Spec models, connector SDK, backend interfaces, registration pipeline
  udap-connectors/     Built-in connectors (sqlite; postgres + s3/files in M1)
  udap-catalog-om/     OpenMetadata catalog backend (M1)
  udap-governance-aws/ AWS Glue + Lake Formation governance backend (M3)
  udap-enable/         Generators: REST access layer, MCP tools (RAG + MCP server in M2)
  udap-cli/            The `udap` CLI
deploy/
  sandbox/             Local OpenMetadata + Postgres + MinIO stack (M1)
  aws/                 Terraform reference deployment (M3)
examples/quickstart/   End-to-end walkthrough
```

## Open core

| | This repo (Apache-2.0) | UDAP Platform (commercial) |
|---|---|---|
| **What** | The standards and the framework: manifests, descriptors, connectors, catalog/governance adapters, generators, CLI, reference deployment | The end-to-end automation & management plane |
| **Includes** | Everything above | Onboarding portal (form UI emitting spec-compliant JSON), scheduled crawling & approval workflows, governance/compliance dashboards, utilization & performance metrics, RBAC/SSO, multi-tenancy, managed infra |

Artifacts are portable by design — the platform produces and consumes exactly
the specs in this repo. No lock-in.

## Roadmap

- [x] **M0** — Specs v0.1, core models + registration pipeline with contract
  verification, sqlite connector, REST access layer, MCP tool manifest, CLI
- [ ] **M1** — OpenMetadata backend + sandbox stack, Postgres + S3/files
  connectors, `udap init`
- [ ] **M2** — RAG vectorization (chunking → embeddings → pgvector), live MCP
  server, semantic search endpoints, `udap vectorize`
- [ ] **M3** — AWS reference deployment: Terraform, Glue + Lake Formation
  governance backend
- [ ] **M4** — Docs site, public name, launch

## License

Apache-2.0. See [LICENSE](LICENSE).
