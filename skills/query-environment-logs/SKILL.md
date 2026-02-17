---
name: query-environment-logs
description: Read logs from a Power Platform environment including plugin trace logs, audit logs, flow run history, and system jobs. Use when diagnosing issues, investigating errors, or reviewing environment activity.
allowed-tools: Bash(python:*)
---

# Query Environment Logs

Read and analyze various logs from a specific Power Platform environment.

## Prerequisites

- Python with dependencies from `requirements.txt` installed
- Environment URL and authentication credentials (use the **retrieve-secrets** skill)

## Workflow

1. **Identify the target environment** — ask the user which environment to investigate.
2. **Obtain credentials** — use the **retrieve-secrets** skill.
3. **Determine log type** — ask what kind of logs are needed (plugin traces, audit, flows, etc.).
4. **Query logs** — run the appropriate query against the environment.
5. **Analyze and summarize** — present findings with relevant context.

## Usage

```bash
# Query plugin trace logs
python skills/query-environment-logs/scripts/query_logs.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --log-type plugin-trace \
  --since "2024-01-01T00:00:00Z" \
  --top 50

# Query audit logs
python skills/query-environment-logs/scripts/query_logs.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --log-type audit \
  --entity "account" \
  --since "2024-01-01T00:00:00Z"

# Query flow run history
python skills/query-environment-logs/scripts/query_logs.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --log-type flow-runs \
  --status failed \
  --top 20

# Query system jobs
python skills/query-environment-logs/scripts/query_logs.py \
  --environment-url "https://org.crm4.dynamics.com" \
  --log-type system-jobs \
  --status failed
```

### Log Types

| Type | Description |
|------|-------------|
| `plugin-trace` | Plugin execution trace logs with error details and stack traces |
| `audit` | Entity change audit trail — who changed what, when |
| `flow-runs` | Power Automate cloud flow execution history |
| `system-jobs` | Background system job status and errors (workflows, bulk operations) |

## Important

- **Read-only** — never modify or clear logs
- Plugin trace logging must be enabled in the environment for `plugin-trace` logs
- Audit logging must be enabled for the relevant entities for `audit` logs
- Use `--since` and `--top` to limit result size

## Reference

See [Logging sources reference](references/logging-sources.md) for details on each log type.
