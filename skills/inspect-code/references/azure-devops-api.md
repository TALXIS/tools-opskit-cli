# Azure DevOps REST API Reference

## Authentication

Authentication is handled via `az login`. Access tokens are obtained using:
```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798
```

The resource ID `499b84ac-1321-427f-aa17-267ca6975798` is the Azure DevOps service principal.

## Base URLs

```
https://dev.azure.com/{organization}/{project}/_apis/       # Core APIs (Git, Build, etc.)
https://almsearch.dev.azure.com/{organization}/{project}/    # Search API
https://vsrm.dev.azure.com/{organization}/{project}/         # Release Management API
```

## Key Endpoints

### Git Repositories

```
GET /_apis/git/repositories?api-version=7.1
GET /_apis/git/repositories/{repoId}/items?path=/&recursionLevel=OneLevel&api-version=7.1
GET /_apis/git/repositories/{repoId}/items?path={filePath}&api-version=7.1
```

### Git Commits (History)

```
GET /_apis/git/repositories/{repoId}/commits?$top=10&api-version=7.1
GET /_apis/git/repositories/{repoId}/commits?searchCriteria.itemPath={filePath}&$top=10&api-version=7.1
```

Returns commit history with author, date, message. Use `searchCriteria.itemPath` to filter commits affecting a specific file.

### Code Search

```
POST https://almsearch.dev.azure.com/{organization}/{project}/_apis/search/codesearchresults?api-version=7.1
Body: {
  "searchText": "ntg_documentsignature path:workflows ext:json",
  "$top": 25,
  "$skip": 0,
  "filters": {
    "Repository": ["RepoName"],
    "Path": ["workflows"],
    "CodeElement": ["json"]
  }
}
```

Search text supports inline filters:
- `path:workflows` — filter by directory path
- `ext:json` — filter by file extension
- `repo:RepoName` — filter by repository name

Requires the Azure DevOps Search extension to be enabled on the organization.

### Pipelines / Builds

```
GET /_apis/build/builds?$top=10&api-version=7.1
GET /_apis/build/builds/{buildId}?api-version=7.1
GET /_apis/build/builds/{buildId}/timeline?api-version=7.1
```

### Releases

```
GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?$top=10&api-version=7.1
GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{releaseId}?api-version=7.1
```

## Azure CLI

The `az devops` extension provides CLI access:

```bash
# Install extension
az extension add --name azure-devops

# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/thenetworg project=INT0015

# List repositories
az repos list --org https://dev.azure.com/thenetworg --project INT0015

# Invoke arbitrary API endpoints
az devops invoke --area git --resource repositories --org ...
```

## Useful Scopes for PAT

| Scope | Permissions |
|-------|-------------|
| `Code (Read)` | Read source code and metadata |
| `Build (Read)` | Read build definitions and results |
| `Release (Read)` | Read release definitions and deployments |
| `Project and Team (Read)` | Read project information |
