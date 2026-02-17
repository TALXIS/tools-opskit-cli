#!/usr/bin/env python3
"""Query Dataverse environment data using the Web API."""

import argparse
import json
import sys

import requests
from azure.identity import ClientSecretCredential


def get_access_token(tenant_id: str, client_id: str, client_secret: str, environment_url: str) -> str:
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = credential.get_token(f"{environment_url}/.default")
    return token.token


def query_odata(environment_url: str, token: str, query: str, top: int = 50) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    url = f"{environment_url.rstrip('/')}/api/data/v9.2/{query.lstrip('/')}"
    if top and "$top" not in query:
        separator = "&" if "?" in url else "?"
        url += f"{separator}$top={top}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def query_fetchxml(environment_url: str, token: str, fetchxml: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Content-Type": "application/json",
    }
    # Extract entity name from FetchXML for the URL
    import re
    match = re.search(r"<entity\s+name=['\"](\w+)['\"]", fetchxml)
    if not match:
        print("Error: Could not parse entity name from FetchXML", file=sys.stderr)
        sys.exit(1)
    entity_name = match.group(1)
    # Pluralize entity name (simple heuristic)
    entity_set = entity_name + "es" if entity_name.endswith("s") else entity_name + "s"

    url = f"{environment_url.rstrip('/')}/api/data/v9.2/{entity_set}"
    params = {"fetchXml": fetchxml}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Query Dataverse environment data")
    parser.add_argument("--environment-url", required=True, help="Dataverse environment URL")
    parser.add_argument("--tenant-id", required=True, help="Azure AD tenant ID")
    parser.add_argument("--client-id", required=True, help="Azure AD app client ID")
    parser.add_argument("--client-secret", required=True, help="Azure AD app client secret")
    parser.add_argument("--query", required=True, help="OData query string or FetchXML")
    parser.add_argument("--query-type", choices=["odata", "fetchxml"], default="odata", help="Query type")
    parser.add_argument("--top", type=int, default=50, help="Max results to return (OData only)")
    args = parser.parse_args()

    token = get_access_token(args.tenant_id, args.client_id, args.client_secret, args.environment_url)

    if args.query_type == "fetchxml":
        result = query_fetchxml(args.environment_url, token, args.query)
    else:
        result = query_odata(args.environment_url, token, args.query, args.top)

    records = result.get("value", [])
    print(json.dumps(records, indent=2, default=str))
    print(f"\n--- {len(records)} record(s) returned ---", file=sys.stderr)


if __name__ == "__main__":
    main()
