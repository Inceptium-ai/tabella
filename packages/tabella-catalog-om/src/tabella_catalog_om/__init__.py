"""tabella-catalog-om: OpenMetadata catalog backend.

Mirrors Asset Descriptors into OpenMetadata: entity hierarchy, tags, domain,
custom properties, and data contracts. Configure via TABELLA_OM_HOST and
TABELLA_OM_TOKEN. Built against vendored OM 1.12.x API schemas (reference/);
live-server validation lands with deploy/sandbox.
"""

from tabella_catalog_om.backend import IngestTimeout, OpenMetadataCatalog
from tabella_catalog_om.client import OpenMetadataClient, OpenMetadataError
from tabella_catalog_om.settings import OMSettings

__all__ = [
    "IngestTimeout",
    "OMSettings",
    "OpenMetadataCatalog",
    "OpenMetadataClient",
    "OpenMetadataError",
]
