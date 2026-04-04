---
name: workflow_group_match
description: Use when deciding whether workflow evidence matches an existing workflow group or should create a new one.
---

# Workflow Group Match

## Purpose

Decide whether workflow evidence matches an existing workflow group or should create a new one.

## Inputs

- `transcript_name`
- `workflow_summary`
- `existing_groups`

## Outputs

- `matched_existing_title`
- `recommended_title`
- `recommended_slug`
- `confidence`
- `rationale`

## Rules

- only match an existing workflow when the operational workflow is materially the same
- do not merge workflows based only on broad domain overlap
- `matched_existing_title` must be one exact existing group title or `null`
- keep `recommended_slug` in lowercase kebab-case
- confidence must be one of `high`, `medium`, `low`, `unknown`
