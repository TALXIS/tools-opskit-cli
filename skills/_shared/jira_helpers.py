"""Shared Jira helpers for opskit skills — pure Python stdlib, no third-party deps."""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


def _auth_header(email: str, api_token: str) -> str:
    raw = f"{email}:{api_token}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


def jira_request(
    server: str,
    path: str,
    *,
    email: str,
    api_token: str,
    method: str = "GET",
    body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    accept: str = "application/json",
    raw_response: bool = False,
) -> Any:
    """
    Make an authenticated request to the Jira REST API.

    Returns parsed JSON by default, or the raw HTTPResponse if raw_response=True.
    """
    url = server.rstrip("/") + path
    if params:
        # Filter out None values
        filtered = {k: v for k, v in params.items() if v is not None}
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header(email, api_token))
    req.add_header("Accept", accept)
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_json = json.loads(error_body)
            msg = error_json.get("errorMessages", [error_body])
            if isinstance(msg, list):
                msg = "; ".join(msg) if msg else error_body
        except (json.JSONDecodeError, KeyError):
            msg = error_body
        print(f"HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)

    if raw_response:
        return resp

    return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------


def search_issues_paginated(
    server: str,
    email: str,
    api_token: str,
    jql: str,
    fields: Optional[List[str]] = None,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search issues using JQL with automatic pagination.

    Uses POST /rest/api/3/search/jql (current endpoint).
    """
    all_issues: List[Dict[str, Any]] = []
    next_page_token: Optional[str] = None

    while True:
        body: Dict[str, Any] = {
            "jql": jql,
            "maxResults": min(max_results - len(all_issues), 100),
        }
        if fields:
            body["fields"] = fields
        if next_page_token:
            body["nextPageToken"] = next_page_token

        result = jira_request(
            server,
            "/rest/api/3/search/jql",
            email=email,
            api_token=api_token,
            method="POST",
            body=body,
        )

        issues = result.get("issues", [])
        all_issues.extend(issues)
        total = result.get("total", "?")
        print(f"  Fetched {len(all_issues)}/{total} issues...", file=sys.stderr)

        next_page_token = result.get("nextPageToken")
        if not next_page_token or len(all_issues) >= max_results or not issues:
            break

    return all_issues[:max_results]


def servicedesk_paginated(
    server: str,
    email: str,
    api_token: str,
    path: str,
    values_key: str = "values",
) -> List[Dict[str, Any]]:
    """Paginate through a JSM Service Desk API endpoint."""
    all_values: List[Dict[str, Any]] = []
    start = 0
    limit = 50

    while True:
        result = jira_request(
            server,
            path,
            email=email,
            api_token=api_token,
            params={"start": start, "limit": limit},
        )

        values = result.get(values_key, [])
        all_values.extend(values)

        if result.get("isLastPage", True) or not values:
            break
        start += len(values)

    return all_values


# ---------------------------------------------------------------------------
# ADF (Atlassian Document Format) → plain text
# ---------------------------------------------------------------------------


def adf_to_text(node: Any) -> str:
    """
    Convert an Atlassian Document Format node to plain text.

    Handles common node types: paragraph, text, heading, bulletList,
    orderedList, listItem, codeBlock, blockquote, hardBreak, mention,
    mediaGroup, mediaSingle, table, tableRow, tableCell, tableHeader.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node

    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")
    text = node.get("text", "")
    content = node.get("content", [])

    if node_type == "text":
        return text

    if node_type == "hardBreak":
        return "\n"

    if node_type == "mention":
        return node.get("attrs", {}).get("text", "@unknown")

    if node_type == "emoji":
        return node.get("attrs", {}).get("shortName", "")

    # Recurse into children
    children_text = "".join(adf_to_text(child) for child in content)

    if node_type == "doc":
        return children_text

    if node_type in ("paragraph", "blockquote"):
        return children_text + "\n"

    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return "#" * level + " " + children_text + "\n"

    if node_type in ("bulletList", "orderedList"):
        lines = []
        for i, item in enumerate(content):
            prefix = f"{i + 1}. " if node_type == "orderedList" else "- "
            item_text = adf_to_text(item).strip()
            lines.append(prefix + item_text)
        return "\n".join(lines) + "\n"

    if node_type == "listItem":
        return children_text

    if node_type == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        return f"```{lang}\n{children_text}```\n"

    if node_type in ("mediaSingle", "mediaGroup"):
        return "[attachment]\n"

    if node_type == "table":
        rows = []
        for row in content:
            cells = []
            for cell in row.get("content", []):
                cells.append(adf_to_text(cell).strip())
            rows.append(" | ".join(cells))
        return "\n".join(rows) + "\n"

    if node_type in ("tableRow", "tableHeader", "tableCell"):
        return children_text

    # Fallback: just return children text
    return children_text


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_output(records: Any, output_format: str = "json") -> str:
    """Format results as JSON or table."""
    if output_format == "json":
        return json.dumps(records, indent=2, default=str)

    if output_format == "table":
        if isinstance(records, dict):
            records = [records]
        if not records:
            return "No records found"

        columns = list(records[0].keys())
        widths = {col: len(str(col)) for col in columns}
        for record in records:
            for col in columns:
                val = str(record.get(col, ""))
                # Truncate long values for table display
                if len(val) > 80:
                    val = val[:77] + "..."
                widths[col] = max(widths[col], len(val))

        lines = []
        header = " | ".join(str(col).ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-+-".join("-" * widths[col] for col in columns))
        for record in records:
            row_parts = []
            for col in columns:
                val = str(record.get(col, ""))
                if len(val) > 80:
                    val = val[:77] + "..."
                row_parts.append(val.ljust(widths[col]))
            lines.append(" | ".join(row_parts))
        return "\n".join(lines)

    return str(records)



def add_output_args(parser) -> None:
    """Add common output arguments."""
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )
