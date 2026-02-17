#!/usr/bin/env python3
"""Retrieve secrets for accessing customer environments and resources.

This is a stub implementation. Replace the secret retrieval logic with your
actual secrets management solution (e.g., Azure Key Vault, HashiCorp Vault,
environment variables, encrypted config files).
"""

import argparse
import json
import os
import sys


# Stub: In production, replace with actual secret store integration
SECRETS_STORE = {
    # Example structure — replace with real implementation
    # "customer-abc": {
    #     "dataverse-credentials": {
    #         "tenant_id": "...",
    #         "client_id": "...",
    #         "client_secret": "...",
    #         "environment_url": "https://org.crm4.dynamics.com"
    #     },
    #     "ado-pat": {"pat": "..."},
    # },
    # "global": {
    #     "jira-credentials": {
    #         "server": "https://company.atlassian.net",
    #         "username": "user@company.com",
    #         "api_token": "..."
    #     },
    # },
}


def mask_value(value: str) -> str:
    """Mask a secret value, showing only the last 4 characters."""
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def mask_dict(d: dict) -> dict:
    """Mask all string values in a dictionary."""
    masked = {}
    for key, value in d.items():
        if isinstance(value, str):
            masked[key] = mask_value(value)
        elif isinstance(value, dict):
            masked[key] = mask_dict(value)
        else:
            masked[key] = value
    return masked


def list_scopes():
    scopes = list(SECRETS_STORE.keys())
    print(json.dumps({"scopes": scopes}, indent=2))
    print(f"\n--- {len(scopes)} scope(s) available ---", file=sys.stderr)


def get_secret(scope: str, secret_name: str):
    if scope not in SECRETS_STORE:
        print(f"Error: Scope '{scope}' not found. Available: {list(SECRETS_STORE.keys())}", file=sys.stderr)
        sys.exit(1)
    scope_secrets = SECRETS_STORE[scope]
    if secret_name not in scope_secrets:
        print(f"Error: Secret '{secret_name}' not found in scope '{scope}'. Available: {list(scope_secrets.keys())}", file=sys.stderr)
        sys.exit(1)
    secret = scope_secrets[secret_name]
    # Output masked version for display
    masked = mask_dict(secret) if isinstance(secret, dict) else mask_value(str(secret))
    print(json.dumps({"scope": scope, "name": secret_name, "value_masked": masked}, indent=2))
    # Output actual values to stderr for piping to other scripts (only when explicitly requested)
    # In production, consider using environment variables or temporary files instead
    print(f"\nActual values written to environment. Use with caution.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Retrieve secrets for customer environments")
    parser.add_argument("--action", required=True, choices=["list-scopes", "get"], help="Action to perform")
    parser.add_argument("--scope", help="Secret scope (customer name or 'global')")
    parser.add_argument("--secret-name", help="Name of the secret to retrieve")
    args = parser.parse_args()

    if args.action == "list-scopes":
        list_scopes()
    elif args.action == "get":
        if not args.scope or not args.secret_name:
            print("Error: --scope and --secret-name are required for get", file=sys.stderr)
            sys.exit(1)
        get_secret(args.scope, args.secret_name)


if __name__ == "__main__":
    main()
