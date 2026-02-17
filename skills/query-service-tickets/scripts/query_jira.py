#!/usr/bin/env python3
"""Query Jira service tickets — search, get details, get comments."""

import argparse
import json
import sys

from jira import JIRA


def get_client(server: str, username: str, api_token: str) -> JIRA:
    return JIRA(server=server, basic_auth=(username, api_token))


def search_issues(client: JIRA, jql: str, max_results: int = 20):
    issues = client.search_issues(jql, maxResults=max_results)
    results = []
    for issue in issues:
        results.append({
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": str(issue.fields.status),
            "priority": str(issue.fields.priority) if issue.fields.priority else None,
            "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
            "created": str(issue.fields.created),
            "updated": str(issue.fields.updated),
            "issuetype": str(issue.fields.issuetype),
        })
    print(json.dumps(results, indent=2))
    print(f"\n--- {len(results)} issue(s) found ---", file=sys.stderr)


def get_issue(client: JIRA, issue_key: str):
    issue = client.issue(issue_key)
    result = {
        "key": issue.key,
        "summary": issue.fields.summary,
        "description": issue.fields.description,
        "status": str(issue.fields.status),
        "priority": str(issue.fields.priority) if issue.fields.priority else None,
        "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
        "reporter": str(issue.fields.reporter) if issue.fields.reporter else None,
        "created": str(issue.fields.created),
        "updated": str(issue.fields.updated),
        "issuetype": str(issue.fields.issuetype),
        "labels": issue.fields.labels,
        "components": [str(c) for c in issue.fields.components],
    }
    print(json.dumps(result, indent=2))


def get_comments(client: JIRA, issue_key: str):
    comments = client.comments(issue_key)
    results = []
    for comment in comments:
        results.append({
            "id": comment.id,
            "author": str(comment.author),
            "body": comment.body,
            "created": str(comment.created),
            "updated": str(comment.updated),
        })
    print(json.dumps(results, indent=2))
    print(f"\n--- {len(results)} comment(s) ---", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Query Jira service tickets")
    parser.add_argument("--server", required=True, help="Jira server URL")
    parser.add_argument("--username", required=True, help="Jira username/email")
    parser.add_argument("--api-token", required=True, help="Jira API token")
    parser.add_argument("--action", required=True, choices=["search", "get", "get-comments"], help="Action to perform")
    parser.add_argument("--jql", help="JQL query string (for search)")
    parser.add_argument("--issue-key", help="Issue key (for get, get-comments)")
    parser.add_argument("--max-results", type=int, default=20, help="Max results for search")
    args = parser.parse_args()

    client = get_client(args.server, args.username, args.api_token)

    if args.action == "search":
        if not args.jql:
            print("Error: --jql is required for search", file=sys.stderr)
            sys.exit(1)
        search_issues(client, args.jql, args.max_results)
    elif args.action == "get":
        if not args.issue_key:
            print("Error: --issue-key is required for get", file=sys.stderr)
            sys.exit(1)
        get_issue(client, args.issue_key)
    elif args.action == "get-comments":
        if not args.issue_key:
            print("Error: --issue-key is required for get-comments", file=sys.stderr)
            sys.exit(1)
        get_comments(client, args.issue_key)


if __name__ == "__main__":
    main()
