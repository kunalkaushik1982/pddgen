# Scenario 02: Contradictions Across Meetings (Reject/Supersede)

## Problem Statement
Meeting 1 states something, then Meeting 2 rejects or corrects it. We must keep the audit trail and still produce the latest correct process.

## Key Principles
- Never delete steps; change `status`.
- Canonical view filters `status=active`.
- A newer step can supersede an older step with a link + rationale.
- Latest wins by default, BA can override.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  PROCESS_STEP ||--o| PROCESS_STEP : supersedes

  PROCESS_STEP {
    uuid id
    uuid session_id
    uuid meeting_id
    string action_text
    string application_name
    string status
    uuid superseded_by_step_id
    string supersede_reason
  }
```

## Logic (Latest Wins + BA Validation)
- Detect conflict candidates:
  - same application + similar verb/entity, but materially different action text
  - explicit transcript language: "we do not do this anymore", "ignore what I said"
- Default merge rule:
  - newest meeting’s step => `active`
  - older step => `superseded` and `superseded_by_step_id` points to winner
- BA can override:
  - mark winner as `rejected` and revert older to `active`
  - mark older as `exception` (variant)

## Sequence Diagram (Supersede)
```mermaid
sequenceDiagram
  autonumber
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres
  participant W as Worker

  Note over UI: Meeting 2 uploaded with correction
  UI->>API: Start merge (session_id)
  API->>DB: Load steps from all meetings
  API->>W: Run merge algorithm (or internal service)
  W->>DB: Choose latest step as active
  W->>DB: Mark older step superseded + link to latest
  W-->>API: conflicts list
  API-->>UI: canonical(active) + conflicts

  Note over UI: BA reviews conflict
  UI->>API: POST conflict decision (accept latest / revert / exception)
  API->>DB: Update step statuses + rationale
  API-->>UI: updated canonical view
```

## Notes
- This scenario requires the smallest additional fields: `status`, `superseded_by_step_id`, and optional `reason`.

