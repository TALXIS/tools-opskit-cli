#!/usr/bin/env python3
"""Query environment logs from Power Platform / Dataverse."""

import argparse
import json
import sys

import requests
from azure.identity import ClientSecretCredential


def get_access_token(tenant_id: str, client_id: str, client_secret: str, environment_url: str) -> str:
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = credential.get_token(f"{environment_url}/.default")
    return token.token


def query_api(environment_url: str, token: str, endpoint: str, params: dict = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    url = f"{environment_url.rstrip('/')}/api/data/v9.2/{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def query_plugin_traces(environment_url: str, token: str, since: str = None, top: int = 50) -> list:
    filters = []
    if since:
        filters.append(f"performanceexecutionstarttime ge {since}")
    filter_str = " and ".join(filters)
    endpoint = f"plugintracelogs?$top={top}&$orderby=performanceexecutionstarttime desc"
    if filter_str:
        endpoint += f"&$filter={filter_str}"
    result = query_api(environment_url, token, endpoint)
    return result.get("value", [])


def query_audit_logs(environment_url: str, token: str, entity: str = None, since: str = None, top: int = 50) -> list:
    filters = []
    if since:
        filters.append(f"createdon ge {since}")
    if entity:
        filters.append(f"objecttypecode eq '{entity}'")
    filter_str = " and ".join(filters)
    endpoint = f"audits?$top={top}&$orderby=createdon desc"
    if filter_str:
        endpoint += f"&$filter={filter_str}"
    result = query_api(environment_url, token, endpoint)
    return result.get("value", [])


def query_flow_runs(environment_url: str, token: str, status: str = None, top: int = 50) -> list:
    filters = []
    if status:
        filters.append(f"status eq '{status}'")
    filter_str = " and ".join(filters)
    endpoint = f"flowsessions?$top={top}&$orderby=createdon desc"
    if filter_str:
        endpoint += f"&$filter={filter_str}"
    result = query_api(environment_url, token, endpoint)
    return result.get("value", [])


def query_system_jobs(environment_url: str, token: str, status: str = None, top: int = 50) -> list:
    filters = []
    if status == "failed":
        filters.append("statuscode eq 31")  # 31 = Failed
    filter_str = " and ".join(filters)
    endpoint = f"asyncoperations?$top={top}&$orderby=createdon desc"
    if filter_str:
        endpoint += f"&$filter={filter_str}"
    result = query_api(environment_url, token, endpoint)
    return result.get("value", [])


def main():
    parser = argparse.ArgumentParser(description="Query environment logs")
    parser.add_argument("--environment-url", required=True, help="Dataverse environment URL")
    parser.add_argument("--tenant-id", required=True, help="Azure AD tenant ID")
    parser.add_argument("--client-id", required=True, help="Azure AD app client ID")
    parser.add_argument("--client-secret", required=True, help="Azure AD app client secret")
    parser.add_argument("--log-type", required=True, choices=["plugin-trace", "audit", "flow-runs", "system-jobs"], help="Type of logs to query")
    parser.add_argument("--since", help="Filter logs after this ISO 8601 timestamp")
    parser.add_argument("--entity", help="Entity logical name (audit logs only)")
    parser.add_argument("--status", help="Filter by status (e.g., 'failed')")
    parser.add_argument("--top", type=int, default=50, help="Max results to return")
    args = parser.parse_args()

    token = get_access_token(args.tenant_id, args.client_id, args.client_secret, args.environment_url)

    if args.log_type == "plugin-trace":
        records = query_plugin_traces(args.environment_url, token, args.since, args.top)
    elif args.log_type == "audit":
        records = query_audit_logs(args.environment_url, token, args.entity, args.since, args.top)
    elif args.log_type == "flow-runs":
        records = query_flow_runs(args.environment_url, token, args.status, args.top)
    elif args.log_type == "system-jobs":
        records = query_system_jobs(args.environment_url, token, args.status, args.top)
    else:
        records = []

    print(json.dumps(records, indent=2, default=str))
    print(f"\n--- {len(records)} record(s) returned ---", file=sys.stderr)


if __name__ == "__main__":
    main()
