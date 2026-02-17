---
name: inspect-code
description: Look up Azure DevOps repositories to analyze customer system source code. Use when the user needs to understand how a customer's system is implemented, find specific code patterns, or review solution architecture.
allowed-tools: Bash(python:*)
---

# Inspect Code

Look up and analyze source code from Azure DevOps repositories that contain a customer's system implementation.

## Setup

Configure an Azure DevOps connection:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection ado main
```

Or verify existing configuration:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py check ado
```

## Prerequisites

- Python 3.10+
- Azure CLI with `azure-devops` extension: `az extension add --name azure-devops`
- Authenticated: `az login`
- An ADO connection configured via `bootstrap.py add-connection ado <name>` (stores organization URL, project, tenant ID)

## Connection Configuration

Organization and project are resolved from the connection config in `connections.json`. CLI flags (`--organization`, `--project`) override connection values.

## Workflow

1. **Identify the customer** — determine which customer's codebase to inspect.
2. **Search for code** — use the `search` action to find files by name, content, path, or extension.
3. **Browse and read** — use `list-files` and `get-file` to explore the repository.
4. **Check recent changes** — use `git-history` to see who changed the file and when.

> **Tip: Always discover the exact file path before using `git-history`.** The `git-history` action scopes to a path prefix — passing a broad path (e.g., `/src`) returns project-wide commits, not component-specific history. Always search for the component by name first (`--action search --query <name>`) to get the exact file path, then pass that path to `git-history`.

### Troubleshooting a Failing Flow (Example)

1. Query the Jira ticket → `query-service-tickets`
2. Find the failing flow name from environment logs → `query-environment-logs`
3. Search for the flow source: `--action search --query "ntg_documentsignature" --path-filter "workflows" --extension-filter "json"`
4. Read the flow definition: `--action get-file --repo <repo> --path <path>`
5. Check recent changes: `--action git-history --repo <repo> --path <path> --top 10`

## Usage

```bash
# Search for code across repositories (uses Azure DevOps Search API)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action search \
  --query "ntg_documentsignature" \
  --path-filter "workflows" \
  --extension-filter "json"

# Search within a specific repository
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action search \
  --query "PluginBase" \
  --repo-filter "MyRepo"

# List repositories in the project
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action list-repos

# List files in a directory
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action list-files \
  --repo "MyRepo" \
  --path "/src"

# Get file contents
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action get-file \
  --repo "MyRepo" \
  --path "/workflows/flow.json"

# View recent commits for a file (git blame/history)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --action git-history \
  --repo "MyRepo" \
  --path "/workflows/flow.json" \
  --top 10

# Override profile with explicit org/project
python3 ${CLAUDE_PLUGIN_ROOT}/skills/inspect-code/scripts/inspect_ado_repo.py \
  --organization "https://dev.azure.com/yourorg" \
  --project "YourProject" \
  --action search \
  --query "ntg_documentsignature"
```

### Actions

| Action | Description | Required Args |
|--------|-------------|---------------|
| `list-repos` | List all repositories in the project | — |
| `list-files` | List files and directories at a path | `--repo`, `--path` |
| `get-file` | Retrieve contents of a specific file | `--repo`, `--path` |
| `search` | Search for code patterns across repositories | `--query` |
| `git-history` | Show recent commits for a file or repo | `--repo` |

### Search Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `--path-filter` | Filter by directory path | `workflows` |
| `--extension-filter` | Filter by file extension | `json` |
| `--repo-filter` | Filter to a specific repository | `MyRepo` |
| `--top` | Maximum results (default: 25) | `50` |

Common search patterns:
- Power Automate flows: `--path-filter "workflows" --extension-filter "json"`
- C# plugins: `--query "PluginBase" --extension-filter "cs"`
- JavaScript web resources: `--path-filter "WebResources" --extension-filter "js"`

## Important

- **Read-only** — never push, commit, or modify code in customer repositories
- Respect access boundaries — only access repos the credentials permit
- The Search API requires the Azure DevOps Search extension to be enabled on the organization

## Reference

See [Azure DevOps API reference](references/azure-devops-api.md) for API details.
