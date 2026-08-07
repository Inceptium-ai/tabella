"""OpenMetadata backend settings — the FQN standard and the provisioning mode.

The hierarchy standard (identical with or without Glue in the loop):

    {service}.{database}.{source.name}.{asset name}
    e.g.  tabella.default.finapp.users

- `direct` mode: Tabella creates the technical entities itself, then enriches.
- `ingest` mode: the entity is produced by an OM ingestion pipeline (typically
  from Glue). If `pipeline_fqn` is set Tabella triggers it; either way Tabella
  polls for the table FQN, then enriches. Enrichment is the same code path in
  both modes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class OMSettings:
    mode: str = field(default_factory=lambda: _env("TABELLA_OM_MODE", "direct"))
    service: str = field(default_factory=lambda: _env("TABELLA_OM_SERVICE", "tabella"))
    database: str = field(default_factory=lambda: _env("TABELLA_OM_DATABASE", "default"))
    pipeline_fqn: str | None = field(
        default_factory=lambda: os.environ.get("TABELLA_OM_PIPELINE") or None
    )
    poll_timeout: float = field(
        default_factory=lambda: float(_env("TABELLA_OM_POLL_TIMEOUT", "300"))
    )
    poll_interval: float = field(
        default_factory=lambda: float(_env("TABELLA_OM_POLL_INTERVAL", "5"))
    )

    def __post_init__(self) -> None:
        if self.mode not in ("direct", "ingest"):
            raise ValueError(f"TABELLA_OM_MODE must be 'direct' or 'ingest', got {self.mode!r}")
