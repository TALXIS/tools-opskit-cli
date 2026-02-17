# Environment Logging Sources

## Plugin Trace Logs

**Entity:** `plugintracelog`  
**Entity Set:** `plugintracelogs`

Captures execution traces from custom plugins and workflow activities.

### Key Fields

| Field | Description |
|-------|-------------|
| `typename` | Plugin type name |
| `messagename` | Message that triggered the plugin (Create, Update, etc.) |
| `primaryentity` | Entity the plugin ran against |
| `exceptiondetails` | Error message and stack trace (if failed) |
| `messageblock` | Trace log output from the plugin |
| `performanceexecutionstarttime` | When execution started |
| `depth` | Plugin execution depth |
| `operationtype` | 0 = Unknown, 1 = Plug-in |

### Requirements
- Plugin Trace Logging must be enabled: Settings → Administration → System Settings → Customization → Plugin and custom workflow activity tracing → All / Exception

## Audit Logs

**Entity:** `audit`  
**Entity Set:** `audits`

Tracks data changes across the system.

### Key Fields

| Field | Description |
|-------|-------------|
| `objecttypecode` | Entity logical name |
| `action` | 1=Create, 2=Update, 3=Delete |
| `operation` | 1=Create, 2=Update, 3=Delete |
| `createdon` | When the change occurred |
| `userid` | User who made the change |
| `changedata` | JSON with old/new values |

### Requirements
- Auditing must be enabled globally and per-entity

## Flow Run History (Flow Sessions)

**Entity:** `flowsession`  
**Entity Set:** `flowsessions`

Cloud flow execution history.

### Key Fields

| Field | Description |
|-------|-------------|
| `regardingobjectid` | The flow (workflow) that ran |
| `startedon` | When the run started |
| `completedon` | When the run completed |
| `statuscode` | 0=NotSpecified, 1=Paused, 2=Running, 3=Waiting, 4=Succeeded, 5=Skipped, 6=Suspended, 7=Cancelled, 8=Failed |
| `errorcode` | Error code if failed |
| `errormessage` | Error message if failed |

## System Jobs (Async Operations)

**Entity:** `asyncoperation`  
**Entity Set:** `asyncoperations`

Background system jobs including workflows, bulk operations, and solution imports.

### Key Fields

| Field | Description |
|-------|-------------|
| `name` | Job name |
| `operationtype` | Type of operation |
| `statuscode` | 0=WaitingForResources, 10=Waiting, 20=InProgress, 21=Pausing, 22=Canceling, 30=Succeeded, 31=Failed, 32=Canceled |
| `createdon` | When the job was created |
| `startedon` | When processing started |
| `completedon` | When processing completed |
| `message` | Status/error message |
| `friendlymessage` | User-friendly error message |
