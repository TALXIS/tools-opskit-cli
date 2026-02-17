---
name: query-environment-data
description: Run read-only queries against a Power Platform environment using SQL or OData. Use when the user needs to query, inspect, or analyze data in a customer's Dataverse environment.
allowed-tools: Bash(python:*)
---

# Query Environment Data

Run read-only data queries against a specific Power Platform / Dataverse environment using the official Microsoft PowerPlatform Dataverse Client.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Environment URL and authentication credentials (use the **retrieve-secrets** skill to obtain these)

## Workflow

1. **Identify the target environment** — ask the user which customer/environment to query, or use the **list-environments** skill to find it.
2. **Obtain credentials** — use the **retrieve-secrets** skill to get authentication details for the target tenant, OR use interactive browser authentication if working in a devbox environment.
3. **Discover available tables** — list all tables in the environment to find what data is available.
4. **Inspect table schema** — get detailed information about the table structure, including column names and types.
5. **Construct the query** — build a SQL query (preferred) or OData query based on the discovered schema.
6. **Execute the query** — run the query script against the environment's Dataverse Web API.
7. **Present results** — format and display the results in a readable table or JSON.

## Usage

### Discovering Tables and Schemas

Before querying data, discover what tables and columns are available:

```bash
# List all available tables
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --list-tables

# Get detailed information about a specific table
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table-info account
```

You can also use the Python API directly:

```python
from azure.identity import InteractiveBrowserCredential
from PowerPlatform.Dataverse.client import DataverseClient

# Connect to the environment
credential = InteractiveBrowserCredential()
client = DataverseClient("https://org.crm4.dynamics.com", credential)

# List all available tables
tables = client.list_tables()
print(f"Found {len(tables)} tables")
for table in tables[:10]:  # Show first 10
    print(f"  - {table}")

# Get detailed information about a specific table
table_info = client.get_table_info("account")
print(f"\nTable: {table_info['table_schema_name']}")
print(f"Logical Name: {table_info['table_logical_name']}")
print(f"Entity Set: {table_info['entity_set_name']}")
print(f"Primary Key: {table_info['primary_key_attribute']}")

# Columns are available in table metadata via Web API
# Use this information to construct your queries
```

**Important:** Always discover the table schema first before constructing queries. This ensures you use the correct table names and column names.

### SQL Queries (Recommended)

SQL is the recommended query method for simple, read-only data retrieval:

```bash
# Interactive authentication (devbox environment)
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --sql "SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0"

# Client secret authentication (customer tenant)
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --tenant-id "xxx-xxx-xxx" \
  --client-id "xxx-xxx-xxx" \
  --client-secret "xxx" \
  --sql "SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0"
```

### OData Queries (Advanced)

For more complex filtering, sorting, and relationship expansion:

```bash
# Query with filter and select
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table account \
  --select name accountnumber \
  --filter "statecode eq 0" \
  --orderby "createdon desc" \
  --top 10

# Output as table format
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --interactive \
  --table contact \
  --select fullname emailaddress1 \
  --top 5 \
  --format table
```

## Authentication Methods

### Interactive Browser (Devbox Environments)
Use the `--interactive` flag when running the script on a support user's computer. This will open a browser window for authentication using the user's credentials.

### Client Secret (Customer Tenants)
Use `--tenant-id`, `--client-id`, and `--client-secret` when accessing a customer's environment. Obtain these credentials using the **retrieve-secrets** skill.

## Common Query Examples

### SQL Examples
- List active accounts: `SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0`
- Find contacts by email: `SELECT fullname, emailaddress1 FROM contact WHERE emailaddress1 LIKE '%@example.com%'`
- Get solution components: `SELECT componenttype, objectid FROM solutioncomponent WHERE solutionid = '{solution-guid}'`

### OData Examples
- List accounts: `--table account --select name accountnumber --top 10`
- Find contacts by email: `--table contact --filter "contains(emailaddress1,'@example.com')"`
- Get active opportunities: `--table opportunity --filter "statecode eq 0" --orderby "createdon desc"`

## Important

- **Read-only operations only** — never modify or delete data
- Always confirm the target environment with the user before executing queries
- SQL queries support a limited subset of standard SQL syntax
- Be mindful of large result sets — use `TOP` in SQL or `--top` in OData to limit results

## Reference

See [Dataverse SDK reference](references/dataverse-sdk.md) for API details.
