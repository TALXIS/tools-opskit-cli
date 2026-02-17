#!/usr/bin/env python3
"""Query Dataverse environment data using the PowerPlatform Dataverse Client."""

import argparse
import base64
import json
import sys
from typing import Any, Dict, List, Optional

from azure.identity import (
    AzureCliCredential,
    ChainedTokenCredential,
    ClientSecretCredential,
    InteractiveBrowserCredential,
)
from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def _get_identity_from_token(credential, environment_url: str) -> Optional[Dict[str, str]]:
    """Decode the JWT access token to extract user/tenant info."""
    try:
        token = credential.get_token(f"{environment_url.rstrip('/')}/.default")
        payload = token.token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.b64decode(payload))
        return {
            "username": claims.get("upn", claims.get("unique_name", "unknown")),
            "tenant_id": claims.get("tid", "unknown"),
        }
    except Exception:
        return None


def create_client(
    environment_url: str,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    interactive: bool = False,
) -> DataverseClient:
    """
    Create a DataverseClient with appropriate authentication.

    Interactive auth tries Azure CLI first (silent if 'az login' was done),
    then falls back to browser prompt. No keychain or token cache files needed.
    """
    if interactive:
        credential = ChainedTokenCredential(
            AzureCliCredential(),
            InteractiveBrowserCredential(),
        )
    elif tenant_id and client_id and client_secret:
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        raise ValueError(
            "Either use --interactive flag or provide --tenant-id, --client-id, and --client-secret"
        )

    # Show who we're connecting as for safety
    identity = _get_identity_from_token(credential, environment_url)
    if identity:
        print(
            f"{identity['username']} → {environment_url}",
            file=sys.stderr,
        )
    else:
        print(f"Connecting to {environment_url}...", file=sys.stderr)

    return DataverseClient(environment_url, credential)


def list_tables(client: DataverseClient) -> List[Dict[str, str]]:
    """
    List all tables in the environment, returning just name/schema/type info.

    The SDK's list_tables() returns full metadata dicts. We extract
    the useful fields for a concise overview.
    """
    raw = client.list_tables()
    tables = []
    for t in raw:
        if isinstance(t, dict):
            tables.append({
                "LogicalName": t.get("LogicalName", ""),
                "SchemaName": t.get("SchemaName", ""),
                "EntitySetName": t.get("EntitySetName", ""),
                "PrimaryNameAttribute": t.get("PrimaryNameAttribute", ""),
                "IsCustomEntity": t.get("IsCustomEntity", False),
            })
        else:
            tables.append({"LogicalName": str(t), "SchemaName": str(t)})
    return tables


def _is_odata_annotation(key: str) -> bool:
    """Check if a key is an OData annotation (metadata, not user data)."""
    return key.startswith("@") or "@OData" in key or "@Microsoft" in key


def _strip_annotations(record: Dict[str, Any]) -> Dict[str, Any]:
    """Remove OData annotation keys from a record."""
    return {k: v for k, v in record.items() if not _is_odata_annotation(k)}


def get_table_columns(client: DataverseClient, table_name: str) -> List[Dict[str, str]]:
    """
    Discover columns for a table by querying a single record and returning
    the column names from the response.

    This is more reliable than the Attributes metadata endpoint because
    it returns the actual queryable column logical names.
    OData annotations (@odata.etag, etc.) are filtered out.
    """
    try:
        pages = client.get(table_name, top=1)
        for page in pages:
            if page:
                return [
                    {"LogicalName": k}
                    for k in sorted(page[0].keys())
                    if not _is_odata_annotation(k)
                ]
            break
    except (HttpError, ValidationError):
        pass
    return []


def query_sql(
    client: DataverseClient, sql_query: str, include_annotations: bool = False
) -> List[Dict[str, Any]]:
    """Execute a read-only SQL query against Dataverse."""
    results = client.query_sql(sql_query)
    if include_annotations:
        return list(results)
    return [_strip_annotations(r) for r in results]


def query_odata(
    client: DataverseClient,
    table_name: str,
    select: Optional[List[str]] = None,
    filter_expr: Optional[str] = None,
    orderby: Optional[List[str]] = None,
    top: Optional[int] = None,
    include_annotations: bool = False,
) -> List[Dict[str, Any]]:
    """
    Query Dataverse using OData parameters.

    Args:
        client: DataverseClient instance
        table_name: Table schema name (e.g., "account", "contact")
        select: List of column names to select
        filter_expr: OData filter expression (e.g., "statecode eq 0")
        orderby: List of order by expressions (e.g., ["createdon desc"])
        top: Maximum number of results to return
        include_annotations: If True, keep OData annotations (formatted values, etag, etc.)
    """
    kwargs: Dict[str, Any] = {}
    if select:
        kwargs["select"] = select
    if filter_expr:
        kwargs["filter"] = filter_expr
    if orderby:
        kwargs["orderby"] = orderby
    if top is not None:
        kwargs["top"] = top

    pages = client.get(table_name, **kwargs)

    all_records: List[Dict[str, Any]] = []
    for page in pages:
        if include_annotations:
            all_records.extend(page)
        else:
            all_records.extend(_strip_annotations(r) for r in page)
        print(f"  Fetched {len(all_records)} records...", file=sys.stderr)

    return all_records


