---
name: troubleshoot
description: |
  Investigate a customer support ticket end-to-end. Gathers context from Jira, queries environment logs and data, inspects code, checks deployments, and produces structured documentation (context, investigation log, repro steps, RCA, action plan) in an ops/<ticket-id>/ folder.

  Usage: /troubleshoot <ticket-id>
  Example: /troubleshoot CASE-1234
  Without a ticket ID, runs in playground mode (ops/playground/).
agent: troubleshooter
---

Investigate ticket `$ARGUMENTS`.

## Workflow

Follow these phases in order. Pause after the Analyze phase to present findings before writing final documentation.

### Phase 1 — Initialize

1. Parse the ticket ID from the arguments. If empty, use `playground` as the identifier and ask the user to describe the issue.
2. Create the output directory structure: `ops/<ticket-id>/` with subdirectories `artifacts/logs/`, `artifacts/data/`, `artifacts/screenshots/`.
3. Fetch the ticket from Jira (details, comments, attachments). If the ticket fetch fails, ask the user for manual context.
4. Write `context.md` with all ticket metadata, customer info, environment details, and recent comments.

### Phase 2 — Gather

Based on the ticket content, collect relevant diagnostic data. Not all steps apply to every ticket — use judgment.

1. **Identify the customer and environment** — Use list-environments to find environment URLs and tenant details. Update `context.md` with environment info.
2. **Query logs** — Based on the issue type:
   - Flow failures: query failed flow runs, drill into action details
   - Plugin errors: query plugin trace logs around the failure timeframe
   - Data anomalies: query audit logs for the affected entity
3. **Inspect code** — If logs reference specific plugins or components, look up the source code.
4. **Check deployments** — List recent deployments to see if the issue correlates with a release.
5. **Save raw outputs** — Store verbose log data in `artifacts/logs/` and data exports in `artifacts/data/`.
6. **Update investigation.md** — Log each step chronologically as you go (what you queried, what you found, what it means).

### Phase 3 — Analyze

1. Review all gathered evidence and identify patterns.
2. Form one or more hypotheses about the root cause.
3. Cross-reference findings (e.g., did the error start after a specific deployment? Does the code match the error in the logs?).
4. **Present findings to the user** — Summarize what you found, your hypotheses, and confidence level. Ask for input before proceeding.

### Phase 4 — Document

After the user confirms or provides additional input:

1. Write `repro-steps.md` — Clear steps to reproduce, expected vs actual behavior.
2. Write `rca.md` — Root cause statement, evidence, contributing factors, impact analysis.
3. Write `action-plan.md` — Immediate, short-term, and long-term actions with verification steps.

### Phase 5 — Review

Present a summary of all generated documents. Ask the user if any section needs refinement. Make adjustments as requested.
