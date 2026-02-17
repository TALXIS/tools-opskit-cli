#!/usr/bin/env python3
"""Inspect Azure DevOps repositories — list repos, search code, get file contents."""

import argparse
import json
import sys

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


def get_connection(organization_url: str, pat: str) -> Connection:
    credentials = BasicAuthentication("", pat)
    return Connection(base_url=organization_url, creds=credentials)


def list_repos(connection: Connection, project: str):
    git_client = connection.clients.get_git_client()
    repos = git_client.get_repositories(project)
    results = [{"name": r.name, "id": r.id, "default_branch": r.default_branch, "web_url": r.remote_url} for r in repos]
    print(json.dumps(results, indent=2, default=str))
    print(f"\n--- {len(results)} repository(ies) ---", file=sys.stderr)


def list_files(connection: Connection, project: str, repo: str, path: str):
    git_client = connection.clients.get_git_client()
    items = git_client.get_items(repo, project=project, scope_path=path, recursion_level="OneLevel")
    results = [{"path": i.path, "is_folder": i.is_folder} for i in items]
    print(json.dumps(results, indent=2, default=str))


def get_file(connection: Connection, project: str, repo: str, path: str):
    git_client = connection.clients.get_git_client()
    item = git_client.get_item_text(repo, path, project=project)
    content = "".join(chunk.decode("utf-8", errors="replace") for chunk in item)
    print(content)


def search_code(connection: Connection, project: str, query: str):
    # Code search uses the Search API (separate from core Git API)
    # This is a simplified placeholder — full implementation uses the Search REST API
    print(json.dumps({"message": "Code search requires the Azure DevOps Search API.", "query": query, "project": project}, indent=2))
    print("TODO: Implement Azure DevOps Search API call", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Inspect Azure DevOps repositories")
    parser.add_argument("--organization", required=True, help="Azure DevOps organization URL")
    parser.add_argument("--pat", required=True, help="Personal Access Token")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--repo", help="Repository name (required for get-file, list-files)")
    parser.add_argument("--action", required=True, choices=["list-repos", "list-files", "get-file", "search"], help="Action to perform")
    parser.add_argument("--path", default="/", help="File or directory path")
    parser.add_argument("--query", help="Search query string")
    args = parser.parse_args()

    connection = get_connection(args.organization, args.pat)

    if args.action == "list-repos":
        list_repos(connection, args.project)
    elif args.action == "list-files":
        if not args.repo:
            print("Error: --repo is required for list-files", file=sys.stderr)
            sys.exit(1)
        list_files(connection, args.project, args.repo, args.path)
    elif args.action == "get-file":
        if not args.repo:
            print("Error: --repo is required for get-file", file=sys.stderr)
            sys.exit(1)
        get_file(connection, args.project, args.repo, args.path)
    elif args.action == "search":
        if not args.query:
            print("Error: --query is required for search", file=sys.stderr)
            sys.exit(1)
        search_code(connection, args.project, args.query)


if __name__ == "__main__":
    main()
