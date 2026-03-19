# Scenario 03: Multi-Application Chain (App1 -> App2 Validate -> App3 Insert)

## Problem Statement
A process spans multiple applications:
- input in App1
- validate in App2
- insert in App3

This chain might be revealed gradually across meetings.

## Key Principles
- Each step must store `application_name`.
- Canonical process must preserve cross-app ordering.
- Introducing a new validation app in later meetings should insert steps, not just append.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  PROCESS_STEP ||--o{ STEP_LINK : next
  PROCESS_STEP {
    uuid id
    uuid session_id
    uuid meeting_id
    int canonical_order
    string application_name
    string action_text
    string status
  }
  STEP_LINK {
    uuid id
    uuid session_id
    uuid from_step_id
    uuid to_step_id
    string link_type
  }
```

## Logic (Insert Intermediate App Steps)
- When a new meeting introduces an intermediate validation app:
  - detect “before/after” anchors (App1 input, App3 insert)
  - insert App2 validation steps between the anchored steps
- If anchors are not clear:
  - flag as conflict/ambiguity for BA reordering

## Sequence Diagram (Later Meeting Adds App2)
```mermaid
sequenceDiagram
  autonumber
  participant BA as BA User
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres
  participant W as Worker

  Note over BA,UI: Meeting 1 says App1 -> App3
  BA->>UI: Upload Meeting 1 transcript
  UI->>API: Extract steps
  API->>DB: Save steps(App1, App3) as active

  Note over BA,UI: Meeting 2 adds App2 validation
  BA->>UI: Upload Meeting 2 transcript
  UI->>API: Extract steps
  API->>W: Merge canonical
  W->>DB: Detect anchors (App1 input, App3 insert)
  W->>DB: Insert App2 validation steps in between
  W->>DB: Mark replaced ordering as superseded if needed
  API-->>UI: Updated canonical order + conflicts (if any)
```

## Notes
- The `STEP_LINK` entity is optional initially; you can keep a linear list with `canonical_order`.
- Introducing explicit links later makes diagrams/branches easier.

