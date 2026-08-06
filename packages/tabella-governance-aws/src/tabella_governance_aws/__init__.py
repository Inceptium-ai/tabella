"""tabella-governance-aws: AWS governance backend (lands in M3).

Will implement `tabella_core.interfaces.GovernanceBackend`: Glue Data Catalog
registration and Lake Formation permission grants derived from descriptor
`classification` and `access` policy.
"""

from tabella_core.interfaces import GovernanceBackend
from tabella_core.models import AssetDescriptor


class AwsGovernance(GovernanceBackend):
    name = "aws"

    def apply(self, descriptor: AssetDescriptor) -> None:
        raise NotImplementedError(
            "AWS Glue/Lake Formation backend lands in M3 (deploy/aws)"
        )
