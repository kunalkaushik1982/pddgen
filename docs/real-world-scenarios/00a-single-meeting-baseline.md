# Scenario 00a: Single Meeting Baseline (Current App Approach)

## Problem Statement
One process recording is captured in a single meeting:
- one video recording (optional)
- one transcript
- one template

Goal:
- extract steps + notes
- show review UI (steps/diagram/ask)
- export DOCX/PDF

This is the current baseline flow your app supports.

---

## Key Principles
- One `DraftSession` is the unit of work.
- Artifacts belong to the session.
- Worker generates draft steps asynchronously.
- BA can edit steps and diagrams before export.
- Exports are generated on demand and stored as output documents.

---

## Data Model (Conceptual ER)
```mermaid
erDiagram
  USER ||--o{ DRAFT_SESSION : owns
  DRAFT_SESSION ||--o{ ARTIFACT : contains
  DRAFT_SESSION ||--o{ PROCESS_STEP : has
  DRAFT_SESSION ||--o{ PROCESS_NOTE : has
  DRAFT_SESSION ||--o{ OUTPUT_DOCUMENT : exports
  DRAFT_SESSION ||--o{ ACTION_LOG : logs

  USER {
    uuid id
    string username
  }

  DRAFT_SESSION {
    uuid id
    string title
    string owner_id
    string status
    string diagram_type
  }

  ARTIFACT {
    uuid id
    uuid session_id
    string kind
    string name
    string storage_path
  }

  PROCESS_STEP {
    uuid id
    uuid session_id
    int step_number
    string application_name
    string action_text
  }
```

---

## Logic (Baseline Workflow)

### Upload prerequisites
Minimum required artifacts for generation:
- transcript
- video
- template

### Generation (async)
- Backend marks session `processing` and enqueues a worker task.
- Worker reads transcript from storage and extracts:
  - `process_steps`
  - `process_notes`
  - screenshot mappings/candidates (if available)
- Worker sets session status to `review`.

### Review + edit
- BA can edit:
  - process steps text/metadata
  - diagram layout/model
  - screenshot selection order

### Export
- Backend renders DOCX/PDF using:
  - stored template
  - steps/notes
  - optional saved diagram image
- Stores output document metadata and returns bytes for download.

---

## Sequence Diagram (Single Meeting Happy Path)
```mermaid
sequenceDiagram
  autonumber
  participant BA as BA User
  participant UI as Frontend
  participant API as Backend API
  participant DB as Postgres
  participant Q as Redis Broker
  participant W as Worker
  participant ST as Storage

  BA->>UI: Create session
  UI->>API: POST /uploads/sessions (Cookie+CSRF)
  API->>DB: Insert draft_session(status=draft)
  API-->>UI: 201 session_id

  BA->>UI: Upload transcript/video/template
  UI->>API: POST /uploads/sessions/{id}/artifacts (Cookie+CSRF + file)
  API->>ST: Save bytes
  API->>DB: Insert artifact metadata
  API-->>UI: 201

  BA->>UI: Generate draft
  UI->>API: POST /draft-sessions/{id}/generate (Cookie+CSRF)
  API->>DB: status=processing + action log
  API->>Q: Enqueue task(session_id)
  Q-->>W: Deliver task
  W->>ST: Read transcript bytes
  W->>DB: Persist steps/notes + status=review
  API-->>UI: 202

  BA->>UI: Review steps/diagram
  UI->>API: GET /draft-sessions/{id}
  API->>DB: Load session detail
  API-->>UI: 200

  BA->>UI: Edit steps/diagram
  UI->>API: PATCH steps / PUT diagram layout/model (Cookie+CSRF)
  API->>DB: Update rows + logs
  API-->>UI: 200

  BA->>UI: Export DOCX/PDF
  UI->>API: POST /exports/{id}/docx/download (Cookie+CSRF)
  API->>DB: Load session + artifacts
  API->>ST: Materialize assets and render output
  API->>DB: Insert output_document + status=exported
  API-->>UI: 200 bytes
```

---

## Notes
This is the simplest production-ready flow.
Multi-meeting support extends this baseline by adding:
- a `Meeting` entity
- per-meeting extraction + merge into a canonical process

