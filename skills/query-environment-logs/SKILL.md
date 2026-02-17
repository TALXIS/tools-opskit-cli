---
name: query-environment-logs
description: Read logs from a Power Platform environment including plugin trace logs, audit logs, flow run history, flow run action details, flow definitions, and system jobs. Use when diagnosing issues, investigating errors, or reviewing environment activity.
allowed-tools: Bash(python:*)
---

# Query Environment Logs

Read and analyze various logs from a specific Power Platform / Dataverse environment using the official Microsoft PowerPlatform Dataverse Client and the Flow Management API.

## Setup

First-time use — create a virtual environment and install dependencies:

```bash
cd skills/query-environment-logs
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Prerequisites

- Python 3.10+ with dependencies from `requirements.txt` installed (see Setup above)
- Environment URL (format: `https://orgname.crm4.dynamics.com` — get from Power Platform admin center)
- Interactive browser authentication or client secret credentials

## Workflow

1. **Identify the target environment** — ask the user for the environment URL (format: `https://orgname.crm4.dynamics.com`).
2. **Obtain credentials** — use interactive browser authentication (`--interactive`) if working in a devbox environment, or ask the user for service principal credentials (`--tenant-id`, `--client-id`, `--client-secret`).
3. **Determine what to investigate** — choose the right script based on the task (see Scripts below).
4. **Query and analyze** — run the appropriate script, then present findings with relevant context.

### Troubleshooting a Failing Flow (Recommended Workflow)

1. **Find recent failures** — use `query_dataverse_logs.py --log-type flow-runs --status failed` to find failed run IDs
2. **Get action-level detail** — use `query_flow_runs.py --flow-id X --run-id Y` to see which specific action failed and the exact error
3. **Understand the flow logic** — use `get_flow_definition.py --flow-id X` to get the full implementation (triggers, actions, expressions)
4. **Correlate with plugin traces** — use `query_dataverse_logs.py --log-type plugin-trace --since ...` around the failure time

## Scripts

### `query_dataverse_logs.py` — Dataverse Log Queries

Query log tables via Dataverse OData: flow runs, plugin traces, audit trail, system jobs.

```bash
# Recent failed flow runs
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type flow-runs --status failed --top 20

# Flow runs since a date
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type flow-runs --since 2025-01-01T00:00:00Z

# Custom OData filter
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type flow-runs --filter "status eq 'Failed' and triggertype eq 'Automated'"

# Plugin trace logs
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type plugin-trace --top 50

# Audit entries for a specific entity
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type audit --entity account --top 20

# Failed system jobs
python scripts/query_dataverse_logs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --log-type system-jobs --status failed --top 10
```

**Arguments:**
- `--log-type` (required): `flow-runs`, `plugin-trace`, `audit`, `system-jobs`
- `--status`: Filter by status (values depend on log type — see Status Filter Values below)
- `--since`: ISO 8601 timestamp — filter records after this time
- `--entity`: Entity logical name (audit logs only)
- `--filter`: Raw OData `$filter` expression (overrides `--since`, `--status`, `--entity`)
- `--top`: Maximum number of records to return
- `--format`: `json` (default) or `table`

### `query_flow_runs.py` — Flow Run Details (Flow Management API)

List flow runs with error summaries, or get action-level detail for a specific run.

```bash
# List recent failed runs with error messages
python scripts/query_flow_runs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --flow-name my_flow --status failed --top 5

# Action-level detail for a specific run
python scripts/query_flow_runs.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --flow-id c655d528-0e52-ee11-be6d-00224880190f \
  --run-id 08585000000000000000000000000CU100
```

When `--run-id` is provided, returns per-action details: status, error code, error message, timing.
Without `--run-id`, lists recent runs with top-level status, trigger info, and error summaries.

**Arguments:**
- `--flow-name` or `--flow-id` (required, mutually exclusive): Flow display name or Dataverse `workflowid` GUID
- `--run-id`: Specific run to inspect (the logic app run ID, same as `flowrun.name` in Dataverse)
- `--status`: Filter runs by status (`failed`, `succeeded`)
- `--top`: Maximum number of runs to list (default: 10)
- `--format`: `json` (default) or `table`

