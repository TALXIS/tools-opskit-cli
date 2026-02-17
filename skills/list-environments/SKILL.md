---
name: list-environments
description: List and display details of customer environments, tenants, and their configuration. Use when the user needs to find which environments exist for a customer, check environment URLs, or review tenant details.
allowed-tools: Bash(python:*)
---

# List Environments

Print environments, tenants, and their details for a particular customer.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Access to environment registry/configuration

## Workflow

1. **Identify the customer** — ask the user which customer they want to look up, or list all customers.
2. **Retrieve environment list** — query the environment registry.
3. **Present results** — display in a clear table with key details.

## Usage

```bash
# List all customers
python skills/list-environments/scripts/list_environments.py \
  --action list-customers

# List environments for a specific customer
python skills/list-environments/scripts/list_environments.py \
  --action list \
  --customer "customer-abc"

# Get details of a specific environment
python skills/list-environments/scripts/list_environments.py \
  --action details \
  --customer "customer-abc" \
  --environment "production"
```

### Actions

| Action | Description |
|--------|-------------|
| `list-customers` | List all available customers |
| `list` | List environments for a specific customer |
| `details` | Get detailed info for a specific environment |

### Output Includes

- Environment name and type (production, sandbox, development)
- Dataverse environment URL
- Tenant ID and domain
- Region / datacenter
- Last known status
