# Releasing Tabella

All six packages version and release **in lockstep** — one tag publishes them
all at the same version.

## One-time setup (PyPI trusted publishing)

No API tokens are stored anywhere; the release workflow authenticates to PyPI
via GitHub OIDC. Before the first release:

1. On [pypi.org](https://pypi.org) → your account → **Publishing** → *Add a
   new pending publisher*, create one entry **per package name**:
   `tabella-core`, `tabella-connectors`, `tabella-catalog-om`,
   `tabella-governance-aws`, `tabella-enable`, `tabella-cli` — each with:
   - Owner: `Yazdan-Ahmed`  ·  Repository: `tabella`
   - Workflow name: `release.yml`  ·  Environment: `pypi`
2. On GitHub → repo → Settings → Environments, create an environment named
   `pypi` (optionally with required reviewers as a release gate).

Note: the bare name `tabella` on PyPI belongs to an unrelated project (an
Open-RPC docs tool). Our install entry point is `pip install tabella-cli`;
the console command is still `tabella`.

## Cutting a release

1. Bump `version` in all six `packages/*/pyproject.toml` (same value) and in
   the two `__init__.py` `__version__` strings; update `CHANGELOG.md`.
2. Commit, then tag and push:

   ```bash
   git tag v0.1.0
   git push origin main --tags
   ```

3. The `Release` workflow lints, tests, builds all six packages, and publishes
   them to PyPI. Verify at `https://pypi.org/project/tabella-cli/`.

## Verifying locally before tagging

```bash
uv run ruff check . && uv run pytest -q
rm -rf dist && for p in tabella-core tabella-connectors tabella-catalog-om \
  tabella-governance-aws tabella-enable tabella-cli; do uv build --package $p; done
```
