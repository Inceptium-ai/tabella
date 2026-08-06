"""Load Onboarding Manifests from YAML (human entry) or JSON (form/API entry)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from udap_core.models import OnboardingManifest


def load_manifest(path: str | Path) -> OnboardingManifest:
    path = Path(path)
    text = path.read_text()
    data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Manifest is not a mapping: {path}")
    return OnboardingManifest.model_validate(data)


def dump_manifest_yaml(manifest: OnboardingManifest) -> str:
    return yaml.safe_dump(manifest.to_json_dict(), sort_keys=False)
