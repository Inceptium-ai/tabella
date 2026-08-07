"""tabella-governance-aws: AWS Glue governance backend.

Glue database = logical source name; Glue table = asset name — mirroring the
OpenMetadata hierarchy so Glue-ingested OM entities have deterministic FQNs.
Lake Formation grants land with the org principal-mapping work (M3/platform).
"""

from tabella_governance_aws.glue import GlueGovernance

# Back-compat alias for the original stub name.
AwsGovernance = GlueGovernance

__all__ = ["AwsGovernance", "GlueGovernance"]
