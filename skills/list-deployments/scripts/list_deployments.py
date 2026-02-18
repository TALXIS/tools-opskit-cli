#!/usr/bin/env python3
"""List recent deployments and their status.

This is a stub implementation. Replace the deployment data source with your
actual deployment tracking system (e.g., Azure DevOps Pipelines API,
a deployment database, or configuration management tool).
"""

import argparse
import json
import sys
from pathlib import Path

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.preflight import require_provider


# Stub: In production, replace with actual deployment tracking data source
DEPLOYMENT_STORE = {
    # Example structure — replace with real implementation
    # "12345": {
    #     "id": "12345",
    #     "customer": "customer-abc",
    #     "environment": "production",
    #     "status": "succeeded",
    #     "started_at": "2024-01-15T10:30:00Z",
    #     "completed_at": "2024-01-15T10:45:00Z",
    #     "duration_minutes": 15,
    #     "triggered_by": "user@company.com",
    #     "pipeline": "Release-Production",
    #     "solutions": ["CoreSolution", "CustomPlugin"],
    #     "error": None,
    # },
}


def list_deployments(customer: str = None, environment: str = None, status: str = None, top: int = 10):
    results = []
    for dep_id, dep in DEPLOYMENT_STORE.items():
        if customer and dep.get("customer") != customer:
            continue
        if environment and dep.get("environment") != environment:
            continue
        if status and dep.get("status") != status:
            continue
        results.append(dep)
    # Sort by started_at descending
    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    results = results[:top]
    print(json.dumps(results, indent=2))
    print(f"\n--- {len(results)} deployment(s) ---", file=sys.stderr)


def get_deployment_details(deployment_id: str):
    if deployment_id not in DEPLOYMENT_STORE:
        print(f"Error: Deployment '{deployment_id}' not found.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(DEPLOYMENT_STORE[deployment_id], indent=2))


def main():
    parser = argparse.ArgumentParser(description="List recent deployments and their status")
    parser.add_argument("--action", required=True, choices=["list", "details"], help="Action to perform")
    parser.add_argument("--customer", help="Filter by customer")
    parser.add_argument("--environment", help="Filter by environment")
    parser.add_argument("--status", help="Filter by status (succeeded, failed, in-progress, cancelled)")
    parser.add_argument("--deployment-id", help="Deployment ID (for details)")
    parser.add_argument("--top", type=int, default=10, help="Max results to return")
    args = parser.parse_args()

    require_provider("ado")

    if args.action == "list":
        list_deployments(args.customer, args.environment, args.status, args.top)
    elif args.action == "details":
        if not args.deployment_id:
            print("Error: --deployment-id is required for details", file=sys.stderr)
            sys.exit(1)
        get_deployment_details(args.deployment_id)


if __name__ == "__main__":
    main()
