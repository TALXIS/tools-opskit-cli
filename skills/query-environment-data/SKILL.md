---
name: query-environment-data
description: Run read-only queries against a Power Platform environment using SQL or OData. Use when the user needs to query, inspect, or analyze data in a customer's Dataverse environment.
allowed-tools: Bash(python:*)
---

# Query Environment Data

Run read-only data queries against a specific Power Platform / Dataverse environment using the official Microsoft PowerPlatform Dataverse Client.

## Setup

First-time use — create a virtual environment and install dependencies:

```bash
cd skills/query-environment-data
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Prerequisites

- Python 3.10+ with dependencies from `requirements.txt` installed (see Setup above)
- Environment URL (format: `https://orgname.crm4.dynamics.com` — get from Power Platform admin center)
- Interactive browser authentication or client secret credentials

## Workflow

1. **Identify the target environment** — ask the user which customer/environment to query, or use the **list-environments** skill to find it.
2. **Obtain credentials** — use the **retrieve-secrets** skill to get authentication details for the target tenant, OR use interactive browser authentication (`--interactive`) if working in a devbox environment.
3. **Discover available tables** — run `--list-tables` to find what tables exist. The output includes LogicalName, SchemaName, EntitySetName, and whether it's a custom entity.
4. **Inspect table schema** — run `--table-info <table_name>` to get table metadata and a list of all queryable column names.
5. **Construct the query** — build a SQL query (preferred for simple reads) or OData query (for filters, ordering, paging) using the discovered column names.
6. **Execute the query** — run the query. For large tables the SDK automatically pages through all results.
7. **Present results** — use `--format table` for human-readable output or `--format json` for structured data.

## Usage

### Discovering Tables and Schemas

Before querying data, discover what tables and columns are available:

```bash
# List all tables (concise: LogicalName, SchemaName, EntitySetName)
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --list-tables

# Get table info + all queryable column names
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table-info talxis_contract
```

**Important:** Always discover the table schema first before constructing queries. Column names in Dataverse are lowercase logical names (e.g., `talxis_name`, `statecode`, `createdon`). `SELECT *` is NOT supported in SQL queries — you must specify column names explicitly.

### SQL Queries

SQL is the simplest query method for read-only data retrieval. Note the supported SQL subset:
- `SELECT col1, col2 FROM table` (no `SELECT *`)
- `WHERE`, `TOP`, `ORDER BY`, `AND`/`OR`
- `GROUP BY` and aggregations are NOT supported

```bash
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --sql "SELECT TOP 10 talxis_name, createdon FROM talxis_contract WHERE statecode = 0"
```

### OData Queries

OData queries support filtering, ordering, column selection, and automatic paging through all results:

```bash
# Fetch all records (SDK auto-pages)
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table talxis_contract \
  --select talxis_name talxis_contractid createdon statecode

# With filter and limit
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table talxis_contract \
  --select talxis_name createdon \
  --filter "statecode eq 0" \
  --orderby "createdon desc" \
  --top 10

# Table output format
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table contact --select fullname emailaddress1 --top 5 --format table
```

## Authentication Methods

### Interactive (Devbox Environments)
Use the `--interactive` flag. This tries **Azure CLI** first (silent, no prompt if `az login` was done), then falls back to a browser prompt. Every invocation prints the authenticated user and target environment (e.g., `tomas.prokop@thenetw.org → https://org.crm4.dynamics.com`) so the user always sees where they're connecting.

To switch tenants or users, run `az login --tenant <tenant-id>` before invoking the script.

### Client Secret (Customer Tenants)
Use `--tenant-id`, `--client-id`, and `--client-secret` for service principal authentication. Obtain these credentials using the **retrieve-secrets** skill.

## SDK Behavior Notes

- **Authentication is silent when `az login` is active** — no browser prompts or keychain dialogs. Falls back to browser if Azure CLI is not logged in.
- **Paging is automatic** — the SDK fetches all pages. For large tables (10k+ records), progress is reported to stderr.
- **`SELECT *` is NOT supported** — always specify column names explicitly in SQL queries.
- **`GROUP BY` is NOT supported** in SQL — for aggregations, fetch all records and process in Python.
- **`orderby` accepts multiple expressions** — e.g., `--orderby "createdon desc" "talxis_name asc"`.
- **`--top` defaults to no limit** — omit it to fetch all records, or set it to limit results.
- **Column names are lowercase** — use logical names like `talxis_name`, not display names.
- **OData annotations** — by default stripped to save context tokens. Use `--include-annotations` to see formatted values (optionset labels, lookup names, etags).

## Important

- **Read-only operations only** — never modify or delete data
- Always confirm the target environment with the user before executing queries
- The environment URL must be in the format `https://orgname.crm4.dynamics.com` (no trailing slash)

## Reference

See [Dataverse SDK reference](references/dataverse-sdk.md) for API details.
