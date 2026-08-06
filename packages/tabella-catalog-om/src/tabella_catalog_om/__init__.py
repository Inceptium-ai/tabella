"""tabella-catalog-om: OpenMetadata catalog backend (lands in M1).

Will implement `tabella_core.interfaces.CatalogBackend`: entity upsert, tag and
domain assignment, custom properties, contract publication, and ingest
pipeline triggering against the OpenMetadata API.
"""

from tabella_core.interfaces import CatalogBackend
from tabella_core.models import AssetDescriptor


class OpenMetadataCatalog(CatalogBackend):
    name = "openmetadata"

    def __init__(self, host: str | None = None):
        self.host = host

    def upsert_asset(self, descriptor: AssetDescriptor) -> None:
        raise NotImplementedError(
            "OpenMetadata backend lands in M1 (sandbox: deploy/sandbox)"
        )
