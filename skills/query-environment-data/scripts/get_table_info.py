#!/usr/bin/env python3
"""Get table metadata and column names from a Dataverse environment."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.dataverse_helpers import (
    add_auth_args,
    add_output_args,
    check_dependencies,
    create_client,
    format_output,
    is_odata_annotation,
)

check_dependencies()

from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def get_table_columns(client, table_name: str) -> List[Dict[str, str]]:
    """Discover columns by querying a single record and returning column names.

    More reliable than the Attributes metadata endpoint because it returns
    the actual queryable column logical names.
    """
    try:
        pages = client.get(table_name, top=1)
        for page in pages:
            if page:
                return [
                    {"LogicalName": k}
                    for k in sorted(page[0].keys())
                    if not is_odata_annotation(k)
                ]
            break
    except (HttpError, ValidationError):
        pass
    return []


def main():
    parser = argparse.ArgumentParser(
        description="Get table metadata and column names from a Dataverse environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --table account

  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --table contact --format table
        """,
    )

    add_auth_args(parser)

    parser.add_argument(
        "--table",
        required=True,
        help="Table logical name (e.g., account, contact)",
    )

    add_output_args(parser)

    args = parser.parse_args()

    try:
        client = create_client(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )

        print(f"Getting info for table: {args.table}...", file=sys.stderr)
        info = client.get_table_info(args.table)
        if not info:
            print(f"Table '{args.table}' not found", file=sys.stderr)
            sys.exit(1)

        print("Discovering columns...", file=sys.stderr)
        columns = get_table_columns(client, args.table)
        info["columns"] = columns

        print(format_output(info, args.format))

    except (HttpError, ValidationError) as e:
        print(f"Dataverse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
