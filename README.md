# OpsKit

Operational toolkit plugin for [GitHub Copilot CLI](https://github.com/github/copilot-cli) and [Claude Code](https://docs.claude.com/en/docs/claude-code/plugins). Provides skills for managing customer environments, querying data, inspecting code, reading logs, and more.

## Installation

### GitHub Copilot CLI / Claude Code

```
/plugin marketplace add TALXIS/tools-opskit-cli
/plugin install opskit@talxis
```

## Quick Start

### 1. Set up the virtual environment

```bash
python3 scripts/bootstrap.py setup
```

### 2. Configure provider connections

```bash
# Jira
python3 scripts/bootstrap.py add-connection jira main

# Azure DevOps
python3 scripts/bootstrap.py add-connection ado main

# Dataverse
python3 scripts/bootstrap.py add-connection dataverse main
```

### 3. Check readiness

```bash
python3 scripts/bootstrap.py status
```

### 4. Set up a workspace (per customer)

Create `ops/opskit.json` in your project directory:

```json
{
  "environment_url": "https://orgname.crm4.dynamics.com",
  "connections": {
    "jira": "main",
    "ado": "main",
    "dataverse": "main"
  }
}
```

## Available Skills

| Skill | Description |
|-------|-------------|
| **query-environment-data** | Run read-only SQL and OData queries against a Dataverse environment using the [PowerPlatform Dataverse Client SDK](https://github.com/microsoft/PowerPlatform-DataverseClient-Python) |
| **inspect-code** | Look up Azure DevOps repositories to analyze customer system source code |
| **query-environment-logs** | Read plugin trace logs, audit logs, flow run history, and other environment logs |
| **query-service-tickets** | List and view customer incidents, changes, and service requests from Jira |
| **list-deployments** | View recent deployments and their status |

## Troubleshooter

The `/troubleshoot` command provides a structured workflow for investigating customer support tickets. It orchestrates all available skills to gather diagnostic data and produces evidence-based findings.

### Usage

```
/troubleshoot TICKET-1234
```

Running without a ticket ID starts a playground session for ad-hoc investigation.

### What It Does

1. Checks provider status — reports which tools are available
2. Fetches ticket details, comments, and attachments from Jira
3. Identifies the customer environment and gathers logs, data, code, and deployment info
4. Produces structured documentation in `ops/<ticket-id>/`:
   - `findings.md` — Evidence-based findings (always produced)
   - `rca.md` — Root cause analysis (only when evidence supports it)
   - `action-plan.md` — Resolution steps (only when requested)

## Configuration

### Two-level config

- **Global** (`config.json` + `connections.json` at plugin root) — provider connections and defaults
- **Workspace** (`ops/opskit.json` in project dir) — per-customer environment URL and connection overrides

### Connection management

```bash
python3 scripts/bootstrap.py add-connection <provider> <name>
python3 scripts/bootstrap.py remove-connection <provider> <name>
python3 scripts/bootstrap.py set-default <provider> <name>
python3 scripts/bootstrap.py list-connections
```

### Auth model

- **Jira**: Connection stores server URL + email + API token
- **ADO / Dataverse**: Connection stores metadata (org URL, project, tenant ID). Tokens managed by Azure CLI (`az login`)

## Prerequisites

- Python 3.10+
- Azure CLI for ADO/Dataverse: `az login`
- Dependencies installed via `bootstrap.py setup`

See each skill's `SKILL.md` for detailed usage.

## Development

```bash
# Test locally with Claude Code
claude --plugin-dir .

# Test locally with Copilot CLI (skills are auto-discovered)
copilot
```

## License

MIT — see [LICENSE](LICENSE).
