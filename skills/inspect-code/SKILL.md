---
name: inspect-code
description: Look up Azure DevOps repositories to analyze customer system source code. Use when the user needs to understand how a customer's system is implemented, find specific code patterns, or review solution architecture.
allowed-tools: Bash(python:*)
---

# Inspect Code

Look up and analyze source code from Azure DevOps repositories that contain a customer's system implementation.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Azure DevOps organization URL and Personal Access Token (use the **retrieve-secrets** skill)

## Workflow

1. **Identify the customer** — determine which customer's codebase to inspect.
2. **Obtain credentials** — use the **retrieve-secrets** skill to get Azure DevOps PAT.
3. **List repositories** — browse available repos in the customer's Azure DevOps project.
4. **Search or browse code** — find specific files, patterns, or browse the repository tree.
5. **Analyze** — review the code and explain findings to the user.

## Usage

```bash
# List repositories in a project
python skills/inspect-code/scripts/inspect_ado_repo.py \
  --organization "https://dev.azure.com/orgname" \
  --project "ProjectName" \
  --action list-repos

# Search code across repos
python skills/inspect-code/scripts/inspect_ado_repo.py \
  --organization "https://dev.azure.com/orgname" \
  --project "ProjectName" \
  --action search \
  --query "PluginBase"

# Get file contents
python skills/inspect-code/scripts/inspect_ado_repo.py \
  --organization "https://dev.azure.com/orgname" \
  --project "ProjectName" \
  --repo "RepoName" \
  --action get-file \
  --path "src/Plugins/AccountPlugin.cs"

# List files in directory
python skills/inspect-code/scripts/inspect_ado_repo.py \
  --organization "https://dev.azure.com/orgname" \
  --project "ProjectName" \
  --repo "RepoName" \
  --action list-files \
  --path "src/"
```

### Actions

| Action | Description |
|--------|-------------|
| `list-repos` | List all repositories in the project |
| `list-files` | List files and directories at a path |
| `get-file` | Retrieve contents of a specific file |
| `search` | Search for code patterns across repositories |

## Important

- **Read-only** — never push, commit, or modify code in customer repositories
- Respect access boundaries — only access repos the credentials permit

## Reference

See [Azure DevOps API reference](references/azure-devops-api.md) for API details.
