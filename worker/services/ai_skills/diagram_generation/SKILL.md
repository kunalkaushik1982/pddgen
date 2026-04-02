# Diagram Generation

## Purpose

Generate overview and detailed flowchart graph models for the session.

## Inputs

- `session_title`
- `diagram_type`
- `steps`
- `notes`

## Outputs

- `overview`
- `detailed`

## Rules

- preserve one connected workflow per view
- only allow `process` and `decision` node categories
- only use `decision` when branching is explicit in the evidence
- keep overview compact and business-oriented
- keep detailed flow aligned with discovered business action order
