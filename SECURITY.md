# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Email
`yazdanmahmed@gmail.com` with details; you'll receive a response within a few
days. Coordinated disclosure is appreciated.

## Scope notes

- Tabella artifacts (manifests, descriptors, tool manifests) must never
  contain credentials — connectors resolve secrets from the environment or a
  secret store at run time. Reports of any code path that persists a secret
  into an artifact are treated as vulnerabilities.
- The reference access layer does not perform authentication; deployments are
  expected to enforce `access` policy at their serving boundary.
