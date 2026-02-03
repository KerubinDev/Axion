# Security Policy

## Supported Versions

The following versions of AkitaLLM are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

We take the security of AkitaLLM seriously. If you believe you have found a security vulnerability, please report it to us by following these steps:

1. **Do not** open a public GitHub Issue.
2. Send an email to **kelvin.moraes117@gmail.com** with the details of the vulnerability.
3. Include as much information as possible, including steps to reproduce and potential impact.

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Security Philosophy

- **Local-First**: AkitaLLM is designed to keep your code on your machine. We avoid sending sensitive data to external servers unless explicitly configured by the user (i.e., when using remote LLM providers).
- **Transparency**: All reasoning pipelines and command executions are auditable and require human confirmation for destructive actions.
- **Trusted Dependencies**: We minimize external dependencies and use Trusted Publishing for our releases to ensure supply chain security.
