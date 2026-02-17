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


# ---------------------------------------------------------------------------
# Profile configuration
# ---------------------------------------------------------------------------

_PROFILES_FILENAME = ".profiles.json"


def _profiles_path() -> Path:
    return Path(__file__).resolve().parents[1] / _PROFILES_FILENAME


def load_profiles() -> Dict[str, Any]:
    path = _profiles_path()
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"profiles": {}}


def save_profiles(data: Dict[str, Any]) -> None:
    path = _profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_profile(name: str = "default") -> Dict[str, Any]:
    data = load_profiles()
    return data.get("profiles", {}).get(name, {})


def set_profile(name: str, profile: Dict[str, Any]) -> None:
    data = load_profiles()
    data.setdefault("profiles", {})[name] = profile
    save_profiles(data)


def resolve_config(args) -> Dict[str, str]:
    """Merge profile defaults with CLI flags (CLI flags take precedence)."""
    profile = get_profile(args.profile) if args.profile else {}
    org = args.organization or profile.get("organization", "")
    project = args.project or profile.get("project", "")
    if not org:
        print("Error: --organization is required (or set it in a profile)", file=sys.stderr)
        sys.exit(1)
    if not project:
        print("Error: --project is required (or set it in a profile)", file=sys.stderr)
        sys.exit(1)
    return {"organization": org, "project": project}


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

  # Save a profile for reuse
  %(prog)s --action set-profile --profile-name default \\
    --organization "https://dev.azure.com/thenetworg" --project "INT0015"
        """,
    )

    parser.add_argument("--organization", help="Azure DevOps organization URL (overrides profile)")
    parser.add_argument("--project", help="Project name (overrides profile)")
    parser.add_argument("--profile", default="default", help="Profile name to use (default: 'default')")
    parser.add_argument("--repo", help="Repository name (required for list-files, get-file, git-history)")
    parser.add_argument(
        "--action", required=True,
        choices=["list-repos", "list-files", "get-file", "search", "git-history", "set-profile", "show-profile"],
        help="Action to perform",
    )
    parser.add_argument("--path", default="/", help="File or directory path")
    parser.add_argument("--query", help="Search query string")
    parser.add_argument("--repo-filter", help="Filter search results to a specific repository")
    parser.add_argument("--path-filter", help="Filter search results by path (e.g., 'workflows')")
    parser.add_argument("--extension-filter", help="Filter search results by file extension (e.g., 'json')")
    parser.add_argument("--top", type=int, default=25, help="Maximum results to return (default: 25)")
    parser.add_argument("--profile-name", help="Profile name for set-profile action")

    args = parser.parse_args()

    # Profile management actions
    if args.action == "set-profile":
        name = args.profile_name or args.profile or "default"
        profile = {"provider": "ado"}
        if args.organization:
            profile["organization"] = args.organization
        if args.project:
            profile["project"] = args.project
        set_profile(name, profile)
        print(json.dumps({"message": f"Profile '{name}' saved", "profile": profile}, indent=2))
        print(f"Saved to {_profiles_path()}", file=sys.stderr)
        return

    if args.action == "show-profile":
        name = args.profile or "default"
        profile = get_profile(name)
        if profile:
            print(json.dumps({"name": name, "profile": profile}, indent=2))
        else:
            all_profiles = load_profiles().get("profiles", {})
            print(json.dumps({"error": f"Profile '{name}' not found", "available": list(all_profiles.keys())}, indent=2))
        return

    # Resolve org/project from profile + CLI flags
    config = resolve_config(args)
    org = config["organization"]
    project = config["project"]
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
