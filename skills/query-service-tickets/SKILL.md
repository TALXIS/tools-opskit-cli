---
name: query-service-tickets
description: List and view customer incidents, changes, and service requests from Jira. Use when the user needs to check open tickets, review incident details, or look up service request status.
allowed-tools: Bash(python:*)
---

# Query Service Tickets

Look up customer incidents, change requests, and service requests from Jira.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Jira server URL, username, and API token (use the **retrieve-secrets** skill)

## Workflow

1. **Identify the customer** — determine which customer's tickets to query.
2. **Obtain credentials** — use the **retrieve-secrets** skill to get Jira credentials.
3. **Search or list tickets** — use JQL queries to find relevant tickets.
4. **Present results** — show ticket details in a readable format.

## Usage

```bash
# List recent incidents for a project
python skills/query-service-tickets/scripts/query_jira.py \
  --server "https://company.atlassian.net" \
  --action search \
  --jql "project = PROJ AND issuetype = Incident ORDER BY created DESC" \
  --max-results 20

# Get details of a specific ticket
python skills/query-service-tickets/scripts/query_jira.py \
  --server "https://company.atlassian.net" \
  --action get \
  --issue-key "PROJ-1234"

# List open service requests
python skills/query-service-tickets/scripts/query_jira.py \
  --server "https://company.atlassian.net" \
  --action search \
  --jql "project = PROJ AND issuetype = 'Service Request' AND status != Done"

# Get comments on a ticket
python skills/query-service-tickets/scripts/query_jira.py \
  --server "https://company.atlassian.net" \
  --action get-comments \
  --issue-key "PROJ-1234"
```

### Actions

| Action | Description |
|--------|-------------|
| `search` | Search tickets using JQL |
| `get` | Get full details of a specific ticket |
| `get-comments` | Get comments/discussion on a ticket |

### Common JQL Patterns

- Open incidents: `issuetype = Incident AND status != Done`
- Recent changes: `issuetype = "Change Request" AND created >= -7d`
- High priority: `priority in (Critical, High) AND status != Done`
- Assigned to team: `assignee in membersOf("team-name")`

## Important

- **Read-only** — never create, modify, or transition tickets
- Be mindful of large result sets — use `--max-results` to limit

## Reference

See [Jira API reference](references/jira-api.md) for API details.
