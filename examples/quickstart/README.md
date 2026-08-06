# Quickstart: onboard, serve, and AI-enable a database in two minutes

From the repository root:

```bash
uv sync

# 1. Create the demo database
uv run python examples/quickstart/make_demo_db.py

# 2. Register the assets from their onboarding manifests
uv run udap register examples/quickstart/customers.yaml examples/quickstart/orders.yaml
#    -> catalog/sales.customers.json, catalog/sales.orders.json

# (alternative entry point: draft manifests from the source, then review + register)
uv run udap discover sqlite:///examples/quickstart/retail.db --domain sales -o manifests/

# 3. Serve the generated access layer
uv run udap serve catalog/
#    GET http://127.0.0.1:8400/assets
#    GET http://127.0.0.1:8400/assets/sales.customers/records?country=DE&limit=10

# 4. Emit the AI tool manifest (MCP-aligned)
uv run udap tools catalog/ -o tools.json
```

Things to notice:

- `customers.yaml` declares a **contract**; break it (e.g. declare a field the
  table doesn't have) and registration fails with a violation report.
- `email` and `full_name` are marked **pii** in the contract — they are
  cataloged as PII and excluded from the generated tool's filters.
- Re-running `udap register` updates the same descriptors — registration is
  idempotent.
