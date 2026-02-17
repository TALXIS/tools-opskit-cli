#!/usr/bin/env python3
"""Query Dataverse log tables via OData.

Supports four log types:
- flow-runs:     Cloud flow execution history (flowrun, elastic table)
- plugin-trace:  Plugin/workflow activity trace logs (plugintracelog)
- audit:         Entity change audit trail (audit)
- system-jobs:   Background system job status and errors (asyncoperation)
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    validate_auth_args,
)

from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


LOG_TYPES: Dict[str, Dict[str, Any]] = {
    "flow-runs": {
        "table": "flowrun",
        "select": [
            "name", "status", "starttime", "endtime", "duration",
            "errorcode", "errormessage", "triggertype", "workflowid",
        ],
        "orderby": ["starttime desc"],
        "since_column": "starttime",
        "status_map": {
            "failed": "status eq 'Failed'",
            "succeeded": "status eq 'Succeeded'",
            "cancelled": "status eq 'Cancelled'",
        },
    },
    "plugin-trace": {
        "table": "plugintracelog",
        "select": [
            "typename", "messagename", "primaryentity", "exceptiondetails",
            "messageblock", "performanceexecutionstarttime",
            "performanceexecutionduration", "depth", "operationtype",
            "mode", "correlationid",
        ],
        "orderby": ["performanceexecutionstarttime desc"],
        "since_column": "performanceexecutionstarttime",
        "status_map": {},
    },
    "audit": {
        "table": "audit",
        "select": [
            "action", "operation", "objecttypecode", "createdon",
            "changedata", "_userid_value", "_objectid_value",
        ],
        "orderby": ["createdon desc"],
        "since_column": "createdon",
        "status_map": {},
    },
    "system-jobs": {
        "table": "asyncoperation",
        "select": [
            "name", "operationtype", "statuscode", "createdon",
            "startedon", "completedon", "message", "friendlymessage",
        ],
        "orderby": ["createdon desc"],
        "since_column": "createdon",
        "status_map": {
            "failed": "statuscode eq 31",
            "succeeded": "statuscode eq 30",
            "waiting": "statuscode eq 10",
            "in-progress": "statuscode eq 20",
            "cancelled": "statuscode eq 32",
        },
    },
}


def build_filter(
    log_type: str,
    since: Optional[str] = None,
    status: Optional[str] = None,
    entity: Optional[str] = None,
    custom_filter: Optional[str] = None,
) -> Optional[str]:
    """Build an OData filter expression from convenience parameters."""
    if custom_filter:
        return custom_filter

    config = LOG_TYPES[log_type]
    parts: List[str] = []

    if since:
        parts.append(f"{config['since_column']} ge {since}")

    if status:
        status_lower = status.lower()
        status_expr = config["status_map"].get(status_lower)
        if status_expr:
            parts.append(status_expr)
        else:
            valid = ", ".join(config["status_map"].keys()) or "(none available)"
            print(
                f"Warning: Unknown status '{status}' for {log_type}. "
                f"Valid values: {valid}. Using as raw filter.",
                file=sys.stderr,
            )
            parts.append(status)

    if entity and log_type == "audit":
        parts.append(f"objecttypecode eq '{entity}'")

    return " and ".join(parts) if parts else None


def main():
    parser = argparse.ArgumentParser(
        description="Query Dataverse log tables (flow-runs, plugin-trace, audit, system-jobs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Recent failed flow runs
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --log-type flow-runs --status failed --top 20

  # Plugin traces since a date
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --log-type plugin-trace --since 2025-01-01T00:00:00Z --top 50

  # Audit logs for a specific entity
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --log-type audit --entity account --top 20

  # Failed system jobs
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --log-type system-jobs --status failed --top 10

  # Custom OData filter
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --log-type flow-runs --filter "status eq 'Failed' and triggertype eq 'Automated'"
        """,
    )

    add_auth_args(parser)

    parser.add_argument(
        "--log-type",
        required=True,
        choices=list(LOG_TYPES.keys()),
        help="Type of logs to query",
    )
    parser.add_argument(
        "--since",
        help="Filter logs after this ISO 8601 timestamp (e.g., 2025-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--status",
        help="Filter by status (e.g., 'failed', 'succeeded'). Valid values depend on log type.",
    )
    parser.add_argument(
        "--entity",
        help="Entity logical name filter (audit logs only, e.g., 'account')",
    )
    parser.add_argument(
        "--filter",
        help="Raw OData filter expression (overrides --since, --status, --entity)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Maximum number of results to return (default: 50)",
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

        config = LOG_TYPES[args.log_type]
        filter_expr = build_filter(
            log_type=args.log_type,
            since=args.since,
            status=args.status,
            entity=args.entity,
            custom_filter=args.filter,
        )

        print(f"Querying {args.log_type} ({config['table']})...", file=sys.stderr)
        records = query_odata(
            client=client,
            table_name=config["table"],
            select=config["select"],
            filter_expr=filter_expr,
            orderby=config["orderby"],
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
