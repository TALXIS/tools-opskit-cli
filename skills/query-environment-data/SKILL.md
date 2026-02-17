---
name: query-environment-data
description: Run read-only Dataverse queries against a Power Platform environment. Use when the user needs to query, inspect, or analyze data in a customer's Dataverse environment using FetchXML or OData syntax.
allowed-tools: Bash(python:*)
---

# Query Environment Data

Run read-only data queries against a specific Power Platform / Dataverse environment.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Environment URL and authentication credentials (use the **retrieve-secrets** skill to obtain these)

## Workflow

1. **Identify the target environment** — ask the user which customer/environment to query, or use the **list-environments** skill to find it.
2. **Obtain credentials** — use the **retrieve-secrets** skill to get authentication details for the target tenant.
3. **Construct the query** — build a FetchXML or OData query based on what data the user needs.
4. **Execute the query** — run the query script against the environment's Dataverse Web API.
5. **Present results** — format and display the results in a readable table or summary.

## Usage

Run the query script:

```bash
python skills/query-environment-data/scripts/query_dataverse.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --query "<fetch><entity name='account'><attribute name='name'/></entity></fetch>" \
  --query-type fetchxml
```

### Supported Query Types

- **FetchXML** — XML-based query language for complex queries with aggregation, joins, and filtering
- **OData** — RESTful query syntax using `$filter`, `$select`, `$expand`, `$top`, `$orderby`

### Common Queries

- List accounts: `?$select=name,accountnumber&$top=10`
- Find contacts by email: `?$filter=contains(emailaddress1,'@example.com')`
- Get solution components: query `solutioncomponent` entity

## Important

- **Read-only operations only** — never modify or delete data
- Always confirm the target environment with the user before executing queries
- Be mindful of large result sets — use `$top` or FetchXML `count` to limit results

## Reference

See [Dataverse SDK reference](references/dataverse-sdk.md) for API details.
