---
name: configure
description: |
  Configure OpsKit provider connections and workspace settings. Use to set up Jira, Azure DevOps, and Dataverse connections, or to initialize a workspace for a customer environment.

  Usage: /configure
  Example: /configure
---

Configure OpsKit. $ARGUMENTS

## Step 1 — Check current status

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py status
```

Read the output. Identify which providers show ✗ (not configured) and which show ✓ (ready).

## Step 2 — Determine what to configure

Based on the status output and the user's request, decide what needs setup:

- **If no connections exist at all**: guide the user through first-time setup (Step 3)
- **If the user asked about a specific provider**: jump to that provider in Step 3
- **If connections are ready but no workspace config**: jump to Step 4
- **If everything is configured**: show the status and ask if the user wants to change anything

## Step 3 — Configure provider connections

Ask the user which providers they need, then collect values **one provider at a time** via conversation. After collecting values, run the non-interactive command.

### Jira

Ask for: server URL, email, API token. Mention they can create a token at https://id.atlassian.com/manage-profile/security/api-tokens

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection jira <name> \
  --server "<server_url>" \
  --email "<email>" \
  --api-token "<api_token>"
```

### Azure DevOps

Ask for: organization URL (e.g. `https://dev.azure.com/yourorg`), project name, and optionally tenant ID.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection ado <name> \
  --organization "<org_url>" \
  --project "<project>" \
  --tenant-id "<tenant_id>"
```

Remind the user to run `az login` if they haven't authenticated yet.

### Dataverse

Ask for: tenant ID. Environment URL is set per-workspace (Step 4).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py add-connection dataverse <name> \
  --tenant-id "<tenant_id>"
```

Also ensure the virtual environment is set up:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py setup
```

Remind the user to run `az login` if they haven't authenticated yet.

### Connection naming

- Default name is `main` for the first connection of each provider
- Use descriptive names for additional connections (e.g. `partner`, `staging`)

## Step 4 — Initialize workspace

If the user is working with a specific customer environment, create the workspace config:

Ask for: environment URL (e.g. `https://orgname.crm4.dynamics.com`), and which connection names to use (defaults to `main` for each).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py init-workspace \
  --environment-url "<url>" \
  --jira "<connection_name>" \
  --ado "<connection_name>" \
  --dataverse "<connection_name>"
```

## Step 5 — Verify

Run status again to confirm everything is ready:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py status
```

Report the result to the user.

## Important

- Collect sensitive values (API tokens) directly from the user — never guess or fabricate credentials
- The `--api-token` flag passes the value via command line arguments which may appear in process listings — this is acceptable for a local dev tool
- Connection names in the workspace (`ops/opskit.json`) must match names in `connections.json`
- If the user asks to reconfigure an existing connection, just run `add-connection` again with the same name — it overwrites
