# Azure DevOps REST API Reference

## Authentication

Use a Personal Access Token (PAT) with HTTP Basic auth:
```
Authorization: Basic base64(":{PAT}")
```

## Base URL

```
https://dev.azure.com/{organization}/{project}/_apis/
```

## Key Endpoints

### Git Repositories

```
GET /_apis/git/repositories?api-version=7.1
GET /_apis/git/repositories/{repoId}/items?path=/&recursionLevel=OneLevel&api-version=7.1
GET /_apis/git/repositories/{repoId}/items?path={filePath}&api-version=7.1
```

### Code Search

```
POST https://almsearch.dev.azure.com/{organization}/{project}/_apis/search/codesearchresults?api-version=7.1
Body: {
  "searchText": "PluginBase",
  "$top": 25,
  "$skip": 0,
  "filters": {
    "Repository": ["RepoName"]
  }
}
```

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

## Python SDK

The `azure-devops` Python package provides typed clients:

```python
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

credentials = BasicAuthentication("", pat)
connection = Connection(base_url=org_url, creds=credentials)

git_client = connection.clients.get_git_client()
build_client = connection.clients.get_build_client()
```

## Useful Scopes for PAT

| Scope | Permissions |
|-------|-------------|
| `Code (Read)` | Read source code and metadata |
| `Build (Read)` | Read build definitions and results |
| `Release (Read)` | Read release definitions and deployments |
| `Project and Team (Read)` | Read project information |
