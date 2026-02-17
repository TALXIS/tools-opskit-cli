# OpsKit

Operational toolkit plugin for [GitHub Copilot CLI](https://github.com/github/copilot-cli) and [Claude Code](https://docs.claude.com/en/docs/claude-code/plugins). Provides skills for managing customer environments, querying data, inspecting code, reading logs, and more.

## Installation

### GitHub Copilot CLI / Claude Code

```
/plugin marketplace add TALXIS/tools-opskit-cli
/plugin install opskit@talxis
```

## Available Skills

| Skill | Description |
|-------|-------------|
| **query-environment-data** | Run read-only SQL and OData queries against a Dataverse environment using the [PowerPlatform Dataverse Client SDK](https://github.com/microsoft/PowerPlatform-DataverseClient-Python) |
| **inspect-code** | Look up Azure DevOps repositories to analyze customer system source code |
| **query-environment-logs** | Read plugin trace logs, audit logs, flow run history, and other environment logs |
| **query-service-tickets** | List and view customer incidents, changes, and service requests from Jira |
| **retrieve-secrets** | Read environment authentication information for accessing customer tenants |
| **list-environments** | Print environments, tenants, and their details for a customer |
| **list-deployments** | View recent deployments and their status |

## Prerequisites

Python 3.10+ with dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

For interactive authentication (devbox environments), log in via Azure CLI:

```bash
az login
```

See each skill's `SKILL.md` for detailed usage and authentication options.

## Development

```bash
# Test locally with Claude Code
claude --plugin-dir .

# Test locally with Copilot CLI (skills are auto-discovered)
copilot
```

## License

MIT — see [LICENSE](LICENSE).
