---
name: query-service-tickets
description: List and view customer incidents, changes, and service requests from Jira. Use when the user needs to check open tickets, review incident details, or look up service request status.
allowed-tools: Bash(python:*)
---

# Query Service Tickets

Look up customer incidents, change requests, and service requests from Jira Service Management. Uses only Python stdlib — no third-party dependencies.

## Setup

No dependencies to install — uses only Python standard library (`urllib`, `json`, `base64`, `webbrowser`).

Requires Python 3.10+.

## Prerequisites

- Python 3.10+
- An Atlassian account with access to the target Jira instance
- An API token (the script will guide you through creating one on first run)

## Authentication

On first run, the script:
1. Opens `https://id.atlassian.com/manage-profile/security/api-tokens` in your browser
2. Prompts for your Atlassian email and API token
3. Caches credentials locally at `skills/query-service-tickets/.credentials.json`

Subsequent runs use cached credentials silently. Use `--clear-credentials` to reset.

## Workflow

1. **Identify the customer** — determine which customer's tickets to query. Use `list-organizations` to find their JSM organization.
2. **Search tickets** — use JQL queries to find relevant tickets, optionally filtered by organization.
3. **Get ticket details** — retrieve full issue details including description, labels, components, and attachment list.
4. **Read comments** — get the discussion thread on a ticket for troubleshooting context.
5. **Download attachments** — download files attached to tickets for analysis.

## Usage

```bash
# Search for open tickets in CASE project (default server: networg.atlassian.net)
python skills/query-service-tickets/scripts/query_jira.py \
  --action search \
  --jql "project = CASE AND status != Done ORDER BY created DESC" \
  --max-results 20

# Get details of a specific ticket
python skills/query-service-tickets/scripts/query_jira.py \
  --action get \
  --issue-key "CASE-1234"

# Get comments on a ticket
python skills/query-service-tickets/scripts/query_jira.py \
  --action get-comments \
  --issue-key "CASE-1234"

# List all JSM organizations (customers)
python skills/query-service-tickets/scripts/query_jira.py \
  --action list-organizations

# List attachments on a ticket
python skills/query-service-tickets/scripts/query_jira.py \
  --action list-attachments \
  --issue-key "CASE-1234"

# Download an attachment to a specific directory
python skills/query-service-tickets/scripts/query_jira.py \
  --action download-attachment \
  --attachment-id 12345 \
  --output-dir ./downloads

# Use a different Jira instance
python skills/query-service-tickets/scripts/query_jira.py \
  --server "https://other-instance.atlassian.net" \
  --action search \
  --jql "project = PROJ ORDER BY created DESC"

# Table output format
python skills/query-service-tickets/scripts/query_jira.py \
  --action search \
  --jql "project = CASE AND status != Done" \
  --format table
```

### Actions

| Action | Description | Required Args |
|--------|-------------|---------------|
| `search` | Search tickets using JQL | `--jql` |
| `get` | Get full details of a specific ticket | `--issue-key` |
| `get-comments` | Get comments/discussion on a ticket | `--issue-key` |
| `list-organizations` | List JSM organizations (customers) | — |
| `list-attachments` | List attachments on a ticket | `--issue-key` |
| `download-attachment` | Download an attachment by ID | `--attachment-id`, `--output-dir` |

### Common JQL Patterns

- Open incidents: `project = CASE AND issuetype = Incident AND status != Done`
- Recent changes: `project = CASE AND issuetype = "Change Request" AND created >= -7d`
- High priority: `project = CASE AND priority in (Critical, High) AND status != Done`
- By organization: `project = CASE AND organizations = "Customer Name"`
- Text search: `project = CASE AND text ~ "error message"`

### Troubleshooting Workflow

When investigating a customer issue:

1. Find the organization: `--action list-organizations`
2. Search their tickets: `--action search --jql "project = CASE AND organizations = \"Customer Name\" ORDER BY updated DESC"`
3. Get issue details: `--action get --issue-key CASE-1234`
4. Read comments: `--action get-comments --issue-key CASE-1234`
5. Download relevant attachments: `--action list-attachments --issue-key CASE-1234`, then `--action download-attachment --attachment-id <id> --output-dir ./downloads`

## Important

- **Read-only** — never create, modify, or transition tickets
- Be mindful of large result sets — use `--max-results` to limit
- Default server is `https://networg.atlassian.net` — override with `--server`
- Credentials are stored in the skill folder and removed when the plugin is uninstalled

## Reference

See [Jira API reference](references/jira-api.md) for API details.
