# OpsKit

Operational toolkit plugin for [GitHub Copilot CLI](https://github.com/github/copilot-cli) and [Claude Code](https://docs.claude.com/en/docs/claude-code/plugins). Provides skills for managing customer environments, querying data, inspecting code, reading logs, and more.

## Installation

### GitHub Copilot CLI

```
/plugin marketplace add TALXIS/tools-opskit-cli
/plugin install opskit@opskit
```

### Claude Code

```
/plugin marketplace add TALXIS/tools-opskit-cli
/plugin install opskit@opskit
```

## Available Skills

| Skill | Description |
|-------|-------------|
| **query-environment-data** | Run read-only Dataverse queries (FetchXML/OData) against a customer environment |
| **inspect-code** | Look up Azure DevOps repositories to analyze customer system source code |
| **query-environment-logs** | Read plugin trace logs, audit logs, flow run history, and other environment logs |
| **query-service-tickets** | List and view customer incidents, changes, and service requests from Jira |
| **retrieve-secrets** | Read environment authentication information for accessing customer tenants |
| **list-environments** | Print environments, tenants, and their details for a customer |
| **list-deployments** | View recent deployments and their status |

## Prerequisites

Skills use Python scripts that require dependencies listed in `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

Scripts also require appropriate credentials and environment configuration. See each skill's `SKILL.md` for details.

## Development

```bash
# Test locally with Claude Code
claude --plugin-dir .

# Test locally with Copilot CLI (skills are auto-discovered)
copilot
```

## License

MIT — see [LICENSE](LICENSE).
