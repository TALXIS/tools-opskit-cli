#!/usr/bin/env python3
"""Query flow runs via the Power Automate Flow Management API.

Two modes:
- Without --run-id: list recent runs with status, error summaries, and trigger info.
- With --run-id:    get a single run with per-action detail (status, errors, timing).
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.dataverse_helpers import (
    add_auth_args,
    add_output_args,
    check_dependencies,
    create_credential,
    format_output,
)
from _shared.flow_helpers import (
    discover_flow_api_base,
    get_flow_run_with_actions,
    list_flow_runs,
    resolve_environment_id,
    resolve_flow_id,
)

check_dependencies()

from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def _resolve_flow_context(client, credential, environment_url: str,
                          flow_name=None, flow_id=None) -> Dict[str, str]:
    """Resolve flow identity + Flow API endpoint + environment ID."""
    if flow_name:
        print(f"Resolving flow '{flow_name}'...", file=sys.stderr)
        flow_info = resolve_flow_id(client, flow_name=flow_name)
    else:
        print(f"Resolving flow ID '{flow_id}'...", file=sys.stderr)
        flow_info = resolve_flow_id(client, workflow_id=flow_id)

    print(
        f"  Flow: {flow_info['name']} (workflowid={flow_info['workflowid']}, "
        f"resourceid={flow_info['resourceid']})",
        file=sys.stderr,
    )

    print("Discovering Flow API endpoint...", file=sys.stderr)
    flow_api_base = discover_flow_api_base(credential, environment_url)
    env_id = resolve_environment_id(credential, environment_url)
    if not env_id:
        raise ValueError(
            "Could not resolve Power Platform environment ID. "
            "Ensure you have access to the BAP admin API."
        )

    return {
        "flow_resource_id": flow_info["resourceid"],
        "flow_name": flow_info["name"],
        "environment_id": env_id,
        "flow_api_base": flow_api_base,
    }


def _format_run_actions(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and format action details from an expanded flow run."""
    actions = run.get("properties", {}).get("actions", {})
    result = []
    for name, action in sorted(actions.items()):
        entry: Dict[str, Any] = {
            "action": name,
            "status": action.get("status", ""),
            "code": action.get("code", ""),
            "startTime": action.get("startTime", ""),
            "endTime": action.get("endTime", ""),
        }
        error = action.get("error")
        if error:
            entry["error_code"] = error.get("code", "")
            entry["error_message"] = error.get("message", "")
        if action.get("repetitionCount"):
            entry["repetitionCount"] = action["repetitionCount"]
        result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Query flow runs via the Flow Management API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List recent failed runs with error summaries
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --flow-name my_flow --status failed --top 5

  # Action-level detail for a specific run
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --flow-name my_flow --run-id 08585000000000000000000000000CU100

  # Use flow ID instead of name
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --flow-id 00000000-0000-0000-0000-000000000000 --status failed --top 3
        """,
    )

    add_auth_args(parser)

    flow_group = parser.add_mutually_exclusive_group(required=True)
    flow_group.add_argument(
        "--flow-name",
        help="Flow display name (resolved via Dataverse workflow table)",
    )
    flow_group.add_argument(
        "--flow-id",
        help="Dataverse workflowid GUID",
    )

    parser.add_argument(
        "--run-id",
        help="Specific run ID for action-level detail (logic app run ID from flowrun.name)",
    )
    parser.add_argument(
        "--status",
        help="Filter by status (e.g., 'failed', 'succeeded')",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of runs to return when listing (default: 10)",
    )

    add_output_args(parser)

    args = parser.parse_args()

    try:
        credential = create_credential(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )
        client = DataverseClient(args.environment_url, credential)

        ctx = _resolve_flow_context(
            client, credential, args.environment_url,
            flow_name=args.flow_name, flow_id=args.flow_id,
        )

        if args.run_id:
            print(f"Getting run {args.run_id} with action details...", file=sys.stderr)
            run = get_flow_run_with_actions(
                credential, ctx["flow_api_base"], ctx["environment_id"],
                ctx["flow_resource_id"], args.run_id,
            )
            actions = _format_run_actions(run)
            props = run.get("properties", {})
            output = {
                "run_id": args.run_id,
                "status": props.get("status", ""),
                "error": props.get("error", {}),
                "trigger": props.get("trigger", {}).get("name", ""),
                "startTime": props.get("startTime", ""),
                "endTime": props.get("endTime", ""),
                "actions": actions,
            }
            print(format_output(output, args.format))
            failed = [a for a in actions if a["status"] == "Failed"]
            print(f"\n--- {len(actions)} action(s), {len(failed)} failed ---", file=sys.stderr)
        else:
            status_filter = args.status.capitalize() if args.status else None
            print(f"Listing recent runs (top {args.top})...", file=sys.stderr)
            runs = list_flow_runs(
                credential, ctx["flow_api_base"], ctx["environment_id"],
                ctx["flow_resource_id"], top=args.top, status_filter=status_filter,
            )
            results = []
            for run in runs:
                props = run.get("properties", {})
                results.append({
                    "run_id": run.get("name", ""),
                    "status": props.get("status", ""),
                    "error_code": props.get("error", {}).get("code", ""),
                    "error_message": props.get("error", {}).get("message", ""),
                    "startTime": props.get("startTime", ""),
                    "endTime": props.get("endTime", ""),
                    "trigger": props.get("trigger", {}).get("name", ""),
                })
            print(format_output(results, args.format))
            print(f"\n--- {len(results)} run(s) returned ---", file=sys.stderr)

    except (HttpError, ValidationError) as e:
        print(f"Dataverse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
