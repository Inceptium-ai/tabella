"""udap-catalog-om: OpenMetadata catalog backend (lands in M1).

Will implement `udap_core.interfaces.CatalogBackend`: entity upsert, tag and
domain assignment, custom properties, contract publication, and ingest
pipeline triggering against the OpenMetadata API.
"""

from udap_core.interfaces import CatalogBackend
from udap_core.models import AssetDescriptor


class OpenMetadataCatalog(CatalogBackend):
    name = "openmetadata"

    def __init__(self, host: str | None = None):
        self.host = host

    def upsert_asset(self, descriptor: AssetDescriptor) -> None:
        raise NotImplementedError(
            "OpenMetadata backend lands in M1 (sandbox: deploy/sandbox)"
        )
