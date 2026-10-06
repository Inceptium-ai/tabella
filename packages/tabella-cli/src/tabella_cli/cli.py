"""The `tabella` CLI: init, register, discover, validate, serve, tools, vectorize, mcp."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tabella_connectors  # noqa: F401  (registers built-in connectors)
from tabella_core.manifest import dump_manifest_yaml, load_manifest
from tabella_core.pipeline import discover, register
from tabella_core.store import load_catalog


def _catalog_backends(names: list[str]):
    backends = []
    for name in names:
        if name == "openmetadata":
            from tabella_catalog_om import OpenMetadataCatalog

            backends.append(OpenMetadataCatalog())
        else:
            raise ValueError(f"Unknown catalog backend: {name}")
    return backends


def _governance_backends(names: list[str]):
    backends = []
    for name in names:
        if name == "aws":
            from tabella_governance_aws import GlueGovernance

            backends.append(GlueGovernance())
        else:
            raise ValueError(f"Unknown governance backend: {name}")
    return backends


def _cmd_register(args: argparse.Namespace) -> int:
    backends = _catalog_backends(args.backend or [])
    governance = _governance_backends(args.governance or [])
    for path in args.manifests:
        manifest = load_manifest(path)
        result = register(
            manifest, args.catalog, catalog_backends=backends, governance_backends=governance
        )
        extras = [*result.governance_backends, *result.catalog_backends]
        mirrored = f" (applied: {', '.join(extras)})" if extras else ""
        print(f"registered {result.descriptor.id} -> {result.descriptor_path}{mirrored}")
    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    drafts = discover(args.uri, domain=args.domain, source_name=args.source_name)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for manifest in drafts:
        path = out / f"{manifest.asset_id}.yaml"
        path.write_text(dump_manifest_yaml(manifest))
        print(f"drafted {path}")
    print(
        f"drafted {len(drafts)} manifest(s) -> {out} — review, edit domain/owner/"
        "classification, then `tabella register <manifest>`"
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    print(f"OK: {len(catalog)} valid descriptor(s) in {args.catalog}")
    return 0


def _cmd_classify(args: argparse.Namespace) -> int:
    from tabella_core.classify import apply_suggestions, classify_asset
    from tabella_core.store import save_descriptor

    catalog = load_catalog(args.catalog)
    if args.asset:
        catalog = [d for d in catalog if d.id == args.asset]
        if not catalog:
            print(f"error: no asset '{args.asset}' in {args.catalog}", file=sys.stderr)
            return 1

    changed = 0
    for descriptor in catalog:
        result = classify_asset(
            descriptor, sample_size=args.sample_size, sample_content=not args.names_only
        )
        if not result.fields and result.suggested_classification is None:
            continue
        print(f"{descriptor.id} (sampled {result.sampled_rows} row(s)):")
        for suggestion in result.fields:
            flags = []
            if suggestion.pii:
                flags.append("PII")
            sources = sorted({e["source"] for e in suggestion.evidence})
            print(
                f"  {suggestion.field}: {', '.join(suggestion.tags)}"
                f" [{' '.join(flags) or 'tag only'}; via {'/'.join(sources)}]"
            )
        if result.suggested_classification is not None:
            print(
                f"  classification: {descriptor.classification.value}"
                f" -> {result.suggested_classification.value}"
            )
        if args.apply:
            apply_suggestions(descriptor, result)
            save_descriptor(descriptor, args.catalog)
            changed += 1
    if args.apply:
        print(f"applied suggestions to {changed} descriptor(s)")
    else:
        print("(suggestions only — re-run with --apply to write them)")
    return 0


def _search_service():
    from tabella_enable.rag import (
        SearchService,
        embedding_provider_from_env,
        vector_store_from_env,
    )

    return SearchService(embedding_provider_from_env(), vector_store_from_env())


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    from tabella_enable.rest import build_app

    catalog = load_catalog(args.catalog)
    print(f"serving {len(catalog)} asset(s) on http://{args.host}:{args.port}")
    uvicorn.run(build_app(catalog, search=_search_service()), host=args.host, port=args.port)
    return 0


def _cmd_vectorize(args: argparse.Namespace) -> int:
    from tabella_enable.rag import embedding_provider_from_env, vector_store_from_env
    from tabella_enable.rag.pipeline import build_rag_manifest, vectorize_asset

    catalog = load_catalog(args.catalog)
    embedder = embedding_provider_from_env()
    store = vector_store_from_env()
    targets = [d for d in catalog if d.enablement.vectorization.enabled]
    if args.assets:
        targets = [d for d in targets if d.id in set(args.assets)]
    if not targets:
        print("no vectorization-enabled assets matched", file=sys.stderr)
        return 1
    entries = []
    for descriptor in targets:
        entry = vectorize_asset(descriptor, embedder, store)
        entries.append(entry)
        print(
            f"vectorized {descriptor.id}: {entry['chunk_count']} chunk(s) -> "
            f"{entry['store']['backend']}:{entry['store']['collection']}"
        )
    text = json.dumps(build_rag_manifest(entries), indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from tabella_cli.sandbox import init_sandbox

    return init_sandbox(args.directory, start=not args.no_start)


def _cmd_mcp(args: argparse.Namespace) -> int:
    import asyncio

    from tabella_enable.mcp_server import run_stdio

    catalog = load_catalog(args.catalog)
    search = None if args.no_search else _search_service()
    asyncio.run(run_stdio(catalog, search=search))
    return 0


def _cmd_tools(args: argparse.Namespace) -> int:
    from tabella_enable.tools import build_manifest

    manifest = build_manifest(
        load_catalog(args.catalog), include_restricted=args.include_restricted
    )
    text = json.dumps(manifest, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output} ({len(manifest['tools'])} tool(s))")
    else:
        print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tabella", description="Tabella — Unified Data Access Platform CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register", help="Register asset(s) from onboarding manifest(s)")
    p.add_argument("manifests", nargs="+", help="Manifest file(s), .yaml or .json")
    p.add_argument("-c", "--catalog", default="catalog", help="Catalog dir (default: catalog)")
    p.add_argument(
        "--backend",
        action="append",
        choices=["openmetadata"],
        help="Also mirror into a catalog backend (repeatable). openmetadata reads"
        " TABELLA_OM_HOST / TABELLA_OM_TOKEN / TABELLA_OM_MODE (direct|ingest)"
        " / TABELLA_OM_SERVICE / TABELLA_OM_DATABASE / TABELLA_OM_PIPELINE",
    )
    p.add_argument(
        "--governance",
        action="append",
        choices=["aws"],
        help="Also apply a governance backend (repeatable; runs before catalog"
        " backends). aws = Glue registration, credentials from the AWS environment",
    )
    p.set_defaults(func=_cmd_register)

    p = sub.add_parser("discover", help="Draft onboarding manifests for assets found at a source")
    p.add_argument("uri", help="Source URI, e.g. sqlite:///path/to.db")
    p.add_argument("-o", "--output", default="manifests", help="Draft dir (default: manifests)")
    p.add_argument("--domain", default="unassigned", help="Domain to pre-fill in drafts")
    p.add_argument(
        "--source-name",
        help="Logical source name for the drafts (default: derived from the URI)",
    )
    p.set_defaults(func=_cmd_discover)

    p = sub.add_parser(
        "classify",
        help="Suggest PII flags / semantic tags / classification from field names "
        "and sampled content (install presidio-analyzer for NER-grade detection)",
    )
    p.add_argument("catalog", help="Catalog directory")
    p.add_argument("--asset", help="Classify one asset id only")
    p.add_argument("--sample-size", type=int, default=50)
    p.add_argument("--names-only", action="store_true", help="Skip content sampling")
    p.add_argument("--apply", action="store_true", help="Write suggestions to descriptors")
    p.set_defaults(func=_cmd_classify)

    p = sub.add_parser("validate", help="Validate every descriptor in a catalog")
    p.add_argument("catalog", help="Catalog directory")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("serve", help="Serve the generated access layer for a catalog")
    p.add_argument("catalog", help="Catalog directory")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8400)
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("tools", help="Emit the AI tool manifest (MCP-aligned) for a catalog")
    p.add_argument("catalog", help="Catalog directory")
    p.add_argument("-o", "--output", help="Write manifest to file instead of stdout")
    p.add_argument("--include-restricted", action="store_true")
    p.set_defaults(func=_cmd_tools)

    p = sub.add_parser(
        "vectorize",
        help="Chunk, embed, and index vectorization-enabled assets; emit rag.json."
        " Env: TABELLA_EMBED_* (hash|openai), TABELLA_VECTOR_* (local|pgvector)",
    )
    p.add_argument("catalog", help="Catalog directory")
    p.add_argument("assets", nargs="*", help="Asset ids to vectorize (default: all enabled)")
    p.add_argument("-o", "--output", help="Write the RAG index manifest to a file")
    p.set_defaults(func=_cmd_vectorize)

    p = sub.add_parser(
        "init",
        help="Bootstrap the local sandbox (OpenMetadata + pgvector Postgres + MinIO)",
    )
    p.add_argument("directory", nargs="?", default="tabella-sandbox", help="Target directory")
    p.add_argument(
        "--no-start", action="store_true", help="Write the compose files without starting"
    )
    p.set_defaults(func=_cmd_init)

    p = sub.add_parser("mcp", help="Serve the catalog as a live MCP server (stdio)")
    p.add_argument("catalog", help="Catalog directory")
    p.add_argument("--no-search", action="store_true", help="Disable semantic search tools")
    p.set_defaults(func=_cmd_mcp)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # surface as clean CLI errors, not tracebacks
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
