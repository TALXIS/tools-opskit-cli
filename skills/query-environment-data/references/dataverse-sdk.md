# Dataverse SDK Reference

## PowerPlatform Dataverse Client for Python

Official Microsoft library for interacting with Dataverse environments.

### Installation

```bash
pip install PowerPlatform-Dataverse-Client
```

**Documentation:**
- PyPI: https://pypi.org/project/PowerPlatform-Dataverse-Client/
- GitHub: https://github.com/microsoft/PowerPlatform-DataverseClient-Python
- API Reference: https://learn.microsoft.com/python/api/dataverse-sdk-docs-python/dataverse-overview

### Authentication

The client supports multiple authentication methods via Azure Identity:

```python
from azure.identity import (
    InteractiveBrowserCredential,  # Browser authentication for devbox
    ClientSecretCredential,        # Service principal for production
    AzureCliCredential,           # If logged in via 'az login'
)
from PowerPlatform.Dataverse.client import DataverseClient

# Interactive browser authentication (devbox environments)
credential = InteractiveBrowserCredential()
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)

# Client secret authentication (customer tenants)
credential = ClientSecretCredential(tenant_id, client_id, client_secret)
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

**Authentication Requirements:**
- **Tenant ID** — Azure AD tenant of the customer
- **Client ID** — Registered Azure AD application
- **Client Secret** — Application secret (for service principal auth)
- **Scope** — Automatically handled by the client (`{environment_url}/.default`)

### SQL Queries (Recommended)

Execute read-only SQL queries using the Dataverse Web API `?sql=` parameter:

```python
# Simple query
results = client.query_sql(
    "SELECT TOP 10 accountid, name FROM account WHERE statecode = 0"
)
for record in results:
    print(record["name"])

# With ordering
results = client.query_sql(
    "SELECT TOP 10 name, createdon FROM account WHERE statecode = 0 ORDER BY createdon DESC"
)
```

**SQL Syntax Support:**
- `SELECT` with column names or `*`
- `TOP N` for limiting results
- `WHERE` clause with comparison operators (`=`, `<>`, `>`, `<`, `>=`, `<=`)
- `AND`, `OR`, `NOT` logical operators
- `LIKE` for pattern matching
- `ORDER BY` with `ASC` or `DESC`
- `INNER JOIN`, `LEFT JOIN` for relationships

**SQL Limitations:**
- Read-only operations (no INSERT, UPDATE, DELETE)
- Limited to Dataverse supported SQL subset
- Some advanced SQL features may not be available

### OData Queries (Advanced)

For complex filtering, navigation property expansion, and pagination:

```python
# Basic query with filter and select
pages = client.get(
    "account",
    select=["accountid", "name"],     # Case-insensitive
    filter="statecode eq 0",          # MUST use lowercase logical names
    orderby="createdon desc",
    top=100
)

for page in pages:
    for record in page:
        print(record["name"])

# Query with navigation property expansion
pages = client.get(
    "account",
    select=["name"],
    expand=["primarycontactid"],     # Case-sensitive!
    filter="statecode eq 0"
)

for page in pages:
    for account in page:
        contact = account.get("primarycontactid", {})
        print(f"{account['name']} - Contact: {contact.get('fullname', 'N/A')}")
```

**OData Parameters:**

| Parameter | Description | Case Sensitivity | Example |
|-----------|-------------|------------------|---------|
| `select` | Columns to return | Case-insensitive (auto-lowercased) | `["name", "accountnumber"]` |
| `filter` | Row filter | **Case-sensitive** (lowercase required) | `"statecode eq 0"` |
| `orderby` | Sort order | Case-insensitive | `"createdon desc"` |
| `top` | Limit results | N/A | `50` |
| `expand` | Navigation properties | **Case-sensitive** | `["primarycontactid"]` |

**Filter Operators:**
- Comparison: `eq`, `ne`, `gt`, `ge`, `lt`, `le`
- String functions: `contains(field,'value')`, `startswith(field,'value')`, `endswith(field,'value')`
- Logical: `and`, `or`, `not`

### Error Handling

```python
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError

try:
    results = client.query_sql("SELECT name FROM account")
except HttpError as e:
    print(f"HTTP {e.status_code}: {e.message}")
    print(f"Error code: {e.code}")
    if e.is_transient:
        print("Retry may succeed")
except ValidationError as e:
    print(f"Validation error: {e.message}")
```

### Environment URL Format

```
https://{org}.crm{N}.dynamics.com
```

Where `N` is the region number:
- `crm` — North America
- `crm4` — Europe
- `crm5` — APAC
- etc.

**Important:** No trailing slash in the URL.

## Common Table Schema Names

When querying tables, use the **schema name** (not display name):

| Display Name | Schema Name | Description |
|--------------|-------------|-------------|
| Account | `account` | Business account |
| Contact | `contact` | Person |
| Lead | `lead` | Potential customer |
| Opportunity | `opportunity` | Sales opportunity |
| Case | `incident` | Customer service case |
| Solution | `solution` | Customization solution |
| Solution Component | `solutioncomponent` | Solution parts |
| Plugin Trace Log | `plugintracelog` | Plugin execution logs |
| Audit | `audit` | Audit history |
| System Job | `asyncoperation` | Background jobs |
| Workflow | `workflow` | Classic workflows |
| Flow Session | `flowsession` | Power Automate runs |

### Custom Tables

Custom tables include a customization prefix (e.g., `new_`, `talxis_`):
- Schema name: `new_MyCustomTable`
- Column names: `new_MyCustomColumn`

## Rate Limits

- **API Protection limits** apply (5000 requests per user per 24 hours by default)
- Use `TOP` in SQL or `top` parameter in OData to limit result sets
- Client automatically handles pagination for large datasets

## Best Practices

1. **Use SQL for simple queries** — Cleaner syntax, easier to read
2. **Use OData for complex scenarios** — Navigation properties, advanced filtering
3. **Limit result sets** — Always use `TOP` or `top` parameter
4. **Reuse client instances** — Create once, query multiple times
5. **Handle errors gracefully** — Check `is_transient` for retry logic
6. **Use specific columns** — Don't select all columns unless needed
