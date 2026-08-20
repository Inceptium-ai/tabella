# Releasing Tabella

All six packages version and release **in lockstep** — one tag publishes them
all at the same version.

## Setup status: ✅ complete (v0.1.0, 2026-08-20)

All six projects exist on PyPI with **trusted publishing** configured
(GitHub OIDC — no stored tokens): each project's publisher is
`Inceptium-ai/tabella` · workflow `release.yml` · environment `pypi`, and the
`pypi` environment exists on the GitHub repo. Every release from here on is
fully automated by the tag push below.

<details>
<summary>How the first release was bootstrapped (for the record)</summary>

PyPI requires every **pending** publisher (for a not-yet-existing project) to
have a *unique* configuration, so six identical entries can't be
pre-registered from one monorepo. The first release was uploaded with a
one-time account-scoped API token (`uv build` per package + `uv publish`),
split across two days because PyPI rate-limits new-project creation
(~4/day observed). The token was revoked immediately after, and per-project
trusted publishers were added once the projects existed — identical configs
across *existing* projects are allowed.

</details>

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
   them to PyPI via trusted publishing. Verify at
   `https://pypi.org/project/tabella-cli/`.

## Verifying locally before tagging

```bash
uv run ruff check . && uv run pytest -q
rm -rf dist && for p in tabella-core tabella-connectors tabella-catalog-om \
  tabella-governance-aws tabella-enable tabella-cli; do uv build --package $p; done
```