def format_output(records: List[Dict[str, Any]], output_format: str = "json") -> str:
    """Format query results for output."""
    if output_format == "json":
        return json.dumps(records, indent=2, default=str)
    elif output_format == "table":
        if not records:
            return "No records found"

        columns = list(records[0].keys())

        # Calculate column widths
        widths = {col: len(str(col)) for col in columns}
        for record in records:
            for col in columns:
                widths[col] = max(widths[col], len(str(record.get(col, ""))))

        lines = []
        header = " | ".join(str(col).ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-+-".join("-" * widths[col] for col in columns))
        for record in records:
            row = " | ".join(str(record.get(col, "")).ljust(widths[col]) for col in columns)
            lines.append(row)

        return "\n".join(lines)
    else:
        return str(records)


def main():
    parser = argparse.ArgumentParser(
        description="Query Dataverse environment data using PowerPlatform Dataverse Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all tables (concise overview)
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --list-tables

  # Get table info including columns
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table-info talxis_contract

  # SQL query with interactive authentication
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --sql "SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0"

  # OData query with all records (no --top limit)
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table account --select name accountnumber --filter "statecode eq 0"

  # OData query with limit and ordering
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table contact --select fullname emailaddress1 --orderby "createdon desc" --top 10
        """,
    )

    # Environment and authentication
    parser.add_argument(
        "--environment-url",
        required=True,
        help="Dataverse environment URL (e.g., https://org.crm.dynamics.com)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Use interactive authentication (tries Azure CLI, falls back to browser)",
    )
    parser.add_argument("--tenant-id", help="Azure AD tenant ID (for client secret auth)")
    parser.add_argument("--client-id", help="Azure AD app client ID (for client secret auth)")
    parser.add_argument("--client-secret", help="Azure AD app client secret (for client secret auth)")

    # Action
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        "--sql",
        help='SQL query (e.g., "SELECT TOP 10 name FROM account WHERE statecode = 0")',
    )
    query_group.add_argument(
        "--table",
        help="Table name for OData query (e.g., account, contact)",
    )
    query_group.add_argument(
        "--list-tables",
        action="store_true",
        help="List all available tables in the environment",
    )
    query_group.add_argument(
        "--table-info",
        metavar="TABLE_NAME",
        help="Get table info and discover columns",
    )

    # OData parameters (used with --table)
    parser.add_argument(
        "--select",
        nargs="+",
        help="Columns to select (space-separated, e.g., name accountnumber)",
    )
    parser.add_argument(
        "--filter",
        help='OData filter expression (e.g., "statecode eq 0")',
    )
    parser.add_argument(
        "--orderby",
        nargs="+",
        help='Order by expressions (e.g., "createdon desc")',
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Maximum number of results to return (default: all records)",
    )

    # Output options
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--include-annotations",
        action="store_true",
        help="Include OData annotations (formatted values, etag, lookup names)",
    )

    args = parser.parse_args()

    try:
        client = create_client(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )

        if args.list_tables:
            print("Listing tables...", file=sys.stderr)
            tables = list_tables(client)
            output = format_output(tables, args.format)
            print(output)
            print(f"\n--- {len(tables)} table(s) found ---", file=sys.stderr)

        elif args.table_info:
            print(f"Getting info for table: {args.table_info}...", file=sys.stderr)
            info = client.get_table_info(args.table_info)
            if not info:
                print(f"Table '{args.table_info}' not found", file=sys.stderr)
                sys.exit(1)

            print(f"Discovering columns...", file=sys.stderr)
            columns = get_table_columns(client, args.table_info)
            info["columns"] = columns

            print(json.dumps(info, indent=2, default=str))

        elif args.sql:
            print("Executing SQL query...", file=sys.stderr)
            records = query_sql(client, args.sql, args.include_annotations)
            output = format_output(records, args.format)
            print(output)
            print(f"\n--- {len(records)} record(s) returned ---", file=sys.stderr)

        else:  # --table
            print(f"Querying table: {args.table}...", file=sys.stderr)
            records = query_odata(
                client=client,
                table_name=args.table,
                select=args.select,
                filter_expr=args.filter,
                orderby=args.orderby,
                top=args.top,
                include_annotations=args.include_annotations,
            )
            output = format_output(records, args.format)
            print(output)
            print(f"\n--- {len(records)} record(s) returned ---", file=sys.stderr)

    except (HttpError, ValidationError) as e:
        print(f"Dataverse Error: {e}", file=sys.stderr)
        if isinstance(e, HttpError):
            if e.subcode:
                print(f"  Subcode: {e.subcode}", file=sys.stderr)
            if e.details and e.details.get("service_error_code"):
                print(f"  Service error code: {e.details['service_error_code']}", file=sys.stderr)
            if e.is_transient:
                print("  This error may be transient. Consider retrying.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
