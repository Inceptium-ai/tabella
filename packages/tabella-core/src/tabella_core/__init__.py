"""tabella-core: models, connector SDK, backend interfaces, registration pipeline."""

from tabella_core.models import (
    TABELLA_SPEC_VERSION,
    AssetDescriptor,
    OnboardingManifest,
)

__version__ = "0.1.0"
__all__ = ["AssetDescriptor", "OnboardingManifest", "TABELLA_SPEC_VERSION", "__version__"]
