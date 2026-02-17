---
name: query-service-tickets
description: List and view customer incidents, changes, and service requests from Jira. Use when the user needs to check open tickets, review incident details, or look up service request status.
allowed-tools: Bash(python:*)
---

# Query Service Tickets

Look up customer incidents, change requests, and service requests from Jira Service Management. Uses only Python stdlib — no third-party dependencies.

## Setup

No pip dependencies — uses only Python standard library. Requires Python 3.10+.

Configure a Jira connection before first use:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection jira main
```

Or verify existing configuration:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py check jira
```

## Prerequisites

- Python 3.10+
- A Jira connection configured via `bootstrap.py add-connection jira <name>` (stores server URL, email, API token)
- Or environment variables: `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_API_TOKEN`

## Authentication

Credentials are resolved in this order:
1. **CLI flags**: `--server`, `--email`, `--api-token`
2. **Workspace config**: connection name in `ops/opskit.json` → `connections.json`
3. **Global default**: default connection in `config.json` → `connections.json`
4. **Environment variables**: `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_API_TOKEN`

## Workflow

1. **Identify the customer** — determine which customer's tickets to query. Use `list-organizations` to find their JSM organization.
2. **Search tickets** — use JQL queries to find relevant tickets, optionally filtered by organization.
3. **Get ticket details** — retrieve full issue details including description, labels, components, and attachment list.
4. **Read comments** — get the discussion thread on a ticket for troubleshooting context.
5. **Download attachments** — download files attached to tickets for analysis.

## Usage

```bash
# Search for open tickets (server/credentials from connection config)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action search \
  --jql "project = PROJ AND status != Done ORDER BY created DESC" \
  --max-results 20

# Get details of a specific ticket
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action get \
  --issue-key "PROJ-1234"

# Get comments on a ticket
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action get-comments \
  --issue-key "PROJ-1234"

# List all JSM organizations (customers)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action list-organizations

# List attachments on a ticket
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action list-attachments \
  --issue-key "PROJ-1234"

# Download an attachment to a specific directory
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action download-attachment \
  --attachment-id 12345 \
  --output-dir ./downloads

# Override connection with explicit server
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --server "https://other-instance.atlassian.net" \
  --action search \
  --jql "project = PROJ ORDER BY created DESC"

# Table output format
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-service-tickets/scripts/query_jira.py \
  --action search \
  --jql "project = PROJ AND status != Done" \
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

- Open incidents: `project = PROJ AND issuetype = Incident AND status != Done`
- Recent changes: `project = PROJ AND issuetype = "Change Request" AND created >= -7d`
- High priority: `project = PROJ AND priority in (Critical, High) AND status != Done`
- By organization: `project = PROJ AND organizations = "Customer Name"`
- Text search: `project = PROJ AND text ~ "error message"`

### Troubleshooting Workflow

When investigating a customer issue:

1. Find the organization: `--action list-organizations`
2. Search their tickets: `--action search --jql "project = PROJ AND organizations = \"Customer Name\" ORDER BY updated DESC"`
3. Get issue details: `--action get --issue-key PROJ-1234`
4. Read comments: `--action get-comments --issue-key PROJ-1234`
5. Download relevant attachments: `--action list-attachments --issue-key PROJ-1234`, then `--action download-attachment --attachment-id <id> --output-dir ./downloads`

## Important

- **Read-only** — never create, modify, or transition tickets
- Be mindful of large result sets — use `--max-results` to limit
- Server, email, and API token come from the connection config — override with CLI flags
- Manage connections with `bootstrap.py add-connection jira <name>`

## Reference

See [Jira API reference](references/jira-api.md) for API details.
