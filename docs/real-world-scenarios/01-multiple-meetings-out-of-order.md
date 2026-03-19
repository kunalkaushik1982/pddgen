# Scenario 01: Multiple Meetings Uploaded Out Of Order

## Problem Statement
One process is recorded across multiple meetings. Meetings can be uploaded in any order (or later), but we still need a coherent sequence of process steps.

## Key Principles
- A `DraftSession` can contain multiple `Meetings`.
- Meeting order is explicit and editable (do not assume upload order).
- Steps always store provenance: `meeting_id` + evidence refs.
- Canonical process is derived from all meetings, not just one.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  DRAFT_SESSION ||--o{ MEETING : contains
  MEETING ||--o{ ARTIFACT : has
  MEETING ||--o{ PROCESS_STEP : produces

  MEETING {
    uuid id
    uuid session_id
    datetime meeting_date
    datetime uploaded_at
    int order_index
  }

  PROCESS_STEP {
    uuid id
    uuid session_id
    uuid meeting_id
    int extracted_order
    string application_name
    string action_text
    string status
  }
```

## Logic (Ordering Rules)
- Meeting order:
  - If `order_index` is set: sort by `order_index`.
  - Else if `meeting_date` exists: sort by `meeting_date`.
  - Else: sort by `uploaded_at`.
- Step order in canonical view:
  - Sort steps by (meeting order, `extracted_order`).
- BA can reorder meetings (sets `order_index`) to correct the sequence.

## Sequence Diagram (Upload Out Of Order)
```mermaid
sequenceDiagram
  autonumber
  participant BA as BA User
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres
  participant Q as Redis (broker)
  participant W as Worker
  participant ST as Storage

  Note over BA,UI: Meeting 2 is uploaded first (out of order)
  BA->>UI: Upload Meeting 2 transcript/video
  UI->>API: Create meeting + upload artifacts
  API->>ST: Save bytes
  API->>DB: Save meeting(uploaded_at) + artifacts
  UI->>API: Run extraction/merge
  API->>Q: Enqueue job(session_id, meeting_id=M2)
  Q-->>W: Deliver job
  W->>ST: Read transcript
  W->>DB: Persist steps with meeting_id=M2
  W->>DB: Build canonical ordering (only M2 so far)

  Note over BA,UI: Meeting 1 arrives later
  BA->>UI: Upload Meeting 1 transcript/video
  UI->>API: Create meeting + upload artifacts
  API->>DB: Save meeting(uploaded_at) + artifacts
  UI->>API: Run extraction/merge
  API->>Q: Enqueue job(session_id, meeting_id=M1)
  Q-->>W: Deliver job
  W->>DB: Persist steps with meeting_id=M1
  W->>DB: Recompute canonical using meeting order rules

  BA->>UI: Reorder meetings (drag/drop)
  UI->>API: PATCH meeting order_index
  API->>DB: Update order_index
  API->>DB: Recompute canonical ordering
```

## Notes
- This scenario is solved primarily by having a first-class `Meeting` entity and explicit ordering.

