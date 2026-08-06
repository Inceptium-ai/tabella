"""Local catalog store: a directory of `<id>.json` Asset Descriptors.

This is the reference catalog — portable, diffable, no external dependency.
Catalog backends (OpenMetadata) mirror it; they never replace it.
"""

from __future__ import annotations

import json
from pathlib import Path

from tabella_core.models import AssetDescriptor


def save_descriptor(descriptor: AssetDescriptor, directory: str | Path) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{descriptor.id}.json"
    path.write_text(json.dumps(descriptor.to_json_dict(), indent=2) + "\n")
    return path


def load_catalog(directory: str | Path) -> list[AssetDescriptor]:
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Catalog directory not found: {directory}")
    return [
        AssetDescriptor.model_validate(json.loads(p.read_text()))
        for p in sorted(directory.glob("*.json"))
    ]
