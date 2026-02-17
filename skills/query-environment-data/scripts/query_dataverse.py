#!/usr/bin/env python3
"""Query Dataverse environment data using the PowerPlatform Dataverse Client."""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from azure.identity import ClientSecretCredential, InteractiveBrowserCredential
from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def create_client(
    environment_url: str,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    interactive: bool = False,
) -> DataverseClient:
    """
    Create a DataverseClient with appropriate authentication.
    
    Args:
        environment_url: Dataverse environment URL (e.g., https://org.crm.dynamics.com)
        tenant_id: Azure AD tenant ID (required for client secret auth)
        client_id: Azure AD app client ID (required for client secret auth)
        client_secret: Azure AD app client secret (required for client secret auth)
        interactive: If True, use interactive browser authentication
        
    Returns:
        Configured DataverseClient instance
    """
    if interactive:
        # Interactive browser authentication for devbox environments
        credential = InteractiveBrowserCredential()
        print("Opening browser for interactive authentication...", file=sys.stderr)
    elif tenant_id and client_id and client_secret:
        # Client secret authentication for customer tenants
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        raise ValueError(
            "Either use --interactive flag or provide --tenant-id, --client-id, and --client-secret"
        )
    
    return DataverseClient(environment_url, credential)


def query_sql(client: DataverseClient, sql_query: str) -> List[Dict[str, Any]]:
    """
    Execute a read-only SQL query against Dataverse.
    
    Args:
        client: DataverseClient instance
        sql_query: SQL query string (e.g., "SELECT TOP 10 name FROM account")
        
    Returns:
        List of records as dictionaries
    """
    try:
        results = client.query_sql(sql_query)
        return list(results)
    except HttpError as e:
        print(f"HTTP Error {e.status_code}: {e.message}", file=sys.stderr)
        if e.code:
            print(f"Error code: {e.code}", file=sys.stderr)
        if e.is_transient:
            print("This error may be transient. Consider retrying.", file=sys.stderr)
        raise
    except ValidationError as e:
        print(f"Validation Error: {e.message}", file=sys.stderr)
        raise


def query_odata(
    client: DataverseClient,
    table_name: str,
    select: Optional[List[str]] = None,
    filter_expr: Optional[str] = None,
    orderby: Optional[str] = None,
    top: int = 50,
) -> List[Dict[str, Any]]:
    """
    Query Dataverse using OData parameters.
    
    Args:
        client: DataverseClient instance
        table_name: Table schema name (e.g., "account", "contact")
        select: List of column names to select
        filter_expr: OData filter expression (e.g., "statecode eq 0")
        orderby: Order by expression (e.g., "createdon desc")
        top: Maximum number of results to return
        
    Returns:
        List of records as dictionaries
    """
    try:
        # Build query parameters
        kwargs = {"top": top}
        if select:
            kwargs["select"] = select
        if filter_expr:
            kwargs["filter"] = filter_expr
        if orderby:
            kwargs["orderby"] = orderby
        
        # Execute query - returns iterator of pages
        pages = client.get(table_name, **kwargs)
        
        # Collect all records from all pages
        all_records = []
        for page in pages:
            all_records.extend(page)
            # Limit to top parameter across all pages
            if len(all_records) >= top:
                all_records = all_records[:top]
                break
                
        return all_records
    except HttpError as e:
        print(f"HTTP Error {e.status_code}: {e.message}", file=sys.stderr)
        if e.code:
            print(f"Error code: {e.code}", file=sys.stderr)
        if e.is_transient:
            print("This error may be transient. Consider retrying.", file=sys.stderr)
        raise
    except ValidationError as e:
        print(f"Validation Error: {e.message}", file=sys.stderr)
        raise


def format_output(records: List[Dict[str, Any]], output_format: str = "json") -> str:
    """
    Format query results for output.
    
    Args:
        records: List of record dictionaries
        output_format: Output format ("json" or "table")
        
    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps(records, indent=2, default=str)
    elif output_format == "table":
        if not records:
            return "No records found"
        
        # Extract column names from first record
        columns = list(records[0].keys())
        
        # Build simple table
        lines = []
        # Header
        header = " | ".join(str(col) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for record in records:
            row = " | ".join(str(record.get(col, "")) for col in columns)
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
  # SQL query with interactive authentication
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --sql "SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0"
  
  # OData query with client secret authentication
  %(prog)s --environment-url https://org.crm.dynamics.com \\
    --tenant-id xxx --client-id xxx --client-secret xxx \\
    --table account --select name accountnumber --filter "statecode eq 0" --top 10
  
  # OData query with table output
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table contact --select fullname emailaddress1 --top 5 --format table
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
        help="Use interactive browser authentication (for devbox environments)",
    )
    parser.add_argument("--tenant-id", help="Azure AD tenant ID (for client secret auth)")
    parser.add_argument("--client-id", help="Azure AD app client ID (for client secret auth)")
    parser.add_argument("--client-secret", help="Azure AD app client secret (for client secret auth)")
    
    # Query parameters
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        "--sql",
        help='SQL query (e.g., "SELECT TOP 10 name FROM account WHERE statecode = 0")',
    )
    query_group.add_argument(
        "--table",
        help="Table name for OData query (e.g., account, contact)",
    )
    
    # OData parameters (only used with --table)
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
        help='Order by expression (e.g., "createdon desc")',
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Maximum number of results to return (default: 50)",
    )
    
    # Output options
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )
    
    args = parser.parse_args()
    
    try:
        # Create Dataverse client
        client = create_client(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )
        
        # Execute query
        if args.sql:
            print(f"Executing SQL query...", file=sys.stderr)
            records = query_sql(client, args.sql)
        else:
            print(f"Querying table: {args.table}...", file=sys.stderr)
            records = query_odata(
                client=client,
                table_name=args.table,
                select=args.select,
                filter_expr=args.filter,
                orderby=args.orderby,
                top=args.top,
            )
        
        # Format and output results
        output = format_output(records, args.format)
        print(output)
        
        print(f"\n--- {len(records)} record(s) returned ---", file=sys.stderr)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
