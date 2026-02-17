---
name: list-deployments
description: List recent deployments and their status for a customer environment. Use when the user needs to check what was deployed recently, verify deployment success, or investigate deployment failures.
allowed-tools: Bash(python:*)
---

# List Deployments

View recent deployments and their status for customer environments.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Access to deployment tracking system / Azure DevOps pipelines

## Workflow

1. **Identify the customer and environment** — ask the user which customer/environment to check.
2. **Retrieve deployment history** — query the deployment tracking system.
3. **Present results** — show deployments with status, timestamps, and key details.

## Usage

```bash
# List recent deployments for a customer
python skills/list-deployments/scripts/list_deployments.py \
  --action list \
  --customer "customer-abc" \
  --top 10

# List deployments for a specific environment
python skills/list-deployments/scripts/list_deployments.py \
  --action list \
  --customer "customer-abc" \
  --environment "production" \
  --top 10

# Get details of a specific deployment
python skills/list-deployments/scripts/list_deployments.py \
  --action details \
  --deployment-id "12345"

# List only failed deployments
python skills/list-deployments/scripts/list_deployments.py \
  --action list \
  --customer "customer-abc" \
  --status failed
```

### Actions

| Action | Description |
|--------|-------------|
| `list` | List recent deployments with optional filters |
| `details` | Get detailed info for a specific deployment |

### Output Includes

- Deployment ID and timestamp
- Target environment
- Status (succeeded, failed, in-progress, cancelled)
- Deployed solutions/components
- Triggered by (user or pipeline)
- Duration
- Error details (for failed deployments)
