"""Shared Dataverse helpers for opskit skills."""

import base64
import json
import sys
from typing import Any, Dict, List, Optional


def check_dependencies():
    """Check if required packages are installed and exit with a clear message if not."""
    missing = []
    try:
        import azure.identity  # noqa: F401
    except ImportError:
        missing.append("azure-identity")
    try:
        import PowerPlatform.Dataverse  # noqa: F401
    except ImportError:
        missing.append("PowerPlatform-Dataverse-Client")

    if missing:
        print(f"ERROR: Missing required packages: {', '.join(missing)}", file=sys.stderr)
        print(f"Run: pip install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def _get_identity_from_token(credential, environment_url: str) -> Optional[Dict[str, str]]:
    """Decode the JWT access token to extract user/tenant info."""
    try:
        token = credential.get_token(f"{environment_url.rstrip('/')}/.default")
        payload = token.token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.b64decode(payload))
        return {
            "username": claims.get("upn", claims.get("unique_name", "unknown")),
            "tenant_id": claims.get("tid", "unknown"),
        }
    except Exception:
        return None


def create_credential(
    environment_url: str,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    interactive: bool = False,
):
    """
    Create an Azure credential for Dataverse / Power Platform access.

    Interactive auth tries Azure CLI first (silent if 'az login' was done),
    then falls back to browser prompt.
    """
    from azure.identity import (
        AzureCliCredential,
        ChainedTokenCredential,
        ClientSecretCredential,
        InteractiveBrowserCredential,
    )

    if interactive:
        credential = ChainedTokenCredential(
            AzureCliCredential(),
            InteractiveBrowserCredential(),
        )
    elif tenant_id and client_id and client_secret:
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        raise ValueError(
            "Either use --interactive flag or provide --tenant-id, --client-id, and --client-secret"
        )

    # Show who we're connecting as for safety
    identity = _get_identity_from_token(credential, environment_url)
    if identity:
        print(
            f"{identity['username']} → {environment_url}",
            file=sys.stderr,
        )
    else:
        print(f"Connecting to {environment_url}...", file=sys.stderr)

    return credential


def create_client(
    environment_url: str,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    interactive: bool = False,
):
    """
    Create a DataverseClient with appropriate authentication.

    Interactive auth tries Azure CLI first (silent if 'az login' was done),
    then falls back to browser prompt. No keychain or token cache files needed.
    """
    from PowerPlatform.Dataverse.client import DataverseClient

    credential = create_credential(
        environment_url, tenant_id, client_id, client_secret, interactive,
    )
    return DataverseClient(environment_url, credential)


def is_odata_annotation(key: str) -> bool:
    """Check if a key is an OData annotation (metadata, not user data)."""
    return key.startswith("@") or "@OData" in key or "@Microsoft" in key


def strip_annotations(record: Dict[str, Any]) -> Dict[str, Any]:
    """Remove OData annotation keys from a record."""
    return {k: v for k, v in record.items() if not is_odata_annotation(k)}


def query_odata(
    client,
    table_name: str,
    select: Optional[List[str]] = None,
    filter_expr: Optional[str] = None,
    orderby: Optional[List[str]] = None,
    top: Optional[int] = None,
    include_annotations: bool = False,
) -> List[Dict[str, Any]]:
    """
    Query Dataverse using OData parameters.

    Args:
        client: DataverseClient instance
        table_name: Table schema name (e.g., "account", "contact")
        select: List of column names to select
        filter_expr: OData filter expression (e.g., "statecode eq 0")
        orderby: List of order by expressions (e.g., ["createdon desc"])
        top: Maximum number of results to return
        include_annotations: If True, keep OData annotations (formatted values, etag, etc.)
    """
    kwargs: Dict[str, Any] = {}
    if select:
        kwargs["select"] = select
    if filter_expr:
        kwargs["filter"] = filter_expr
    if orderby:
        kwargs["orderby"] = orderby
    if top is not None:
        kwargs["top"] = top

    pages = client.get(table_name, **kwargs)

    all_records: List[Dict[str, Any]] = []
    for page in pages:
        if include_annotations:
            all_records.extend(page)
        else:
            all_records.extend(strip_annotations(r) for r in page)
        print(f"  Fetched {len(all_records)} records...", file=sys.stderr)

    return all_records


def format_output(records, output_format: str = "json") -> str:
    """Format query results for output.

    Accepts a list of dicts (tabular data) or a single dict/value (JSON only).
    """
    if output_format == "json":
        return json.dumps(records, indent=2, default=str)
    elif output_format == "table":
        # Wrap single dict in a list for table rendering
        if isinstance(records, dict):
            records = [records]
        if not records:
            return "No records found"

        columns = list(records[0].keys())

        # Calculate column widths
        widths = {col: len(str(col)) for col in columns}
        for record in records:
            for col in columns:
                widths[col] = max(widths[col], len(str(record.get(col, ""))))

        lines = []
        header = " | ".join(str(col).ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-+-".join("-" * widths[col] for col in columns))
        for record in records:
            row = " | ".join(str(record.get(col, "")).ljust(widths[col]) for col in columns)
            lines.append(row)

        return "\n".join(lines)
    else:
        return str(records)


def add_auth_args(parser):
    """Add common authentication arguments to an argparse parser."""
    parser.add_argument(
        "--environment-url",
        required=True,
        help="Dataverse environment URL (e.g., https://org.crm.dynamics.com)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Use interactive authentication (tries Azure CLI, falls back to browser)",
    )
    parser.add_argument("--tenant-id", help="Azure AD tenant ID (for client secret auth)")
    parser.add_argument("--client-id", help="Azure AD app client ID (for client secret auth)")
    parser.add_argument("--client-secret", help="Azure AD app client secret (for client secret auth)")


def add_output_args(parser):
    """Add common output arguments to an argparse parser."""
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--include-annotations",
        action="store_true",
        help="Include OData annotations (formatted values, etag, lookup names)",
    )
