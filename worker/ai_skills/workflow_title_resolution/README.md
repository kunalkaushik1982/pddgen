---
name: workflow_title_resolution
description: Use when resolving a stable business workflow title and canonical slug from aggregated workflow evidence.
---

# Workflow Title Resolution

## Purpose

Resolve a stable business workflow title and canonical slug from aggregated workflow evidence.

## Inputs

- `transcript_name`
- `workflow_summary`

## Outputs

- `workflow_title`
- `canonical_slug`
- `confidence`
- `rationale`

## Rules

- prefer operational workflow identity over raw UI phrasing
- avoid broad domain-only titles when the evidence supports a more specific workflow
- keep `canonical_slug` in lowercase kebab-case
- confidence must be one of `high`, `medium`, `low`, `unknown`
- lower confidence when the evidence is weak or mixed
