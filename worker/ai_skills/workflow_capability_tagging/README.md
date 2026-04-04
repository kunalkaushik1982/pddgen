# Workflow Capability Tagging

## Purpose

Classify broader reusable business capability tags for one resolved workflow without redefining workflow identity.

## Inputs

- `process_title`
- `workflow_summary`
- `document_type`

## Output

- `capability_tags`
- `confidence`
- `rationale`

## Rules

- Return 1 to 3 business capability labels when supported by the evidence.
- Prefer broad reusable business capabilities over exact workflow titles.
- Do not return tool names, application names, or UI labels as capability tags.
- Do not redefine the workflow identity; capability tags are broader than the process title.
- Confidence must be one of `high`, `medium`, `low`, or `unknown`.
