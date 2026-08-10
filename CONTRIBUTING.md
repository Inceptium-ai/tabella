# Contributing to Tabella

Thanks for your interest! Tabella is an open framework and set of standards
for onboarding, cataloging, governing, and AI-enabling enterprise data.

## Development setup

```bash
git clone https://github.com/Yazdan-Ahmed/tabella
cd tabella
uv sync                 # installs all workspace packages + dev tools
uv run pytest -q        # full suite runs offline — no databases or API keys
uv run ruff check .
```

The quickstart in [examples/quickstart](examples/quickstart/README.md) is the
fastest way to see the whole pipeline run.

## Repository shape

A `uv` workspace: the open **standards** live in [`spec/`](spec/) (versioned
together as `tabella_version`), and the framework is six packages under
`packages/` (core models + pipeline, connectors, OpenMetadata backend, AWS
governance backend, AI-enablement generators, CLI). Read
[spec/README.md](spec/README.md) first — every artifact derives from those
contracts.

## Guidelines

- **Spec changes travel together**: a change to a spec doc must update the
  matching JSON Schema, the pydantic models in `tabella-core`, and the tests
  that validate artifacts against the schemas.
- **Connectors** implement the three-method contract in
  [spec/connector-interface.md](spec/connector-interface.md): map native types
  to canonical ones, parameterize all queries, never put credentials in URIs.
- **Tests must run offline.** External systems (OpenMetadata, AWS, embedding
  APIs, Postgres) are tested against mocks/fakes in CI; live tests are gated
  behind env vars (e.g. `TABELLA_TEST_PG_URI`).
- Lint with `ruff` (config in the root `pyproject.toml`); CI runs
  `ruff check` and `pytest` on Python 3.11–3.13.

## Pull requests

Keep PRs focused; include tests for behavior changes; note any spec-version
implications in the description.
