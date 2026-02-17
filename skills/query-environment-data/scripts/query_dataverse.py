#!/usr/bin/env python3
"""Query Dataverse environment data using SQL or OData."""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.dataverse_helpers import _ensure_venv
_ensure_venv()
from _shared.preflight import require_provider

require_provider("dataverse")

from _shared.dataverse_helpers import (
    add_auth_args,
    add_output_args,
    create_client,
    format_output,
    query_odata,
    strip_annotations,
    validate_auth_args,
)

from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def query_sql(
    client, sql_query: str, include_annotations: bool = False
) -> List[Dict[str, Any]]:
    """Execute a read-only SQL query against Dataverse."""
    results = client.query_sql(sql_query)
    if include_annotations:
        return list(results)
    return [strip_annotations(r) for r in results]


def main():
    parser = argparse.ArgumentParser(
        description="Query Dataverse environment data using SQL or OData",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SQL query
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --sql "SELECT TOP 10 name, accountnumber FROM account WHERE statecode = 0"

  # OData query with filter and limit
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table account --select name accountnumber --filter "statecode eq 0" --top 10

  # OData query with ordering
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table contact --select fullname emailaddress1 --orderby "createdon desc" --top 10

  # Table output format
  %(prog)s --environment-url https://org.crm.dynamics.com --interactive \\
    --table contact --select fullname emailaddress1 --top 5 --format table
        """,
    )

    add_auth_args(parser)

    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        "--sql",
        help='SQL query (e.g., "SELECT TOP 10 name FROM account WHERE statecode = 0")',
    )
    query_group.add_argument(
        "--table",
        help="Table name for OData query (e.g., account, contact)",
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

    add_output_args(parser)

    args = parser.parse_args()
    validate_auth_args(args)

    try:
        client = create_client(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )

        if args.sql:
            print("Executing SQL query...", file=sys.stderr)
            records = query_sql(client, args.sql, args.include_annotations)
        else:
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

        print(format_output(records, args.format))
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
