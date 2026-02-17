---
name: retrieve-secrets
description: Read environment authentication information including credentials, connection strings, and tokens needed to access customer tenants and other resources. Use when another skill needs credentials to connect to a customer system.
allowed-tools: Bash(python:*)
---

# Retrieve Secrets

Retrieve authentication information for accessing customer environments and resources.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Access to the secrets store (configuration varies by deployment)

## Workflow

1. **Identify what's needed** — determine which customer/environment credentials are required.
2. **Retrieve credentials** — run the script to fetch the appropriate secrets.
3. **Pass to other skills** — use the retrieved credentials with other OpsKit skills.

## Usage

```bash
# List available secret scopes
python skills/retrieve-secrets/scripts/retrieve_secrets.py \
  --action list-scopes

# Get credentials for a specific environment
python skills/retrieve-secrets/scripts/retrieve_secrets.py \
  --action get \
  --scope "customer-abc" \
  --secret-name "dataverse-credentials"

# Get Azure DevOps PAT
python skills/retrieve-secrets/scripts/retrieve_secrets.py \
  --action get \
  --scope "customer-abc" \
  --secret-name "ado-pat"

# Get Jira credentials
python skills/retrieve-secrets/scripts/retrieve_secrets.py \
  --action get \
  --scope "global" \
  --secret-name "jira-credentials"
```

### Actions

| Action | Description |
|--------|-------------|
| `list-scopes` | List available secret scopes/customers |
| `get` | Retrieve a specific secret by scope and name |

## Security Guidelines

- **NEVER display full secrets** in output — always mask sensitive values (show only last 4 characters)
- **NEVER log secrets** to files or console output beyond what's needed
- **NEVER include secrets in commit messages, code, or files**
- Secrets should be passed directly to other scripts via environment variables or secure parameters
- Always confirm with the user before retrieving secrets
- Credentials are scoped per customer — do not mix credentials between customers
