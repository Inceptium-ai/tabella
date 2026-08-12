# Releasing Tabella

All six packages version and release **in lockstep** — one tag publishes them
all at the same version.

## One-time setup

Steady state is trusted publishing (GitHub OIDC, no stored tokens) — but PyPI
requires every **pending** publisher (for a project that doesn't exist yet) to
have a *unique* configuration, so six identical repo/workflow/environment
entries can't be pre-registered from one monorepo. The first release is
therefore **bootstrapped with a one-time API token**, after which all six
projects exist and identical trusted publishers are allowed.

1. Remove any pending publishers left over from earlier attempts
   (pypi.org → account → Publishing).
2. Create an API token (pypi.org → Account settings → API tokens → scope
   *Entire account*; 2FA required).
3. Build and upload the first release locally:

   ```bash
   uv run ruff check . && uv run pytest -q
   rm -rf dist && for p in tabella-core tabella-connectors tabella-catalog-om \
     tabella-governance-aws tabella-enable tabella-cli; do uv build --package $p; done
   uv publish --token pypi-XXXX...           # uploads everything in dist/
   ```

4. **Revoke the token immediately**, then wire up trusted publishing for
   every future release: on each of the six project pages → Settings →
   Publishing → *Add a new publisher* (GitHub):
   - Owner: `Inceptium-ai`  ·  Repository: `tabella`
   - Workflow name: `release.yml`  ·  Environment: `pypi`

   (Identical configs across *existing* projects are fine — the uniqueness
   rule applies only to pending publishers.)
5. On GitHub → repo → Settings → Environments, create an environment named
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
