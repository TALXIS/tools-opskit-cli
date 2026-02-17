#!/usr/bin/env python3
"""Retrieve a Power Automate flow definition (triggers, actions, expressions, connections).

Tries the Flow Management API first, falls back to Dataverse workflow.clientdata.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.dataverse_helpers import _ensure_venv
_ensure_venv()
from _shared.preflight import require_provider

require_provider("dataverse")

from _shared.dataverse_helpers import (
    add_auth_args,
    add_output_args,
    create_credential,
    format_output,
    validate_auth_args,
)
from _shared.flow_helpers import (
    discover_flow_api_base,
    get_flow_definition,
    get_flow_definition_from_dataverse,
    resolve_environment_id,
    resolve_flow_id,
)

from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError


def _format_definition(defn_response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the relevant parts of a flow definition response."""
    props = defn_response.get("properties", {})
    return {
        "displayName": props.get("displayName", ""),
        "state": props.get("state", ""),
        "createdTime": props.get("createdTime", ""),
        "lastModifiedTime": props.get("lastModifiedTime", ""),
        "connectionReferences": props.get("connectionReferences", {}),
        "definition": props.get("definition", {}),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve a flow definition (triggers, actions, expressions, connections)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get flow definition by name
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --flow-name my_flow

  # Get flow definition by Dataverse workflowid
  %(prog)s --environment-url https://org.crm4.dynamics.com --interactive \\
    --flow-id 00000000-0000-0000-0000-000000000000
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

    add_output_args(parser)

    args = parser.parse_args()
    validate_auth_args(args)

    try:
        credential = create_credential(
            environment_url=args.environment_url,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            interactive=args.interactive,
        )
        client = DataverseClient(args.environment_url, credential)

        # Resolve flow identity
        if args.flow_name:
            print(f"Resolving flow '{args.flow_name}'...", file=sys.stderr)
            flow_info = resolve_flow_id(client, flow_name=args.flow_name)
        else:
            print(f"Resolving flow ID '{args.flow_id}'...", file=sys.stderr)
            flow_info = resolve_flow_id(client, workflow_id=args.flow_id)

        print(
            f"  Flow: {flow_info['name']} (workflowid={flow_info['workflowid']}, "
            f"resourceid={flow_info['resourceid']})",
            file=sys.stderr,
        )

        # Try Flow API first
        try:
            print("Discovering Flow API endpoint...", file=sys.stderr)
            flow_api_base = discover_flow_api_base(credential, args.environment_url)
            env_id = resolve_environment_id(credential, args.environment_url)
            if not env_id:
                raise ValueError("Could not resolve environment ID")

            print("Getting flow definition via Flow Management API...", file=sys.stderr)
            defn_resp = get_flow_definition(
                credential, flow_api_base, env_id, flow_info["resourceid"],
            )
            output = _format_definition(defn_resp)
            print(format_output(output, args.format))
            action_count = len(output.get("definition", {}).get("actions", {}))
            trigger_count = len(output.get("definition", {}).get("triggers", {}))
            print(f"\n--- {trigger_count} trigger(s), {action_count} action(s) ---", file=sys.stderr)
            return
        except Exception as e:
            print(f"  Flow API failed ({e}), trying Dataverse fallback...", file=sys.stderr)

        # Fallback: Dataverse workflow.clientdata
        print("Getting flow definition from Dataverse clientdata...", file=sys.stderr)
        clientdata = get_flow_definition_from_dataverse(client, flow_info["workflowid"])
        if clientdata:
            props = clientdata.get("properties", {})
            output = {
                "displayName": flow_info["name"],
                "source": "dataverse_clientdata",
                "connectionReferences": props.get("connectionReferences", {}),
                "definition": props.get("definition", {}),
            }
            print(format_output(output, args.format))
            action_count = len(output.get("definition", {}).get("actions", {}))
            print(f"\n--- {action_count} action(s) (from Dataverse fallback) ---", file=sys.stderr)
        else:
            print("Error: Could not retrieve flow definition from either source.", file=sys.stderr)
            sys.exit(1)

    except (HttpError, ValidationError) as e:
        print(f"Dataverse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
