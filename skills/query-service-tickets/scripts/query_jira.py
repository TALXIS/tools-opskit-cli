#!/usr/bin/env python3
"""Query Jira Service Management tickets — pure stdlib, no third-party deps."""

import argparse
import json
import os
import sys
from pathlib import Path

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.jira_helpers import (
    add_output_args,
    adf_to_text,
    format_output,
    jira_request,
    search_issues_paginated,
    servicedesk_paginated,
)
from _shared.preflight import require_provider


def do_search(args, email, api_token):
    """Search issues using JQL."""
    if not args.jql:
        print("Error: --jql is required for search", file=sys.stderr)
        sys.exit(1)

    fields = ["summary", "status", "priority", "assignee", "created", "updated", "issuetype"]
    issues = search_issues_paginated(
        args.server, email, api_token, args.jql, fields=fields, max_results=args.max_results,
    )

    results = []
    for issue in issues:
        f = issue.get("fields", {})
        results.append({
            "key": issue["key"],
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "priority": (f.get("priority") or {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName"),
            "created": f.get("created"),
            "updated": f.get("updated"),
            "issuetype": (f.get("issuetype") or {}).get("name"),
        })

    print(format_output(results, args.format))
    print(f"\n--- {len(results)} issue(s) found ---", file=sys.stderr)


def do_get(args, email, api_token):
    """Get full details of a specific issue."""
    if not args.issue_key:
        print("Error: --issue-key is required for get", file=sys.stderr)
        sys.exit(1)

    issue = jira_request(
        args.server,
        f"/rest/api/3/issue/{args.issue_key}",
        email=email,
        api_token=api_token,
    )

    f = issue.get("fields", {})
    result = {
        "key": issue["key"],
        "summary": f.get("summary"),
        "description": adf_to_text(f.get("description")),
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "reporter": (f.get("reporter") or {}).get("displayName"),
        "created": f.get("created"),
        "updated": f.get("updated"),
        "issuetype": (f.get("issuetype") or {}).get("name"),
        "labels": f.get("labels", []),
        "components": [c.get("name") for c in (f.get("components") or [])],
        "attachments": [
            {"id": a["id"], "filename": a["filename"], "size": a["size"], "mimeType": a.get("mimeType")}
            for a in (f.get("attachment") or [])
        ],
    }

    print(format_output(result, args.format))


def do_get_comments(args, email, api_token):
    """Get comments on an issue."""
    if not args.issue_key:
        print("Error: --issue-key is required for get-comments", file=sys.stderr)
        sys.exit(1)

    all_comments = []
    start_at = 0

    while True:
        data = jira_request(
            args.server,
            f"/rest/api/3/issue/{args.issue_key}/comment",
            email=email,
            api_token=api_token,
            params={"startAt": start_at, "maxResults": 100},
        )

        for c in data.get("comments", []):
            all_comments.append({
                "id": c["id"],
                "author": (c.get("author") or {}).get("displayName"),
                "body": adf_to_text(c.get("body")),
                "created": c.get("created"),
                "updated": c.get("updated"),
            })

        if start_at + len(data.get("comments", [])) >= data.get("total", 0):
            break
        start_at += len(data.get("comments", []))

    print(format_output(all_comments, args.format))
    print(f"\n--- {len(all_comments)} comment(s) ---", file=sys.stderr)


def do_list_organizations(args, email, api_token):
    """List JSM organizations."""
    orgs = servicedesk_paginated(
        args.server, email, api_token, "/rest/servicedeskapi/organization",
    )

    results = [{"id": o["id"], "name": o["name"]} for o in orgs]
    print(format_output(results, args.format))
    print(f"\n--- {len(results)} organization(s) ---", file=sys.stderr)


def do_list_attachments(args, email, api_token):
    """List attachments on an issue."""
    if not args.issue_key:
        print("Error: --issue-key is required for list-attachments", file=sys.stderr)
        sys.exit(1)

    issue = jira_request(
        args.server,
        f"/rest/api/3/issue/{args.issue_key}",
        email=email,
        api_token=api_token,
        params={"fields": "attachment"},
    )

    attachments = issue.get("fields", {}).get("attachment", [])
    results = [
        {
            "id": a["id"],
            "filename": a["filename"],
            "size": a["size"],
            "mimeType": a.get("mimeType"),
            "created": a.get("created"),
            "author": (a.get("author") or {}).get("displayName"),
        }
        for a in attachments
    ]

    print(format_output(results, args.format))
    print(f"\n--- {len(results)} attachment(s) ---", file=sys.stderr)


def do_download_attachment(args, email, api_token):
    """Download an attachment by ID."""
    if not args.attachment_id:
        print("Error: --attachment-id is required for download-attachment", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get attachment metadata first
    meta = jira_request(
        args.server,
        f"/rest/api/3/attachment/{args.attachment_id}",
        email=email,
        api_token=api_token,
    )

    filename = meta.get("filename", f"attachment-{args.attachment_id}")
    filepath = output_dir / filename

    # Download content
    resp = jira_request(
        args.server,
        f"/rest/api/3/attachment/content/{args.attachment_id}",
        email=email,
        api_token=api_token,
        params={"redirect": "false"},
        raw_response=True,
    )

    with open(filepath, "wb") as f:
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            f.write(chunk)

    print(json.dumps({"filename": filename, "path": str(filepath), "size": os.path.getsize(filepath)}))
    print(f"Downloaded: {filepath} ({os.path.getsize(filepath)} bytes)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Query Jira Service Management tickets (pure stdlib, no third-party deps)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for open tickets
  %(prog)s --action search --jql "project = PROJ AND status != Done ORDER BY created DESC"

  # Get details of a specific ticket
  %(prog)s --action get --issue-key PROJ-1234

  # Get comments on a ticket
  %(prog)s --action get-comments --issue-key PROJ-1234

  # List all organizations
  %(prog)s --action list-organizations

  # List attachments on a ticket
  %(prog)s --action list-attachments --issue-key PROJ-1234

  # Download an attachment
  %(prog)s --action download-attachment --attachment-id 12345 --output-dir ./downloads
        """,
    )

    # Optional CLI overrides (preflight provides defaults from connections.json)
    parser.add_argument("--server", help="Jira server URL (overrides connection)")
    parser.add_argument("--email", help="Atlassian email (overrides connection)")
    parser.add_argument("--api-token", help="Atlassian API token (overrides connection)")
    add_output_args(parser)

    parser.add_argument(
        "--action",
        required=True,
        choices=["search", "get", "get-comments", "list-organizations", "list-attachments", "download-attachment"],
        help="Action to perform",
    )
    parser.add_argument("--jql", help="JQL query string (for search)")
    parser.add_argument("--issue-key", help="Issue key (for get, get-comments, list-attachments)")
    parser.add_argument("--attachment-id", help="Attachment ID (for download-attachment)")
    parser.add_argument("--max-results", type=int, default=50, help="Max results for search (default: 50)")
    parser.add_argument("--output-dir", default=".", help="Output directory for attachments (default: current dir)")

    args = parser.parse_args()

    # Resolve connection (preflight validates, CLI flags override)
    conn = require_provider("jira", cli_overrides={
        "server": args.server,
        "email": args.email,
        "api_token": getattr(args, "api_token", None),
    })
    server = conn["server"]
    email = conn["email"]
    api_token = conn["api_token"]
    # Put resolved values back on args for action functions
    args.server = server
    print(f"{email} → {server}", file=sys.stderr)

    actions = {
        "search": do_search,
        "get": do_get,
        "get-comments": do_get_comments,
        "list-organizations": do_list_organizations,
        "list-attachments": do_list_attachments,
        "download-attachment": do_download_attachment,
    }

    actions[args.action](args, email, api_token)


if __name__ == "__main__":
    main()

