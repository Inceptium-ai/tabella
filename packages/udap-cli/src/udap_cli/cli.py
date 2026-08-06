"""The `udap` CLI: register, discover, validate, serve, tools.

M1 adds `init` (sandbox bootstrap); M2 adds `vectorize`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import udap_connectors  # noqa: F401  (registers built-in connectors)
from udap_core.manifest import dump_manifest_yaml, load_manifest
from udap_core.pipeline import discover, register
from udap_core.store import load_catalog


def _cmd_register(args: argparse.Namespace) -> int:
    for path in args.manifests:
        manifest = load_manifest(path)
        result = register(manifest, args.catalog)
        print(f"registered {result.descriptor.id} -> {result.descriptor_path}")
    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    drafts = discover(args.uri, domain=args.domain)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for manifest in drafts:
        path = out / f"{manifest.asset_id}.yaml"
        path.write_text(dump_manifest_yaml(manifest))
        print(f"drafted {path}")
    print(
        f"drafted {len(drafts)} manifest(s) -> {out} — review, edit domain/owner/"
        "classification, then `udap register <manifest>`"
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    print(f"OK: {len(catalog)} valid descriptor(s) in {args.catalog}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    from udap_enable.rest import build_app

    catalog = load_catalog(args.catalog)
    print(f"serving {len(catalog)} asset(s) on http://{args.host}:{args.port}")
    uvicorn.run(build_app(catalog), host=args.host, port=args.port)
    return 0


def _cmd_tools(args: argparse.Namespace) -> int:
    from udap_enable.tools import build_manifest

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
        prog="udap", description="UDAP — Unified Data Access Platform CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register", help="Register asset(s) from onboarding manifest(s)")
    p.add_argument("manifests", nargs="+", help="Manifest file(s), .yaml or .json")
    p.add_argument("-c", "--catalog", default="catalog", help="Catalog dir (default: catalog)")
    p.set_defaults(func=_cmd_register)

    p = sub.add_parser("discover", help="Draft onboarding manifests for assets found at a source")
    p.add_argument("uri", help="Source URI, e.g. sqlite:///path/to.db")
    p.add_argument("-o", "--output", default="manifests", help="Draft dir (default: manifests)")
    p.add_argument("--domain", default="unassigned", help="Domain to pre-fill in drafts")
    p.set_defaults(func=_cmd_discover)

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

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # surface as clean CLI errors, not tracebacks
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
