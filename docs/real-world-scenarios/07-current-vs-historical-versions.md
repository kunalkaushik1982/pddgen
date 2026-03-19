# Scenario 07: Current vs Historical Process Versions

## Problem Statement
Sometimes BA wants only current process; sometimes enterprise wants historical versions too ("what changed and when").

## Key Principles
- Start with “current-only canonical” but keep enough metadata to upgrade to history.
- Historical versioning is a filter + snapshot, not a rewrite.
- Steps are immutable in meaning; status indicates validity.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  DRAFT_SESSION ||--o{ PROCESS_VERSION : has
  PROCESS_VERSION ||--o{ PROCESS_STEP_SNAPSHOT : includes

  PROCESS_VERSION {
    uuid id
    uuid session_id
    int version_number
    datetime created_at
    string created_by
    string reason
  }

  PROCESS_STEP_SNAPSHOT {
    uuid id
    uuid version_id
    uuid step_id
    string action_text
    string application_name
    string status
  }
```

## Logic (Versioning)
- Current-only mode:
  - show `status=active` steps only
- Historical mode:
  - create a new `process_version` snapshot on major updates (new meeting or BA finalize)
  - snapshot stores step ids + resolved text at that time
- Diff:
  - compare snapshot A vs snapshot B to show changes

## Sequence Diagram (Create Version Snapshot)
```mermaid
sequenceDiagram
  autonumber
  participant BA as BA User
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres

  BA->>UI: Finalize current process (create version)
  UI->>API: POST /process-versions
  API->>DB: Insert process_version
  API->>DB: Insert step snapshots for active steps
  API-->>UI: Version created
```

## Notes
- You can postpone `PROCESS_VERSION` until enterprise customers ask for audit/versioning.

