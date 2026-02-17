"""Helpers for the Power Automate Flow Management API.

Provides functions to:
- Acquire tokens for the Flow API and BAP API
- Discover the regional Flow API endpoint for an environment
- Resolve Dataverse workflow IDs to Flow API resource IDs
- Query flow runs with action-level detail
- Retrieve flow definitions
"""

import json
import sys
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, quote

# CRM region domain → Flow API region prefix
_CRM_DOMAIN_TO_FLOW_REGION = {
    "crm.dynamics.com": "us",           # North America
    "crm2.dynamics.com": "us",          # South America
    "crm3.dynamics.com": "us",          # Canada
    "crm4.dynamics.com": "emea",        # Europe
    "crm5.dynamics.com": "asia",        # Asia Pacific
    "crm6.dynamics.com": "japan",       # Japan
    "crm7.dynamics.com": "japan",       # Japan
    "crm8.dynamics.com": "india",       # India
    "crm9.dynamics.com": "gov",         # US Gov
    "crm11.dynamics.com": "uk",         # UK
    "crm12.dynamics.com": "fr",         # France
    "crm14.dynamics.com": "za",         # South Africa
    "crm15.dynamics.com": "uae",        # UAE
    "crm16.dynamics.com": "de",         # Germany
    "crm17.dynamics.com": "che",        # Switzerland
    "crm19.dynamics.com": "kor",        # Korea
    "crm20.dynamics.com": "no",         # Norway
    "crm21.dynamics.com": "sg",         # Singapore
}

FLOW_API_RESOURCE = "https://service.flow.microsoft.com"
BAP_API_RESOURCE = "https://api.bap.microsoft.com"
FLOW_API_VERSION = "2016-11-01"


def get_flow_token(credential) -> str:
    """Acquire a token for the Flow Management API."""
    token = credential.get_token(f"{FLOW_API_RESOURCE}/.default")
    return token.token


def get_bap_token(credential) -> str:
    """Acquire a token for the Business Application Platform API."""
    token = credential.get_token(f"{BAP_API_RESOURCE}/.default")
    return token.token


def _api_get(url: str, token: str) -> Any:
    """Make an authenticated GET request and return parsed JSON."""
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except (json.JSONDecodeError, AttributeError):
            msg = body
        raise RuntimeError(f"Flow API error ({e.code}): {msg}") from e


def _find_environment(credential, environment_url: str) -> Optional[Dict[str, Any]]:
    """Find a BAP environment record matching the given Dataverse URL.

    Returns the full environment dict from the BAP API, or None.
    Result is cached on the credential object to avoid duplicate calls.
    """
    cache_key = "_bap_env_cache"
    cache = getattr(credential, cache_key, {})
    env_url_lower = environment_url.rstrip("/").lower()

    if env_url_lower in cache:
        return cache[env_url_lower]

    try:
        bap_token = get_bap_token(credential)
        envs = _api_get(
            f"{BAP_API_RESOURCE}/providers/Microsoft.BusinessAppPlatform"
            f"/scopes/admin/environments?api-version=2020-10-01",
            bap_token,
        )
        # Cache all discovered environments
        for env in envs.get("value", []):
            meta = env.get("properties", {}).get("linkedEnvironmentMetadata", {})
            instance_url = (meta.get("instanceUrl") or "").rstrip("/").lower()
            if instance_url:
                cache[instance_url] = env
        setattr(credential, cache_key, cache)
    except Exception as e:
        print(f"  BAP API lookup failed: {e}", file=sys.stderr)
        setattr(credential, cache_key, cache)

    return cache.get(env_url_lower)


def discover_flow_api_base(credential, environment_url: str) -> str:
    """Discover the regional Flow API base URL for an environment.

    Tries two strategies:
    1. BAP API lookup (authoritative, requires api.bap.microsoft.com token)
    2. CRM domain heuristic fallback (no extra token needed)
    """
    env = _find_environment(credential, environment_url)
    if env:
        endpoints = env["properties"].get("runtimeEndpoints", {})
        flow_base = endpoints.get("microsoft.Flow")
        if flow_base:
            print(f"  Flow API: {flow_base} (via BAP discovery)", file=sys.stderr)
            return flow_base.rstrip("/")

    # CRM domain heuristic fallback
    from urllib.parse import urlparse
    host = urlparse(environment_url).hostname or ""
    for domain, region in _CRM_DOMAIN_TO_FLOW_REGION.items():
        if host.endswith(domain):
            base = f"https://{region}.api.flow.microsoft.com"
            print(f"  Flow API: {base} (heuristic from {domain})", file=sys.stderr)
            return base

    base = "https://api.flow.microsoft.com"
    print(f"  Flow API: {base} (default fallback)", file=sys.stderr)
    return base


