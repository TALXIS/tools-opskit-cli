#!/usr/bin/env python3
"""OpsKit bootstrap — venv setup, connection management, and provider status.

Cross-platform (macOS, Linux, Windows).

Usage:
    python3 scripts/bootstrap.py setup
    python3 scripts/bootstrap.py status
    python3 scripts/bootstrap.py check <provider>
    python3 scripts/bootstrap.py add-connection <provider> <name> [--server ...] [--email ...] ...
    python3 scripts/bootstrap.py remove-connection <provider> <name>
    python3 scripts/bootstrap.py set-default <provider> <name>
    python3 scripts/bootstrap.py list-connections
    python3 scripts/bootstrap.py init-workspace [--environment-url ...] [--jira ...] [--ado ...] [--dataverse ...]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PLUGIN_ROOT / ".venv"
REQUIREMENTS = PLUGIN_ROOT / "requirements.txt"

# Import preflight from skills/_shared/
sys.path.insert(0, str(PLUGIN_ROOT / "skills"))
from _shared.preflight import (
    check_all,
    check_provider,
    load_config,
    load_connections,
    load_workspace,
    print_status,
    save_config,
    save_connections,
    save_workspace,
)


def _venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python3"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_setup(_args: argparse.Namespace) -> None:
    """Create virtual environment and install dependencies."""
    venv_python = _venv_python()

    if not venv_python.exists():
        print(f"Creating virtual environment at {VENV_DIR} ...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"Virtual environment already exists at {VENV_DIR}", file=sys.stderr)

    if REQUIREMENTS.exists():
        print("Installing dependencies ...", file=sys.stderr)
        subprocess.check_call([
            str(venv_python), "-m", "pip", "install",
            "--quiet", "--upgrade", "-r", str(REQUIREMENTS),
        ])
    else:
        print(f"No requirements.txt found at {REQUIREMENTS}", file=sys.stderr)

    print(str(venv_python))


def cmd_status(_args: argparse.Namespace) -> None:
    """Check all providers and print readiness report."""
    statuses = check_all()
    print_status(statuses)


def cmd_check(args: argparse.Namespace) -> None:
    """Check a single provider."""
    status = check_provider(args.provider)
    print_status({args.provider: status})
    if not status.ready:
        sys.exit(1)


def cmd_add_connection(args: argparse.Namespace) -> None:
    """Add a named connection. Uses CLI flags if provided, else interactive prompts."""
    provider = args.provider
    name = args.name
    connections = load_connections()

    if provider == "jira":
        conn = _build_jira(args) or _prompt_jira()
    elif provider == "ado":
        conn = _build_ado(args) or _prompt_ado()
    elif provider == "dataverse":
        conn = _build_dataverse(args) or _prompt_dataverse()
    else:
        print(f"Unknown provider: {provider}", file=sys.stderr)
        sys.exit(1)

    connections.setdefault(provider, {})[name] = conn
    save_connections(connections)
    print(f"Connection '{name}' saved for {provider}.", file=sys.stderr)

    # Set as default if it's the first connection for this provider
    config = load_config()
    if not config.get("defaults", {}).get(provider):
        config.setdefault("defaults", {})[provider] = name
        save_config(config)
        print(f"Set '{name}' as default for {provider}.", file=sys.stderr)


def cmd_remove_connection(args: argparse.Namespace) -> None:
    """Remove a named connection."""
    connections = load_connections()
    provider_conns = connections.get(args.provider, {})
    if args.name not in provider_conns:
        print(f"Connection '{args.name}' not found for {args.provider}.", file=sys.stderr)
        sys.exit(1)

    del provider_conns[args.name]
    save_connections(connections)
    print(f"Connection '{args.name}' removed from {args.provider}.", file=sys.stderr)

    # Clear default if it pointed to the removed connection
    config = load_config()
    if config.get("defaults", {}).get(args.provider) == args.name:
        config["defaults"].pop(args.provider, None)
        save_config(config)
        print(f"Default for {args.provider} cleared (was '{args.name}').", file=sys.stderr)


def cmd_set_default(args: argparse.Namespace) -> None:
    """Set the default connection for a provider."""
    connections = load_connections()
    if args.name not in connections.get(args.provider, {}):
        print(f"Connection '{args.name}' not found for {args.provider}.", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    config.setdefault("defaults", {})[args.provider] = args.name
    save_config(config)
    print(f"Default for {args.provider} set to '{args.name}'.", file=sys.stderr)


def cmd_list_connections(_args: argparse.Namespace) -> None:
    """List all connections (secrets masked)."""
    connections = load_connections()
    config = load_config()
    defaults = config.get("defaults", {})

    if not connections:
        print("No connections configured.")
        print(f"  Run: python3 {PLUGIN_ROOT}/scripts/bootstrap.py add-connection <provider> <name>")
        return

    for provider, conns in connections.items():
        default_name = defaults.get(provider, "")
        print(f"\n{provider}:")
        for name, conn in conns.items():
            marker = " (default)" if name == default_name else ""
            print(f"  {name}{marker}:")
            for k, v in conn.items():
                if k in ("api_token", "client_secret"):
                    v = v[:4] + "***" if len(str(v)) > 4 else "***"
                print(f"    {k}: {v}")


def cmd_init_workspace(args: argparse.Namespace) -> None:
    """Create or update ops/opskit.json in the current working directory."""
    ws = load_workspace()

    if args.environment_url:
        ws["environment_url"] = args.environment_url.rstrip("/")

    ws_conns = ws.get("connections", {})
    if args.jira:
        ws_conns["jira"] = args.jira
    if args.ado:
        ws_conns["ado"] = args.ado
    if args.dataverse:
        ws_conns["dataverse"] = args.dataverse
    if ws_conns:
        ws["connections"] = ws_conns

    if not ws:
        print("No options provided. Use --environment-url, --jira, --ado, --dataverse.", file=sys.stderr)
        sys.exit(1)

    save_workspace(ws)
    path = Path.cwd() / "ops" / "opskit.json"
    print(f"Workspace config written to {path}", file=sys.stderr)
    print(json.dumps(ws, indent=2))


# ---------------------------------------------------------------------------
# Non-interactive builders (return dict if all required flags present, else None)
# ---------------------------------------------------------------------------


def _build_jira(args: argparse.Namespace) -> dict | None:
    server = getattr(args, "server", None)
    email = getattr(args, "email", None)
    api_token = getattr(args, "api_token", None)
    if server and email and api_token:
        return {"server": server.rstrip("/"), "email": email, "api_token": api_token}
    if any([server, email, api_token]):
        print("Jira requires all of: --server, --email, --api-token", file=sys.stderr)
        sys.exit(1)
    return None


def _build_ado(args: argparse.Namespace) -> dict | None:
    organization = getattr(args, "organization", None)
    project = getattr(args, "project", None)
    tenant_id = getattr(args, "tenant_id", None)
    if organization and project:
        conn = {"organization": organization.rstrip("/"), "project": project}
        if tenant_id:
            conn["tenant_id"] = tenant_id
        return conn
    if any([organization, project]):
        print("ADO requires both: --organization, --project", file=sys.stderr)
        sys.exit(1)
    return None


def _build_dataverse(args: argparse.Namespace) -> dict | None:
    tenant_id = getattr(args, "tenant_id", None)
    if tenant_id:
        return {"tenant_id": tenant_id}
    return None


# ---------------------------------------------------------------------------
# Interactive prompts (fallback when CLI flags not provided)
# ---------------------------------------------------------------------------


def _prompt(label: str, default: str = "", secret: bool = False) -> str:
    """Prompt for input with optional default. Uses getpass for secrets."""
    suffix = f" [{default}]" if default else ""
    if secret:
        import getpass
        value = getpass.getpass(f"{label}{suffix}: ").strip()
    else:
        value = input(f"{label}{suffix}: ").strip()
    return value or default


def _prompt_jira() -> dict:
    print("\n--- Jira Connection Setup ---")
    print(f"Create an API token at: https://id.atlassian.com/manage-profile/security/api-tokens\n")
    server = _prompt("Server URL (e.g. https://yourcompany.atlassian.net)")
    email = _prompt("Email")
    api_token = _prompt("API token", secret=True)
    if not all([server, email, api_token]):
        print("All fields are required.", file=sys.stderr)
        sys.exit(1)
    return {"server": server.rstrip("/"), "email": email, "api_token": api_token}


def _prompt_ado() -> dict:
    print("\n--- Azure DevOps Connection Setup ---")
    print("Requires: az login (Azure CLI)\n")
    organization = _prompt("Organization URL (e.g. https://dev.azure.com/yourorg)")
    project = _prompt("Project name")
    tenant_id = _prompt("Tenant ID (optional, for multi-tenant)", default="")
    if not all([organization, project]):
        print("Organization and project are required.", file=sys.stderr)
        sys.exit(1)
    conn = {"organization": organization.rstrip("/"), "project": project}
    if tenant_id:
        conn["tenant_id"] = tenant_id
    return conn


def _prompt_dataverse() -> dict:
    print("\n--- Dataverse Connection Setup ---")
    print("Requires: az login (Azure CLI)")
    print("Environment URL is set per-workspace in ops/opskit.json\n")
    tenant_id = _prompt("Tenant ID")
    if not tenant_id:
        print("Tenant ID is required.", file=sys.stderr)
        sys.exit(1)
    return {"tenant_id": tenant_id}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpsKit bootstrap — venv setup, connection management, provider status.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    sub.add_parser("setup", help="Create venv and install dependencies")
    sub.add_parser("status", help="Check all providers and print readiness report")

    p_check = sub.add_parser("check", help="Check a single provider")
    p_check.add_argument("provider", choices=["jira", "ado", "dataverse"])

    p_add = sub.add_parser("add-connection", help="Add a named connection")
    p_add.add_argument("provider", choices=["jira", "ado", "dataverse"])
    p_add.add_argument("name", help="Connection name (e.g. 'main', 'partner')")
    p_add.add_argument("--server", help="Jira server URL")
    p_add.add_argument("--email", help="Jira email")
    p_add.add_argument("--api-token", dest="api_token", help="Jira API token")
    p_add.add_argument("--organization", help="ADO organization URL")
    p_add.add_argument("--project", help="ADO project name")
    p_add.add_argument("--tenant-id", dest="tenant_id", help="Azure tenant ID (ADO/Dataverse)")

    p_rm = sub.add_parser("remove-connection", help="Remove a named connection")
    p_rm.add_argument("provider", choices=["jira", "ado", "dataverse"])
    p_rm.add_argument("name")

    p_def = sub.add_parser("set-default", help="Set default connection for a provider")
    p_def.add_argument("provider", choices=["jira", "ado", "dataverse"])
    p_def.add_argument("name")

    sub.add_parser("list-connections", help="List all connections (secrets masked)")

    p_ws = sub.add_parser("init-workspace", help="Create/update ops/opskit.json")
    p_ws.add_argument("--environment-url", dest="environment_url", help="Dataverse environment URL")
    p_ws.add_argument("--jira", help="Jira connection name")
    p_ws.add_argument("--ado", help="ADO connection name")
    p_ws.add_argument("--dataverse", help="Dataverse connection name")

    args = parser.parse_args()

    dispatch = {
        "setup": cmd_setup,
        "status": cmd_status,
        "check": cmd_check,
        "add-connection": cmd_add_connection,
        "remove-connection": cmd_remove_connection,
        "set-default": cmd_set_default,
        "list-connections": cmd_list_connections,
        "init-workspace": cmd_init_workspace,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

