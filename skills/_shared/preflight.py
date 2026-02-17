"""Provider preflight checks and config management — stdlib only (runs before venv)."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PLUGIN_ROOT / "config.json"
CONNECTIONS_PATH = PLUGIN_ROOT / "connections.json"
VENV_DIR = PLUGIN_ROOT / ".venv"

_TOKEN_CREATE_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"


def _workspace_config_path() -> Path:
    """Return path to ops/opskit.json in the current working directory."""
    return Path.cwd() / "ops" / "opskit.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


@dataclass
class ProviderStatus:
    name: str
    ready: bool
    checks: List[Check] = field(default_factory=list)
    instructions: str = ""


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"defaults": {}}


def save_config(data: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_connections() -> Dict[str, Any]:
    if CONNECTIONS_PATH.exists():
        with open(CONNECTIONS_PATH, "r") as f:
            return json.load(f)
    return {}


def save_connections(data: Dict[str, Any]) -> None:
    with open(CONNECTIONS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(CONNECTIONS_PATH, 0o600)
    except OSError:
        pass


def load_workspace() -> Dict[str, Any]:
    path = _workspace_config_path()
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_workspace(data: Dict[str, Any]) -> None:
    path = _workspace_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Connection resolution
# ---------------------------------------------------------------------------


def resolve_connection(provider: str, cli_overrides: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Resolve the effective connection for a provider.

    Resolution order:
    1. CLI flag overrides (passed in directly)
    2. Workspace config (ops/opskit.json — connection name → connections.json)
    3. Global defaults (config.json — default connection → connections.json)
    4. Environment variables (JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN)
    """
    connections = load_connections()
    workspace = load_workspace()
    config = load_config()

    # Determine which named connection to use
    conn_name = (
        workspace.get("connections", {}).get(provider)
        or config.get("defaults", {}).get(provider)
    )

    conn = {}
    if conn_name:
        conn = connections.get(provider, {}).get(conn_name, {})

    # Workspace-level environment_url applies to dataverse
    if provider == "dataverse" and workspace.get("environment_url"):
        conn.setdefault("environment_url", workspace["environment_url"])

    # Env var fallbacks (Jira only — ADO/Dataverse use Azure CLI)
    if provider == "jira":
        if not conn.get("server"):
            conn["server"] = os.environ.get("JIRA_SERVER", "")
        if not conn.get("email"):
            conn["email"] = os.environ.get("JIRA_EMAIL", "")
        if not conn.get("api_token"):
            conn["api_token"] = os.environ.get("JIRA_API_TOKEN", "")

    # CLI overrides always win
    if cli_overrides:
        for k, v in cli_overrides.items():
            if v:
                conn[k] = v

    return conn


# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------


def _az_cli_available() -> bool:
    return shutil.which("az") is not None