### `get_flow_definition.py` — Flow Definition Retrieval

Retrieve the full flow implementation to understand triggers, actions, expressions, and connections.

```bash
python scripts/get_flow_definition.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --flow-name my_flow
```

Returns the Logic Apps workflow JSON with:
- **triggers** — what starts the flow (webhook, schedule, manual)
- **actions** — every step with type, inputs, parameters, expressions, and runAfter dependencies
- **connectionReferences** — which connectors and connections the flow uses

Uses the Flow Management API primarily, with a Dataverse `workflow.clientdata` fallback.

**Arguments:**
- `--flow-name` or `--flow-id` (required, mutually exclusive): Flow display name or Dataverse `workflowid` GUID
- `--format`: `json` (default) or `table`

## Log Types

| Log Type | Source | Table / API | Description |
|----------|--------|-------------|-------------|
| `flow-runs` | Dataverse OData | `flowrun` (elastic) | Cloud flow run history — status, duration, error summary. 28-day TTL. |
| `plugin-trace` | Dataverse OData | `plugintracelog` | Plugin execution traces with error details and stack traces. |
| `audit` | Dataverse OData | `audit` | Entity change audit trail — who changed what, when. |
| `system-jobs` | Dataverse OData | `asyncoperation` | Background system jobs — workflows, bulk operations, async plugins. |
| _(flow run actions)_ | Flow Management API | — | Per-action detail via `query_flow_runs.py --run-id` |
| _(flow definition)_ | Flow Management API | — | Full workflow JSON via `get_flow_definition.py` |

### Status Filter Values

| Log Type | Status Values |
|----------|---------------|
| `flow-runs` | `failed`, `succeeded`, `cancelled` |
| `system-jobs` | `failed`, `succeeded`, `waiting`, `in-progress`, `cancelled` |
| Flow runs (API) | `failed`, `succeeded` |
| `plugin-trace` | _(no status filter — use `--since` or `--filter`)_ |
| `audit` | _(no status filter — use `--entity`, `--since`, or `--filter`)_ |

## Authentication Methods

### Interactive (Devbox Environments)
Use the `--interactive` flag. This tries **Azure CLI** first (silent, no prompt if `az login` was done), then falls back to a browser prompt. Every invocation prints the authenticated user and target environment (e.g., `user@contoso.com → https://org.crm4.dynamics.com`).

The Flow API scripts (`query_flow_runs.py`, `get_flow_definition.py`) acquire additional tokens for the Flow Management API (`service.flow.microsoft.com`) and BAP API (`api.bap.microsoft.com`) automatically.

To switch tenants or users, run `az login --tenant <tenant-id>` before invoking the script.

### Client Secret (Customer Tenants)
Use `--tenant-id`, `--client-id`, and `--client-secret` for service principal authentication.

## Behavior Notes

- **`flowrun` is an elastic table** — data is partitioned and has a default TTL of 28 days.
- **Flow API endpoint discovery** — the regional endpoint (e.g., `emea.api.flow.microsoft.com`) is discovered automatically via the BAP API, with a domain heuristic fallback.
- **Flow ID mapping** — Dataverse `workflowid` ≠ Flow API `flowId`. Scripts resolve this automatically via the `workflow.resourceid` field.
- **Plugin trace logging must be enabled** in the environment for `plugin-trace` logs to appear.
- **Audit logging must be enabled** globally and per-entity for `audit` logs.
- **`--filter` overrides** `--since`, `--status`, and `--entity` — use it for complex custom queries.
- **OData annotations** — stripped by default. Use `--include-annotations` to see formatted values.
- **Authentication is silent when `az login` is active** — no browser prompts needed.

## Important

- **Read-only** — never modify or clear logs
- Use `--since` and `--top` to limit result size
- The environment URL must be in the format `https://orgname.crm4.dynamics.com` (no trailing slash)

## Reference

See [Logging sources reference](references/logging-sources.md) for details on each log type.
