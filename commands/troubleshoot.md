---
name: troubleshoot
description: |
  Investigate a customer support ticket end-to-end. Gathers context from Jira, queries environment logs and data, inspects code, checks deployments, and produces structured documentation (findings, RCA, action plan) in an ops/<ticket-id>/ folder.

  Usage: /troubleshoot <ticket-id>
  Example: /troubleshoot TICKET-1234
  Without a ticket ID, runs in playground mode (ops/playground/).
---

Investigate ticket `$ARGUMENTS`.

## Phase 0 — Preflight

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py status
```

If any provider shows ✗, tell the user what's missing (the output includes setup instructions). **Only use skills whose providers are ✓ Ready.**

If the virtual environment is missing, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py setup` first.

Check for `ops/opskit.json`. If missing, ask the user for the environment URL and create it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py init-workspace --environment-url "<url>"
```

## Phase 1 — Initialize

1. Parse the ticket ID from the arguments. If empty, use `playground` and ask the user to describe the issue.
2. Create the output directory: `ops/<ticket-id>/` with `artifacts/logs/` and `artifacts/data/` subdirectories.
3. Fetch the ticket via the `query-service-tickets` skill. If the fetch fails, ask the user for manual context.

## Phase 2 — Gather

Use the available OpsKit skills to collect diagnostic data. Not all skills apply to every ticket — choose based on what the ticket describes.

### Parse the ticket for targets first

Extract concrete identifiers from the ticket before querying anything:
- **Resource names** (flows, plugins, entities, records, jobs)
- **Error messages** and status codes
- **Timestamps** of when the issue occurred
- **Environment URLs** or tenant details

Use these to make **targeted queries**. Do NOT run broad queries when the ticket names a specific resource.

### Gather evidence

1. **Fetch ticket details and comments** — `query-service-tickets` skill
2. **Query environment logs** — `query-environment-logs` skill (flow runs, plugin traces, audit logs, system jobs — pick based on issue type)
3. **Query environment data** — `query-environment-data` skill (inspect records, table schemas, data state)
4. **Inspect source code** — `inspect-code` skill (only if logs point to a specific component)
5. **Check deployments** — `list-deployments` skill (correlate with recent releases)

Save verbose raw outputs to `artifacts/logs/` or `artifacts/data/`. Redirect stderr when saving:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/... 2>/dev/null > ops/<ticket-id>/artifacts/logs/output.json
```

Refer to each skill's SKILL.md for detailed usage, arguments, and workflow tips.

## Phase 3 — Analyze & Document

1. Review all gathered evidence and identify patterns.
2. Write `findings.md` — the primary output (see template below).
3. **Present findings to the user.** Summarize what you found, your hypotheses, and confidence level. Ask for input before proceeding.
4. Write `rca.md` **only** when you have concrete evidence for a root cause. Ask the user first.
5. Write `action-plan.md` **only** when the user explicitly requests it.

## Output: findings.md

```markdown
# <Ticket ID> — <One-line summary>

## Ticket
- **Reporter**: ...
- **Created**: ...
- **Priority**: ...
- **Description**: <3-4 line summary>

## Evidence

### <Data source queried>
<Raw findings: error messages, status codes, timestamps, record IDs.
Quote actual data. Do NOT paraphrase.>

## Analysis
<Brief interpretation. What failed, why, what's unknown.
State confidence level. Mark hypotheses as "Hypothesis:".>

## Next Steps
<1-3 concrete actions.>
```

## Rules

- **Evidence only.** Do not generate speculative content, repro steps without evidence, risk matrices, or communication plans.
- **Read-only.** Never modify customer data, tickets, or code.
- **Ask the user** when you need environment URLs, credentials, or customer identification.
