# AWS reference deployment

Terraform for running Tabella's registration pipeline in AWS, mirroring the
production onboarding pattern: a form or API drops a **spec-compliant
onboarding manifest** (JSON or YAML) into S3 → the **registrar Lambda**
validates it, verifies the contract, registers the asset in **Glue**
(governance) and optionally **OpenMetadata** (catalog), and writes the
resulting Asset Descriptor back to the bucket.

```
POST/console/pipeline → s3://<intake>/manifests/x.yaml
                             │  S3 ObjectCreated
                             ▼
                   registrar Lambda (tabella_cli.lambda_handler)
                    ├─ contract verification (fail → Lambda error/DLQ)
                    ├─ Glue database + table        (enable_glue)
                    ├─ OpenMetadata direct/ingest   (enable_openmetadata)
                    └─ s3://<intake>/catalog/<asset-id>.json
```

Works with **Terraform ≥ 1.5 or OpenTofu ≥ 1.6** (CI validates with OpenTofu).

> Status: authored offline; first live `apply` happens in the consolidated
> AWS validation window along with OM/Glue/pgvector verification.

## Deploy

```bash
# 1. Build and push the registrar image (from the repo root)
aws ecr create-repository --repository-name tabella-registrar
docker build -f deploy/aws/lambda.Dockerfile -t tabella-registrar .
docker tag tabella-registrar:latest <acct>.dkr.ecr.<region>.amazonaws.com/tabella-registrar:0.1.0
aws ecr get-login-password | docker login --username AWS --password-stdin <acct>.dkr.ecr.<region>.amazonaws.com
docker push <acct>.dkr.ecr.<region>.amazonaws.com/tabella-registrar:0.1.0

# 2. Apply
cd deploy/aws
tofu init
tofu apply \
  -var lambda_image_uri=<acct>.dkr.ecr.<region>.amazonaws.com/tabella-registrar:0.1.0 \
  -var enable_glue=true
```

OpenMetadata mirroring (optional): store the OM bot JWT in Secrets Manager,
then add:

```bash
  -var enable_openmetadata=true \
  -var om_host=http://<om-endpoint>:8585 \
  -var om_mode=ingest \
  -var om_token_secret_arn=arn:aws:secretsmanager:...:secret:tabella/om-token
```

If OM or your sources are only reachable inside a VPC, set `vpc_subnet_ids`
and `vpc_security_group_ids`.

## Use

```bash
aws s3 cp examples/quickstart/customers.yaml \
  s3://$(tofu output -raw intake_bucket)/manifests/customers.yaml

# watch it register
aws logs tail /aws/lambda/tabella-registrar --follow

# the generated descriptor
aws s3 ls s3://$(tofu output -raw intake_bucket)/catalog/
```

A failed registration (contract violation, unreachable source) raises, so
standard Lambda retry/DLQ semantics apply — wire the function's on-failure
destination to a queue if you want dead-lettering.

## Notes & boundaries

- **Glue IAM is account-scoped** in this reference (`resources = ["*"]` on
  the five Glue actions) — scope to specific database ARNs for production.
- **Lake Formation grants** are intentionally out of scope (org-specific
  principal mapping — see the platform roadmap).
- The **submission API/portal** (auth, drafts, status tracking) is commercial
  platform scope; this stack is the open, single-engineer path: anything that
  can put an object in S3 can onboard data.
