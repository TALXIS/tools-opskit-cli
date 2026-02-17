# Jira REST API Reference

## Authentication

Use HTTP Basic auth with email and API token:
```
Authorization: Basic base64("{email}:{api_token}")
```

Generate API tokens at: https://id.atlassian.com/manage-profile/security/api-tokens

## Base URLs

```
Jira Platform API:  https://{instance}.atlassian.net/rest/api/3/
Service Desk API:   https://{instance}.atlassian.net/rest/servicedeskapi/
```

## Jira Platform API (v3)

### Search (JQL)

```
POST /rest/api/3/search/jql
Content-Type: application/json

{"jql": "project = CASE", "maxResults": 50, "fields": ["summary", "status"]}
```

Response is paginated with `nextPageToken`. Pass it back in subsequent requests to get the next page.

### Get Issue

```
GET /rest/api/3/issue/{issueIdOrKey}
GET /rest/api/3/issue/{issueIdOrKey}?fields=summary,status,description,attachment
```

### Get Comments

```
GET /rest/api/3/issue/{issueIdOrKey}/comment?startAt=0&maxResults=100&orderBy=created
```

Response: `{ "comments": [...], "startAt": 0, "maxResults": 100, "total": 5 }`

### Get Attachment Metadata

```
GET /rest/api/3/attachment/{id}
```

### Download Attachment Content

```
GET /rest/api/3/attachment/content/{id}?redirect=false
```

Returns the binary file content directly when `redirect=false`.

## Service Desk API

### List Organizations

```
GET /rest/servicedeskapi/organization?start=0&limit=50
```

Response: `{ "values": [{"id": "1", "name": "Customer Name"}], "isLastPage": false, "start": 0, "limit": 50 }`

### Get Organization

```
GET /rest/servicedeskapi/organization/{organizationId}
```

### List Service Desks

```
GET /rest/servicedeskapi/servicedesk?start=0&limit=50
```

## JQL Quick Reference

### Filters

| Filter | Example |
|--------|---------|
| Project | `project = CASE` |
| Issue type | `issuetype = Incident` |
| Status | `status = "In Progress"` |
| Priority | `priority in (Critical, High)` |
| Assignee | `assignee = "user@company.com"` |
| Organization | `organizations = "Customer Name"` |
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
project = CASE AND issuetype = Incident AND status != Done ORDER BY created DESC

# High priority open issues
project = CASE AND priority in (Critical, High) AND status != Done ORDER BY priority ASC

# Recently updated
project = CASE AND updated >= -24h ORDER BY updated DESC

# Issues for a specific customer organization
project = CASE AND organizations = "Customer Name" ORDER BY created DESC
```

## Notes

- **ADF (Atlassian Document Format)**: API v3 returns descriptions and comments in ADF format (JSON document model), not plain text. The script converts ADF to readable text automatically.
- **Pagination**: Search uses offset-based pagination (`startAt`/`maxResults`). Service Desk API uses `start`/`limit` with `isLastPage`.
- **Rate limits**: Atlassian Cloud enforces rate limits. The API returns `429 Too Many Requests` when exceeded.
