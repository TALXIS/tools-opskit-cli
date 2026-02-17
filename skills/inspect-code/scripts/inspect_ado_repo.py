#!/usr/bin/env python3
"""Inspect Azure DevOps repositories — list repos, search code, get file contents, git history.

Uses the `az devops` CLI for Git operations and the Azure DevOps Search REST API
for code search. Authentication is via `az login` (interactive).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Add skills/ to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.preflight import require_provider


# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------


def _run_az(args_list: List[str], check: bool = True) -> str:
    """Run an az CLI command and return stdout."""
    cmd = ["az"] + args_list + ["--output", "json"]
    print(f"  $ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        # Strip the pkg_resources deprecation warning from stderr
        err = "\n".join(
            line for line in result.stderr.splitlines()
            if "pkg_resources" not in line and "UserWarning" not in line
        ).strip()
        print(f"az CLI error: {err}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def _get_access_token(resource: str = "499b84ac-1321-427f-aa17-267ca6975798") -> str:
    """Get an access token for Azure DevOps via `az account get-access-token`."""
    out = _run_az(["account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv"])
    # -o tsv already strips quotes, but --output json was appended; parse accordingly
    token = out.strip().strip('"')
    return token


def _get_access_token_raw() -> str:
    """Get a raw access token for Azure DevOps Search API."""
    result = subprocess.run(
        ["az", "account", "get-access-token",
         "--resource", "499b84ac-1321-427f-aa17-267ca6975798",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Failed to get access token: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Git operations via az CLI
# ---------------------------------------------------------------------------


def list_repos(org: str, project: str):
    out = _run_az(["repos", "list", "--org", org, "--project", project])
    repos = json.loads(out)
    results = [
        {
            "name": r["name"],
            "id": r["id"],
            "default_branch": r.get("defaultBranch", ""),
            "web_url": r.get("webUrl", ""),
        }
        for r in repos
    ]
    print(json.dumps(results, indent=2, default=str))
    print(f"\n--- {len(results)} repository(ies) ---", file=sys.stderr)


def list_files(org: str, project: str, repo: str, path: str):
    """List files/directories at a path using the Git Items REST API."""
    token = _get_access_token_raw()
    org_name = org.rstrip("/").split("/")[-1]
    url = (
        f"https://dev.azure.com/{quote(org_name)}/{quote(project)}"
        f"/_apis/git/repositories/{quote(repo)}"
        f"/items?scopePath={quote(path)}&recursionLevel=OneLevel&api-version=7.1"
    )
    req = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"API error ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    items = data.get("value", [])
    results = [{"path": i["path"], "is_folder": i.get("isFolder", False)} for i in items]
    print(json.dumps(results, indent=2, default=str))
    print(f"\n--- {len(results)} item(s) ---", file=sys.stderr)


def get_file(org: str, project: str, repo: str, path: str):
    """Get file contents using the Git Items REST API."""
    token = _get_access_token_raw()
    org_name = org.rstrip("/").split("/")[-1]
    url = (
        f"https://dev.azure.com/{quote(org_name)}/{quote(project)}"
        f"/_apis/git/repositories/{quote(repo)}"
        f"/items?path={quote(path)}&api-version=7.1"
    )
    req = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/octet-stream"})
    try:
        with urlopen(req) as resp:
            print(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        print(f"API error ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Code search via Azure DevOps Search REST API
# ---------------------------------------------------------------------------


def search_code(org: str, project: str, query: str,
                repo_filter: Optional[str] = None,
                path_filter: Optional[str] = None,
                extension_filter: Optional[str] = None,
                top: int = 25):
    """Search code using the Azure DevOps Search REST API."""
    token = _get_access_token_raw()
    org_name = org.rstrip("/").split("/")[-1]
    url = (
        f"https://almsearch.dev.azure.com/{quote(org_name)}"
        f"/{quote(project)}/_apis/search/codesearchresults?api-version=7.1"
    )

    filters: Dict[str, List[str]] = {}
    if repo_filter:
        filters["Repository"] = [repo_filter]
    # Path and CodeElement filters require Repository filter in the API,
    # so we use inline search syntax (path:, ext:) instead of filter objects
    # when no repository is specified.
    if repo_filter:
        if path_filter:
            filters["Path"] = [path_filter]
        if extension_filter:
            filters["CodeElement"] = [extension_filter]

    # Build search text with inline filters for path/extension
    search_text = query
    if path_filter and "path:" not in query:
        search_text += f" path:{path_filter}"
    if extension_filter and "ext:" not in query:
        search_text += f" ext:{extension_filter}"

    body = json.dumps({
        "searchText": search_text,
        "$top": top,
        "$skip": 0,
        "filters": filters if filters else {},
    }).encode()

    print(f"  Searching: {search_text}", file=sys.stderr)
    req = Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode()
        print(f"Search API error ({e.code}): {err_body}", file=sys.stderr)
        sys.exit(1)

    results = []
    for r in data.get("results", []):
        results.append({
            "repository": r.get("repository", {}).get("name", ""),
            "path": r.get("path", ""),
            "filename": r.get("fileName", ""),
            "project": r.get("project", {}).get("name", ""),
            "matches": [
                {"content": h.get("content", ""), "charOffset": h.get("charOffset", 0)}
                for h in r.get("matches", {}).get("content", [])
            ] if r.get("matches") else [],
        })

    print(json.dumps(results, indent=2, default=str))
    count = data.get("count", len(results))
    print(f"\n--- {len(results)} result(s) shown, {count} total ---", file=sys.stderr)


# ---------------------------------------------------------------------------
# Git history via REST API
# ---------------------------------------------------------------------------


def git_history(org: str, project: str, repo: str, path: Optional[str] = None, top: int = 10):
    """Show recent commits for a file or repo using the Git Commits REST API."""
    token = _get_access_token_raw()
    org_name = org.rstrip("/").split("/")[-1]
    url = (
        f"https://dev.azure.com/{quote(org_name)}/{quote(project)}"
        f"/_apis/git/repositories/{quote(repo)}"
        f"/commits?$top={top}&api-version=7.1"
    )
    if path:
        url += f"&searchCriteria.itemPath={quote(path)}"

    req = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"API error ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    commits = data.get("value", [])
    results = []
    for c in commits:
        author = c.get("author", {})
        results.append({
            "commitId": c.get("commitId", "")[:12],
            "author": author.get("name", ""),
            "date": author.get("date", ""),
            "message": c.get("comment", "").strip(),
            "url": c.get("remoteUrl", ""),
        })

    print(json.dumps(results, indent=2, default=str))
    target = f"'{path}'" if path else repo
    print(f"\n--- {len(results)} commit(s) for {target} ---", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Azure DevOps repositories — search code, browse files, view git history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for a Power Automate flow definition
  %(prog)s --action search --query "ntg_documentsignature" --path-filter "workflows" --extension-filter "json"

  # List repositories
  %(prog)s --action list-repos

  # List files in a directory
  %(prog)s --action list-files --repo MyRepo --path "/src"

  # Get file contents
  %(prog)s --action get-file --repo MyRepo --path "/workflows/flow.json"

  # View recent commits for a file
  %(prog)s --action git-history --repo MyRepo --path "/workflows/flow.json" --top 10
        """,
    )

    parser.add_argument("--organization", help="Azure DevOps organization URL (overrides connection)")
    parser.add_argument("--project", help="Project name (overrides connection)")
    parser.add_argument("--repo", help="Repository name (required for list-files, get-file, git-history)")
    parser.add_argument(
        "--action", required=True,
        choices=["list-repos", "list-files", "get-file", "search", "git-history"],
        help="Action to perform",
    )
    parser.add_argument("--path", default="/", help="File or directory path")
    parser.add_argument("--query", help="Search query string")
    parser.add_argument("--repo-filter", help="Filter search results to a specific repository")
    parser.add_argument("--path-filter", help="Filter search results by path (e.g., 'workflows')")
    parser.add_argument("--extension-filter", help="Filter search results by file extension (e.g., 'json')")
    parser.add_argument("--top", type=int, default=25, help="Maximum results to return (default: 25)")

    args = parser.parse_args()

    # Resolve connection (preflight validates, CLI flags override)
    conn = require_provider("ado", cli_overrides={
        "organization": args.organization,
        "project": args.project,
    })
    org = conn["organization"]
    project = conn["project"]
    print(f"Organization: {org}  Project: {project}", file=sys.stderr)

    if args.action == "list-repos":
        list_repos(org, project)

    elif args.action == "list-files":
        if not args.repo:
            print("Error: --repo is required for list-files", file=sys.stderr)
            sys.exit(1)
        list_files(org, project, args.repo, args.path)

    elif args.action == "get-file":
        if not args.repo:
            print("Error: --repo is required for get-file", file=sys.stderr)
            sys.exit(1)
        get_file(org, project, args.repo, args.path)

    elif args.action == "search":
        if not args.query:
            print("Error: --query is required for search", file=sys.stderr)
            sys.exit(1)
        search_code(
            org, project, args.query,
            repo_filter=args.repo_filter,
            path_filter=args.path_filter,
            extension_filter=args.extension_filter,
            top=args.top,
        )

    elif args.action == "git-history":
        if not args.repo:
            print("Error: --repo is required for git-history", file=sys.stderr)
            sys.exit(1)
        git_history(org, project, args.repo, path=args.path if args.path != "/" else None, top=args.top)


if __name__ == "__main__":
    main()
