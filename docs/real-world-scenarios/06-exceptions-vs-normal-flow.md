# Scenario 06: Exceptions vs Normal Flow

## Problem Statement
Meeting 2 might say: "Normally we do X, but for special cases we do Y." We must represent both without losing clarity.

## Key Principles
- Default view shows normal flow.
- Exceptions are attached as conditional branches.
- BA can classify a step as `normal` or `exception`.

## Data Model (Conceptual ER)
```mermaid
erDiagram
  PROCESS_STEP ||--o{ STEP_VARIANT : has

  STEP_VARIANT {
    uuid id
    uuid session_id
    uuid base_step_id
    string variant_type
    string condition
    string action_text
    string status
  }
```

## Logic (Branching)
- Canonical base step stays `active` in normal flow.
- Exception steps become variants:
  - `variant_type=exception`
  - `condition` captured from transcript or BA
- Export:
  - include exceptions in a dedicated “Exceptions” section, or inline with condition text.

## Sequence Diagram (BA Classifies Exception)
```mermaid
sequenceDiagram
  autonumber
  participant UI as Frontend
  participant API as Backend
  participant DB as Postgres

  UI->>API: Mark step as exception + set condition
  API->>DB: Insert/update step_variant(exception)
  API-->>UI: Updated view model (normal + exceptions)
```

## Notes
- This is optional until you see repeated exception patterns.

