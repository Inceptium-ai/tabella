"""udap-core: models, connector SDK, backend interfaces, registration pipeline."""

from udap_core.models import (
    UDAP_SPEC_VERSION,
    AssetDescriptor,
    OnboardingManifest,
)

__version__ = "0.1.0"
__all__ = ["AssetDescriptor", "OnboardingManifest", "UDAP_SPEC_VERSION", "__version__"]
