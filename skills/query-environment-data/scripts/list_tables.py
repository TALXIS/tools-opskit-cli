#!/usr/bin/env python3
"""List all tables in a Dataverse environment."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

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
    validate_auth_args,
)

from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def list_tables(client) -> List[Dict[str, str]]:
    """List all tables, returning name/schema/type info."""
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


def main():
    parser = argparse.ArgumentParser(
        description="List all tables in a Dataverse environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive

  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive --format table
        """,
    )

    add_auth_args(parser)
    add_output_args(parser)
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="Filter tables by logical name (case-insensitive substring match)",
    )

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

        print("Listing tables...", file=sys.stderr)
        tables = list_tables(client)
        if args.search:
            needle = args.search.lower()
            tables = [t for t in tables if needle in t.get("LogicalName", "").lower()]
        print(format_output(tables, args.format))
        print(f"\n--- {len(tables)} table(s) found ---", file=sys.stderr)

    except (HttpError, ValidationError) as e:
        print(f"Dataverse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
