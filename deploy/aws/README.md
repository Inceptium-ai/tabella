# AWS reference deployment (M3)

Terraform modules for running UDAP's pipeline in AWS:

- Registration pipeline on Lambda / Step Functions (onboarding form or API
  submits a spec-compliant JSON manifest → pipeline runs register)
- AWS Glue Data Catalog registration + Lake Formation permissions via the
  `udap-governance-aws` backend
- Connectivity to an OpenMetadata deployment

This mirrors the cloud-agnostic core: everything the stack produces conforms
to the open specs in `../../spec/`. Lands in M3.
