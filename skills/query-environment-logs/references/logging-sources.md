# Environment Logging Sources

## Flow Run History

**Entity:** `flowrun`
**Entity Set:** `flowruns`
**Table Type:** Elastic (Azure Cosmos DB)

Cloud flow execution history stored in Dataverse. Each cloud flow execution creates an entry in this table. Only solution cloud flows (with definitions in Dataverse) have their run history stored here. Data is partitioned by user and has a default TTL of 28 days.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Primary key — logic app ID of the flow run |
| `status` | String | End result: `Succeeded`, `Failed`, `Cancelled` |
| `starttime` | DateTime | When the flow execution was triggered |
| `endtime` | DateTime | When the flow execution finished |
| `duration` | BigInt | Duration in milliseconds |
| `triggertype` | String | `Automated`, `Scheduled`, `Instant` |
| `errorcode` | String | Error code (e.g., `Terminated`) if failed |
| `errormessage` | String | Detailed error message JSON if failed |
| `workflowid` | Guid | WorkflowID of the cloud flow |
| `partitionid` | String | User partition in the elastic table |

### Elastic Table Notes
- This is an **elastic table** — SQL queries return extra columns and ignore `$select`. Use OData for reliable results.
- Data is partitioned by user — each user has a dedicated partition.
- `$expand` (JOINs) is not supported on elastic tables.
- Default retention: 28 days (configurable via `FlowRunTimeToLiveInSeconds` in the Organization table).

### References
- [FlowRun entity reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/flowrun)
- [Cloud flow run metadata](https://learn.microsoft.com/en-us/power-automate/dataverse/cloud-flow-run-metadata)

## Plugin Trace Logs

**Entity:** `plugintracelog`
**Entity Set:** `plugintracelogs`
**Table Type:** Standard

Captures execution traces from custom plugins and workflow activities. Includes trace output, exception details, and performance timing.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `typename` | String | Plugin type name (fully qualified assembly name) |
| `messagename` | String | Message that triggered the plugin (Create, Update, etc.) |
| `primaryentity` | String | Entity the plugin ran against |
| `exceptiondetails` | Memo | Error message and stack trace (if failed) |
| `messageblock` | Memo | Trace log output from the plugin |
| `performanceexecutionstarttime` | DateTime | When execution started |
| `performanceexecutionduration` | Integer | Execution duration in milliseconds |
| `depth` | Integer | Plugin execution depth |
| `operationtype` | Picklist | 0 = Unknown, 1 = Plug-in, 2 = Workflow Activity |
| `mode` | Picklist | 0 = Synchronous, 1 = Asynchronous |
| `correlationid` | Guid | Unique identifier for tracking execution |

### Requirements
- Plugin Trace Logging must be enabled: Settings → Administration → System Settings → Customization → Plugin and custom workflow activity tracing → All / Exception

### References
- [PluginTraceLog entity reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/plugintracelog)
- [Logging and tracing](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/logging-tracing)

## Audit Logs

**Entity:** `audit`
**Entity Set:** `audits`
**Table Type:** Standard

Tracks data changes across the system — who changed what, when.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `objecttypecode` | String | Entity logical name (e.g., `contact`, `account`) |
| `action` | Picklist | 1=Create, 2=Update, 3=Delete |
| `operation` | Picklist | 1=Create, 2=Update, 3=Delete |
| `createdon` | DateTime | When the change occurred |
| `_userid_value` | Lookup | User who made the change |
| `_objectid_value` | Lookup | Record that was changed |
| `changedata` | String | JSON with changed attributes (oldValue/newValue) |

### Requirements
- Auditing must be enabled globally and per-entity

## System Jobs (Async Operations)

**Entity:** `asyncoperation`
**Entity Set:** `asyncoperations`
**Table Type:** Standard

Background system jobs including workflows, bulk operations, and solution imports.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Job name |
| `operationtype` | Picklist | Type of operation (1=Workflow, 10=Recurring Workflow, etc.) |
| `statuscode` | Picklist | 0=WaitingForResources, 10=Waiting, 20=InProgress, 21=Pausing, 22=Canceling, 30=Succeeded, 31=Failed, 32=Canceled |
| `createdon` | DateTime | When the job was created |
| `startedon` | DateTime | When processing started |
| `completedon` | DateTime | When processing completed |
| `message` | Memo | Full error message with plugin trace and stack trace |
| `friendlymessage` | String | User-friendly error summary |
