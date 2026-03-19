# Scenario 04: Application Switching and Loops (Back-and-Forth)

## Problem Statement
Real processes switch apps and can loop:
- App1 -> App2 -> App1 -> App3
- rework loops, retries, validations

Linear lists become confusing; we need a representation that can handle loops.

## Key Principles
- Keep canonical list for export, but store enough structure for loops.
- Support “loop” edges or markers for repeated steps.
- Preserve evidence for each loop instance.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  PROCESS_STEP ||--o{ STEP_EDGE : transitions

  PROCESS_STEP {
    uuid id
    uuid session_id
    uuid meeting_id
    string application_name
    string action_text
    string status
  }

  STEP_EDGE {
    uuid id
    uuid session_id
    uuid from_step_id
    uuid to_step_id
    string edge_type
    string condition
  }
```

## Logic (Loop-Friendly Canonicalization)
- Extract steps as a list (simple).
- If repeated patterns are detected:
  - create `edge_type=loop` from later step back to earlier step
  - annotate `condition` if transcript indicates (e.g. "if validation fails")
- For export:
  - keep the linear “happy path” list
  - optionally include “loop notes” separately

## Sequence Diagram (Loop Detection)
```mermaid
sequenceDiagram
  autonumber
  participant API as Backend
  participant DB as Postgres
  participant W as Worker

  API->>DB: Load extracted steps
  API->>W: Build canonical graph
  W->>W: Detect repeated sequence App1->App2->App1
  W->>DB: Save step edges (including loop)
  W->>DB: Save canonical list for export
  API-->>API: Return view model (list + loop markers)
```

## Notes
- Start with list + loop annotations; migrate to graph UI when needed.