def resolve_environment_id(credential, environment_url: str) -> Optional[str]:
    """Resolve the Power Platform environment ID from a Dataverse URL."""
    env = _find_environment(credential, environment_url)
    return env["name"] if env else None


def resolve_flow_id(client, flow_name: Optional[str] = None, workflow_id: Optional[str] = None) -> Dict[str, str]:
    """Resolve a flow name or Dataverse workflowid to the Flow API resourceid.

    Returns dict with keys: workflowid, resourceid, name
    """
    from _shared.dataverse_helpers import query_odata

    if flow_name:
        filter_expr = f"name eq '{flow_name}' and category eq 5"
    elif workflow_id:
        filter_expr = f"workflowid eq {workflow_id} and category eq 5"
    else:
        raise ValueError("Either flow_name or workflow_id is required")

    records = query_odata(
        client, "workflow",
        select=["workflowid", "resourceid", "name"],
        filter_expr=filter_expr,
        top=1,
    )
    if not records:
        raise ValueError(f"No cloud flow found matching filter: {filter_expr}")

    rec = records[0]
    return {
        "workflowid": rec["workflowid"],
        "resourceid": rec["resourceid"],
        "name": rec["name"],
    }


def get_flow_run_with_actions(
    credential,
    flow_api_base: str,
    environment_id: str,
    flow_resource_id: str,
    run_id: str,
) -> Dict[str, Any]:
    """Get a single flow run with expanded action details.

    Returns the full run object including properties.actions with per-action
    status, error codes, error messages, and input/output links.
    """
    flow_token = get_flow_token(credential)
    url = (
        f"{flow_api_base}/providers/Microsoft.ProcessSimple"
        f"/environments/{environment_id}"
        f"/flows/{flow_resource_id}"
        f"/runs/{quote(run_id, safe='')}"
        f"?$expand=properties/actions,properties/flow"
        f"&api-version={FLOW_API_VERSION}"
        f"&include=repetitionCount&isMigrationSource=false"
    )
    return _api_get(url, flow_token)


def list_flow_runs(
    credential,
    flow_api_base: str,
    environment_id: str,
    flow_resource_id: str,
    top: int = 10,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List flow runs via the Flow Management API.

    Returns runs with trigger info, status, error summaries (no action detail).
    """
    flow_token = get_flow_token(credential)
    params: Dict[str, str] = {"api-version": FLOW_API_VERSION, "$top": str(top)}
    if status_filter:
        params["$filter"] = f"status eq '{status_filter}'"
    url = (
        f"{flow_api_base}/providers/Microsoft.ProcessSimple"
        f"/environments/{environment_id}"
        f"/flows/{flow_resource_id}"
        f"/runs?{urlencode(params)}"
    )
    data = _api_get(url, flow_token)
    return data.get("value", [])


def get_flow_definition(
    credential,
    flow_api_base: str,
    environment_id: str,
    flow_resource_id: str,
) -> Dict[str, Any]:
    """Get a flow's definition (triggers, actions, parameters) via the Flow Management API.

    Returns the full flow object with properties.definition containing
    the Logic Apps workflow JSON.
    """
    flow_token = get_flow_token(credential)
    url = (
        f"{flow_api_base}/providers/Microsoft.ProcessSimple"
        f"/environments/{environment_id}"
        f"/flows/{flow_resource_id}"
        f"?api-version={FLOW_API_VERSION}"
        f"&$expand=operationDefinition"
    )
    return _api_get(url, flow_token)


def get_flow_definition_from_dataverse(client, workflow_id: str) -> Optional[Dict[str, Any]]:
    """Fallback: get flow definition from Dataverse workflow.clientdata field."""
    from _shared.dataverse_helpers import query_odata

    records = query_odata(
        client, "workflow",
        select=["clientdata"],
        filter_expr=f"workflowid eq {workflow_id}",
        top=1,
    )
    if not records or not records[0].get("clientdata"):
        return None
    try:
        return json.loads(records[0]["clientdata"])
    except (json.JSONDecodeError, TypeError):
        return None
