# Jira REST API Reference

## Authentication

Use HTTP Basic auth with email and API token:
```
Authorization: Basic base64("{email}:{api_token}")
```

Generate API tokens at: https://id.atlassian.com/manage-profile/security/api-tokens

## Base URL

```
https://{instance}.atlassian.net/rest/api/3/
```

## Key Endpoints

### Search (JQL)

```
GET /rest/api/3/search?jql={jql}&maxResults=20&startAt=0
```

### Get Issue

```
GET /rest/api/3/issue/{issueIdOrKey}
```

### Get Comments

```
GET /rest/api/3/issue/{issueIdOrKey}/comment
```

## JQL Quick Reference

### Filters

| Filter | Example |
|--------|---------|
| Project | `project = PROJ` |
| Issue type | `issuetype = Incident` |
| Status | `status = "In Progress"` |
| Priority | `priority in (Critical, High)` |
| Assignee | `assignee = "user@company.com"` |
| Created date | `created >= -7d` |
| Updated date | `updated >= "2024-01-01"` |
| Labels | `labels = "production"` |
| Text search | `text ~ "error message"` |
| Component | `component = "Backend"` |

### Operators

- `=`, `!=`, `>`, `>=`, `<`, `<=`
- `in`, `not in`
- `~` (contains), `!~` (not contains)
- `is EMPTY`, `is not EMPTY`
- `was`, `was in`, `was not`, `was not in`, `changed`

### Sorting

```
ORDER BY created DESC
ORDER BY priority ASC, updated DESC
```

### Common Patterns

```
# Open incidents, newest first
project = PROJ AND issuetype = Incident AND status != Done ORDER BY created DESC

# High priority open issues
priority in (Critical, High) AND status != Done ORDER BY priority ASC

# Recently updated
updated >= -24h ORDER BY updated DESC

# Assigned to current user
assignee = currentUser() AND status != Done
```

## Python SDK

The `jira` package provides a high-level client:

```python
from jira import JIRA

client = JIRA(server="https://company.atlassian.net", basic_auth=("email", "token"))
issues = client.search_issues("project = PROJ", maxResults=50)
issue = client.issue("PROJ-123")
comments = client.comments("PROJ-123")
```
