---
name: workflow_boundary_detection
description: Use when classifying whether two adjacent evidence segments belong to the same workflow, a new workflow, or remain uncertain.
---

# Workflow Boundary Detection

## Purpose

Classify whether two adjacent evidence segments belong to the same workflow, a new workflow, or remain uncertain.

## Inputs

- `left_segment`
- `right_segment`

## Outputs

- `decision`
- `confidence`
- `rationale`

## Rules

- `decision` must be one of `same_workflow`, `new_workflow`, or `uncertain`
- use workflow continuity signals from both segments only
- prefer `same_workflow` only when continuity is clear
- prefer `new_workflow` only when the segments indicate materially different business activity
- use `uncertain` when evidence conflicts or remains ambiguous
- confidence must be one of `high`, `medium`, `low`, `unknown`
