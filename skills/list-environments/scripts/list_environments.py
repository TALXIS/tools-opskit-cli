#!/usr/bin/env python3
"""List customer environments, tenants, and their details.

This is a stub implementation. Replace the environment registry logic with your
actual data source (e.g., a database, configuration file, or management API).
"""

import argparse
import json
import sys


# Stub: In production, replace with actual environment registry
ENVIRONMENT_REGISTRY = {
    # Example structure — replace with real implementation
    # "customer-abc": {
    #     "display_name": "Customer ABC Corp",
    #     "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    #     "tenant_domain": "customerabc.onmicrosoft.com",
    #     "environments": {
    #         "production": {
    #             "url": "https://customerabc.crm4.dynamics.com",
    #             "type": "production",
    #             "region": "Europe",
    #             "status": "active",
    #         },
    #         "sandbox": {
    #             "url": "https://customerabc-sandbox.crm4.dynamics.com",
    #             "type": "sandbox",
    #             "region": "Europe",
    #             "status": "active",
    #         },
    #     },
    # },
}


def list_customers():
    results = []
    for key, data in ENVIRONMENT_REGISTRY.items():
        results.append({
            "id": key,
            "display_name": data.get("display_name", key),
            "tenant_domain": data.get("tenant_domain", ""),
            "environment_count": len(data.get("environments", {})),
        })
    print(json.dumps(results, indent=2))
    print(f"\n--- {len(results)} customer(s) ---", file=sys.stderr)


def list_environments(customer: str):
    if customer not in ENVIRONMENT_REGISTRY:
        print(f"Error: Customer '{customer}' not found. Available: {list(ENVIRONMENT_REGISTRY.keys())}", file=sys.stderr)
        sys.exit(1)
    customer_data = ENVIRONMENT_REGISTRY[customer]
    envs = customer_data.get("environments", {})
    results = []
    for name, env in envs.items():
        results.append({
            "name": name,
            "url": env.get("url", ""),
            "type": env.get("type", ""),
            "region": env.get("region", ""),
            "status": env.get("status", ""),
        })
    print(json.dumps({
        "customer": customer,
        "display_name": customer_data.get("display_name", customer),
        "tenant_id": customer_data.get("tenant_id", ""),
        "tenant_domain": customer_data.get("tenant_domain", ""),
        "environments": results,
    }, indent=2))
    print(f"\n--- {len(results)} environment(s) ---", file=sys.stderr)


def get_environment_details(customer: str, environment: str):
    if customer not in ENVIRONMENT_REGISTRY:
        print(f"Error: Customer '{customer}' not found.", file=sys.stderr)
        sys.exit(1)
    envs = ENVIRONMENT_REGISTRY[customer].get("environments", {})
    if environment not in envs:
        print(f"Error: Environment '{environment}' not found for '{customer}'. Available: {list(envs.keys())}", file=sys.stderr)
        sys.exit(1)
    env = envs[environment]
    print(json.dumps({
        "customer": customer,
        "environment": environment,
        **env,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="List customer environments and tenants")
    parser.add_argument("--action", required=True, choices=["list-customers", "list", "details"], help="Action to perform")
    parser.add_argument("--customer", help="Customer identifier")
    parser.add_argument("--environment", help="Environment name (for details)")
    args = parser.parse_args()

    if args.action == "list-customers":
        list_customers()
    elif args.action == "list":
        if not args.customer:
            print("Error: --customer is required for list", file=sys.stderr)
            sys.exit(1)
        list_environments(args.customer)
    elif args.action == "details":
        if not args.customer or not args.environment:
            print("Error: --customer and --environment are required for details", file=sys.stderr)
            sys.exit(1)
        get_environment_details(args.customer, args.environment)


if __name__ == "__main__":
    main()
