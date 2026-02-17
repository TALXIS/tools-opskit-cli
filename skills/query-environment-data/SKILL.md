---
name: query-environment-data
description: Run read-only queries against a Power Platform environment using SQL or OData. Use when the user needs to query, inspect, or analyze data in a customer's Dataverse environment.
allowed-tools: Bash(python:*)
---

# Query Environment Data

Run read-only data queries against a specific Power Platform / Dataverse environment using the official Microsoft PowerPlatform Dataverse Client.

## Setup

First-time use — run the bootstrap script to create a virtual environment and install dependencies:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py setup
```

Configure a Dataverse connection:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection dataverse main
```

Set the customer environment URL in `ops/opskit.json`:

```json
{"environment_url": "https://orgname.crm4.dynamics.com"}
```

Verify readiness:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py check dataverse
```

## Prerequisites

- Python 3.10+ with dependencies installed via `bootstrap.py setup`
- Azure CLI logged in: `az login`
- A Dataverse connection configured via `bootstrap.py add-connection dataverse <name>`
- Environment URL in `ops/opskit.json` or passed as `--environment-url`

## Workflow

1. **Identify the target environment** — ask the user for the environment URL (format: `https://orgname.crm4.dynamics.com`).
2. **Obtain credentials** — use interactive browser authentication (`--interactive`) if working in a devbox environment, or ask the user for service principal credentials (`--tenant-id`, `--client-id`, `--client-secret`).
3. **Discover available tables** — use `list_tables.py` to find what tables exist.
4. **Inspect table schema** — use `get_table_info.py --table <name>` to get metadata and column names.
5. **Query data** — use `query_dataverse.py` with SQL or OData using the discovered column names.
6. **Present results** — use `--format table` for human-readable output or `--format json` for structured data.

## Scripts

> **Note:** `--environment-url` is auto-populated from `ops/opskit.json` if configured. Pass it explicitly only to override. `--interactive` defaults to true when Azure CLI is logged in.

### `list_tables.py` — List All Tables

Discover what tables exist in the environment:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/list_tables.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive

# Table format for quick scanning
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/list_tables.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive --format table
```

Returns: `LogicalName`, `SchemaName`, `EntitySetName`, `IsCustomEntity` for each table.

**Arguments:** Auth args + `--format` only.

### `get_table_info.py` — Inspect Table Schema

Get table metadata and all queryable column names:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/get_table_info.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --table account
```

Returns: table schema name, logical name, entity set name, metadata ID, and a full list of column logical names.

**Arguments:**
- `--table` (required): Logical name of the table to inspect
- Auth args + `--format`

**Important:** Always inspect the table schema before constructing queries. Column names in Dataverse are lowercase logical names (e.g., `name`, `statecode`, `createdon`). `SELECT *` is NOT supported in SQL queries — you must specify column names explicitly.

### `query_dataverse.py` — SQL and OData Queries

Run read-only queries using SQL or OData syntax:

```bash
# SQL query (simplest for read-only retrieval)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --sql "SELECT TOP 10 name, createdon FROM account WHERE statecode = 0"

# OData query with filtering and ordering
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --table account \
  --select name createdon \
  --filter "statecode eq 0" \
  --orderby "createdon desc" \
  --top 10

# Table output format
python3 ${CLAUDE_PLUGIN_ROOT}/skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" --interactive \
  --table contact --select fullname emailaddress1 --top 5 --format table
```

**Arguments:**
- `--sql` or `--table` (required, mutually exclusive): SQL query string or table logical name for OData
- `--select`: Column names to return (OData mode, space-separated)
- `--filter`: OData `$filter` expression (OData mode)
- `--orderby`: OData `$orderby` expression(s) (OData mode)
- `--top`: Maximum number of records to return
- `--format`: `json` (default) or `table`
- `--include-annotations`: Include OData annotations (formatted values, lookup names)

**SQL notes:**
- `SELECT col1, col2 FROM table` — no `SELECT *`
- `WHERE`, `TOP`, `ORDER BY`, `AND`/`OR` supported
- `GROUP BY` and aggregations are NOT supported

## Authentication Methods

### Interactive (Devbox Environments)
Use the `--interactive` flag. This tries **Azure CLI** first (silent, no prompt if `az login` was done), then falls back to a browser prompt. Every invocation prints the authenticated user and target environment (e.g., `user@contoso.com → https://org.crm4.dynamics.com`).

To switch tenants or users, run `az login --tenant <tenant-id>` before invoking the script.

### Client Secret (Customer Tenants)
Use `--tenant-id`, `--client-id`, and `--client-secret` for service principal authentication.

## Behavior Notes

- **Authentication is silent when `az login` is active** — no browser prompts needed.
- **Paging is automatic** — the SDK fetches all pages. For large tables (10k+ records), progress is reported to stderr.
- **`SELECT *` is NOT supported** — always specify column names explicitly in SQL queries.
- **`GROUP BY` is NOT supported** in SQL — for aggregations, fetch all records and process in Python.
- **`--orderby` accepts multiple expressions** — e.g., `--orderby "createdon desc" "name asc"`.
- **`--top` defaults to no limit** — omit it to fetch all records, or set it to limit results.
- **Column names are lowercase** — use logical names, not display names.
- **OData annotations** — stripped by default. Use `--include-annotations` to retain OData system annotations (etag, etc.). Note: `@OData.Community.Display.V1.FormattedValue` labels for option sets (e.g. statuscode) are not currently returned — to resolve a numeric code to its label, use `get_table_info.py --table <table>` which includes column metadata, or look up the option set in the Maker Portal.
- **Filtering tables by name** — `list_tables.py --search <text>` filters results client-side by logical name substring.

## Important

- **Read-only operations only** — never modify or delete data
- Always confirm the target environment with the user before executing queries
- The environment URL must be in the format `https://orgname.crm4.dynamics.com` (no trailing slash)

## Reference

See [Dataverse SDK reference](references/dataverse-sdk.md) for API details.