def _az_logged_in() -> Optional[str]:
    """Check if Azure CLI is logged in. Returns account name or None."""
    if not _az_cli_available():
        return None
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _az_devops_extension_installed() -> bool:
    if not _az_cli_available():
        return False
    try:
        result = subprocess.run(
            ["az", "extension", "show", "--name", "azure-devops", "-o", "json"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Venv / package checks
# ---------------------------------------------------------------------------


def _venv_python() -> Optional[Path]:
    if sys.platform == "win32":
        p = VENV_DIR / "Scripts" / "python.exe"
    else:
        p = VENV_DIR / "bin" / "python3"
    return p if p.exists() else None


def _venv_has_packages() -> bool:
    """Check if required Dataverse packages are importable from the venv."""
    vpy = _venv_python()
    if not vpy:
        return False
    try:
        result = subprocess.run(
            [str(vpy), "-c", "import azure.identity; import PowerPlatform.Dataverse"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Provider checks
# ---------------------------------------------------------------------------


def check_jira() -> ProviderStatus:
    conn = resolve_connection("jira")
    checks = []

    has_server = bool(conn.get("server"))
    checks.append(Check(
        "Server URL",
        has_server,
        conn["server"] if has_server else "not configured",
    ))

    has_email = bool(conn.get("email"))
    checks.append(Check(
        "Email",
        has_email,
        conn["email"] if has_email else "not configured",
    ))

    has_token = bool(conn.get("api_token"))
    checks.append(Check(
        "API token",
        has_token,
        "configured" if has_token else "not configured",
    ))

    ready = has_server and has_email and has_token
    instructions = ""
    if not ready:
        lines = ["To configure Jira:"]
        lines.append(f"  python3 {PLUGIN_ROOT}/scripts/bootstrap.py add-connection jira <name>")
        lines.append("")
        lines.append("Or set environment variables:")
        lines.append("  JIRA_SERVER=https://yourcompany.atlassian.net")
        lines.append("  JIRA_EMAIL=you@company.com")
        lines.append("  JIRA_API_TOKEN=<token>")
        lines.append(f"  Create a token at: {_TOKEN_CREATE_URL}")
        instructions = "\n".join(lines)

    return ProviderStatus("jira", ready, checks, instructions)


def check_ado() -> ProviderStatus:
    conn = resolve_connection("ado")
    checks = []

    az_found = _az_cli_available()
    checks.append(Check(
        "Azure CLI",
        az_found,
        "installed" if az_found else "not found",
    ))

    ext_ok = _az_devops_extension_installed()
    checks.append(Check(
        "azure-devops extension",
        ext_ok,
        "installed" if ext_ok else "not installed",
    ))

    az_user = _az_logged_in()
    checks.append(Check(
        "Azure CLI login",
        az_user is not None,
        az_user or "not logged in",
    ))

    has_org = bool(conn.get("organization"))
    checks.append(Check(
        "Organization",
        has_org,
        conn.get("organization", "not configured"),
    ))

    has_project = bool(conn.get("project"))
    checks.append(Check(
        "Project",
        has_project,
        conn.get("project", "not configured"),
    ))

    ready = all(c.passed for c in checks)
    instructions = ""
    if not ready:
        lines = ["To configure Azure DevOps:"]
        step = 1
        if not az_found:
            lines.append(f"  {step}. Install Azure CLI: https://aka.ms/install-azure-cli")
            step += 1
        if not ext_ok:
            lines.append(f"  {step}. az extension add --name azure-devops")
            step += 1
        if not az_user:
            lines.append(f"  {step}. az login")
            step += 1
        if not has_org or not has_project:
            lines.append(f"  {step}. python3 {PLUGIN_ROOT}/scripts/bootstrap.py add-connection ado <name>")
        instructions = "\n".join(lines)

    return ProviderStatus("ado", ready, checks, instructions)


def check_dataverse() -> ProviderStatus:
    conn = resolve_connection("dataverse")
    checks = []

    vpy = _venv_python()
    checks.append(Check(
        "Virtual environment",
        vpy is not None,
        str(vpy) if vpy else "not created",
    ))

    pkgs = _venv_has_packages()
    checks.append(Check(
        "Dataverse packages",
        pkgs,
        "installed" if pkgs else "missing (azure-identity, PowerPlatform-Dataverse-Client)",
    ))

    az_user = _az_logged_in()
    checks.append(Check(
        "Azure CLI login",
        az_user is not None,
        az_user or "not logged in",
    ))

    has_tenant = bool(conn.get("tenant_id"))
    checks.append(Check(
        "Tenant ID",
        has_tenant,
        conn.get("tenant_id", "not configured"),
    ))

    has_env_url = bool(conn.get("environment_url"))
    checks.append(Check(
        "Environment URL",
        has_env_url,
        conn.get("environment_url", "set per workspace in ops/opskit.json"),
    ))

    # Ready if venv + packages + az login. Tenant and env URL are helpful but not blocking.
    ready = (vpy is not None) and pkgs and (az_user is not None)
    instructions = ""
    if not ready:
        lines = ["To configure Dataverse:"]
        step = 1
        if not vpy or not pkgs:
            lines.append(f"  {step}. python3 {PLUGIN_ROOT}/scripts/bootstrap.py setup")
            step += 1
        if not az_user:
            lines.append(f"  {step}. az login")
            step += 1
        if not has_tenant:
            lines.append(f"  {step}. python3 {PLUGIN_ROOT}/scripts/bootstrap.py add-connection dataverse <name>")
        instructions = "\n".join(lines)

    return ProviderStatus("dataverse", ready, checks, instructions)


_PROVIDER_CHECKS = {
    "jira": check_jira,
    "ado": check_ado,
    "dataverse": check_dataverse,
}


def check_provider(name: str) -> ProviderStatus:
    fn = _PROVIDER_CHECKS.get(name)
    if not fn:
        return ProviderStatus(name, False, [], f"Unknown provider: {name}")
    return fn()


def check_all() -> Dict[str, ProviderStatus]:
    return {name: fn() for name, fn in _PROVIDER_CHECKS.items()}


# ---------------------------------------------------------------------------
# require_provider — call at script startup
# ---------------------------------------------------------------------------


def require_provider(name: str, cli_overrides: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Validate that a provider is configured. Returns resolved connection dict.
    Exits with setup instructions if not ready.
    """
    status = check_provider(name)
    if not status.ready:
        print(f"ERROR: {name} provider is not configured.\n", file=sys.stderr)
        for check in status.checks:
            mark = "✓" if check.passed else "✗"
            print(f"  {mark} {check.name}: {check.detail}", file=sys.stderr)
        if status.instructions:
            print(f"\n{status.instructions}", file=sys.stderr)
        sys.exit(1)
    return resolve_connection(name, cli_overrides)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

_PROVIDER_LABELS = {
    "jira": "Jira",
    "ado": "Azure DevOps",
    "dataverse": "Dataverse",
}


def print_status(statuses: Dict[str, ProviderStatus]) -> None:
    print("=== OpsKit Provider Status ===\n")
    for name, status in statuses.items():
        label = _PROVIDER_LABELS.get(name, name)
        mark = "✓" if status.ready else "✗"
        summary_parts = [c.detail for c in status.checks if c.passed and c.detail not in ("installed", "configured")]
        summary = ", ".join(summary_parts[:2]) if summary_parts else ""
        state = "Ready" if status.ready else "Not configured"
        # If az login passed but connection details are missing, be more precise
        if not status.ready:
            az_check = next((c for c in status.checks if c.name == "Azure CLI login"), None)
            if az_check and az_check.passed:
                state = "Not connected (az login: ✓)"
        line = f"{mark} {label:<16} {state}"
        if summary and status.ready:
            line += f" ({summary})"
        print(line)

        if not status.ready:
            for check in status.checks:
                if not check.passed:
                    print(f"    ✗ {check.name}: {check.detail}")
            if status.instructions:
                for inst_line in status.instructions.split("\n"):
                    print(f"    {inst_line}")
        print()

    # Workspace info
    ws = load_workspace()
    if ws:
        print("--- Workspace (ops/opskit.json) ---")
        if ws.get("environment_url"):
            print(f"  Environment URL: {ws['environment_url']}")
        ws_conns = ws.get("connections", {})
        if ws_conns:
            for prov, cname in ws_conns.items():
                print(f"  {prov} connection: {cname}")
        print()
    else:
        print("--- Workspace ---")
        print("  No ops/opskit.json found in current directory.")
        print("  Create one to set environment URL and connection overrides.\n")
