# Scenario 05: Incremental Session Updates (Add Meetings After DOC Generated)

## Problem Statement
User generates a draft after Meeting 1, then later adds Meeting 2/3 to the same session and wants the session to update.

## Key Principles
- Session is mutable; canonical steps can be recomputed.
- Exports should be versioned (store output documents and timestamps).
- Adding meetings triggers re-merge and creates a new review state.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  DRAFT_SESSION ||--o{ MEETING : contains
  DRAFT_SESSION ||--o{ OUTPUT_DOCUMENT : exports

  OUTPUT_DOCUMENT {
    uuid id
    uuid session_id
    string kind
    string storage_path
    datetime exported_at
    string based_on_meeting_set_hash
  }
```

## Logic (Recompute + Keep Exports)
- When new meeting is added:
  - recompute canonical steps
  - session status moves back to `review` (if it was `exported`)
  - existing exports remain in history (do not overwrite)
- Export action creates new `output_document` row.

## Sequence Diagram (Add Meeting After Export)
```mermaid
sequenceDiagram
  autonumber
  participant BA as BA User
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres
  participant W as Worker

  Note over UI: Session already has export
  BA->>UI: Upload Meeting 2 to existing session
  UI->>API: Create meeting + upload artifacts
  API->>DB: Save meeting + artifacts
  API->>W: Recompute canonical steps
  W->>DB: Mark superseded/active steps as needed
  W->>DB: Set session status=review
  API-->>UI: Updated session for review

  BA->>UI: Export again
  UI->>API: POST export
  API->>DB: Insert new output_document(exported_at)
  API-->>UI: download bytes
```

## Notes
- This enables “living sessions” without losing previous documents.

