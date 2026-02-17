# Dataverse Web API Reference

## Authentication

Use Azure AD OAuth2 client credentials flow:
- **Tenant ID** — Azure AD tenant of the customer
- **Client ID** — Registered Azure AD application
- **Client Secret** — Application secret
- **Scope** — `{environment_url}/.default`

## Base URL

```
https://{org}.crm{N}.dynamics.com/api/data/v9.2/
```

Where `N` is the region number (e.g., `crm4` for Europe).

## OData Query Syntax

```
GET /api/data/v9.2/{entitysetname}?$select=col1,col2&$filter=name eq 'value'&$top=10&$orderby=createdon desc
```

### Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `$select` | Columns to return | `$select=name,accountnumber` |
| `$filter` | Row filter | `$filter=statecode eq 0` |
| `$top` | Limit results | `$top=50` |
| `$orderby` | Sort order | `$orderby=createdon desc` |
| `$expand` | Related entities | `$expand=primarycontactid($select=fullname)` |
| `$count` | Include count | `$count=true` |

### Filter Operators

- `eq`, `ne`, `gt`, `ge`, `lt`, `le`
- `contains(field,'value')`, `startswith(field,'value')`, `endswith(field,'value')`
- `and`, `or`, `not`

## FetchXML Query Syntax

```xml
<fetch top="50" distinct="true">
  <entity name="account">
    <attribute name="name"/>
    <attribute name="accountnumber"/>
    <filter>
      <condition attribute="statecode" operator="eq" value="0"/>
    </filter>
    <order attribute="createdon" descending="true"/>
  </entity>
</fetch>
```

Pass as URL parameter: `GET /api/data/v9.2/accounts?fetchXml={encoded_xml}`

## Common Entity Set Names

| Entity | Entity Set Name |
|--------|----------------|
| Account | `accounts` |
| Contact | `contacts` |
| Lead | `leads` |
| Opportunity | `opportunities` |
| Case (Incident) | `incidents` |
| Solution | `solutions` |
| Solution Component | `solutioncomponents` |
| Plugin Trace Log | `plugintracelogs` |
| Audit | `audits` |
| System Job | `asyncoperations` |
| Workflow | `workflows` |
| Flow Session | `flowsessions` |

## Rate Limits

- API Protection limits apply (5000 requests per user per 24 hours by default)
- Use `$top` and pagination (`@odata.nextLink`) for large datasets
