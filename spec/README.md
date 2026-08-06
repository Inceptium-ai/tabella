# The Tabella Standards

Tabella's value comes from a small set of stable contracts. Any tool that
produces or consumes these artifacts interoperates with any other — including
the commercial Tabella Platform, which is built on exactly these specs.

| # | Spec | Artifact |
|---|---|---|
| 1 | [Onboarding Manifest](onboarding-manifest.md) | `*.yaml` / `*.json` registration documents ([schema](schemas/onboarding-manifest.schema.json)) |
| 2 | [Asset Descriptor](asset-descriptor.md) | Cataloged asset records ([schema](schemas/asset-descriptor.schema.json)) |
| 3 | [Connector Interface](connector-interface.md) | Enumerate/introspect/fetch plugin contract |
| 4 | [Access Layer Contract](access-layer-contract.md) | Generated API conventions |
| 5 | [AI Artifact Manifests](ai-artifact-manifest.md) | `tools.json` (MCP-aligned) + `rag.json` |

## The flow

```
Onboarding Manifest ──register──► Asset Descriptor ──generate──► access APIs,
 (owner declares,                  (declared + introspected,      MCP tools,
  discovery drafts)                 cataloged + governed)         RAG indexes
```

## Design principles

- **Registration is manifest-driven.** The onboarding manifest is the single
  entry artifact — a human writes YAML, a portal submits JSON, discovery
  drafts it for review. Nothing enters the catalog around it.
- **Descriptors are the unit of portability.** Everything downstream — catalog
  entities, governance grants, APIs, tools, vector indexes — derives from the
  descriptor and is regenerable from it.
- **Governance is data, not code.** Classification, contract, and access
  policy live in the artifacts; backends (OpenMetadata, Glue/Lake Formation)
  enforce them.
- **AI is a first-class consumer.** Every asset must be as consumable by an
  agent (tools, semantic search) as by a developer (REST).

## Versioning

Specs are versioned together as `tabella_version` (currently `0.1.0`, semver).
Breaking changes bump the minor version pre-1.0 and the major version after.
