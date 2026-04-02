# Process Summary Generation

## Purpose

Generate a concise business summary for one resolved workflow group.

## Inputs

- `process_title`
- `workflow_summary`
- `steps`
- `notes`
- `document_type`

## Outputs

- `summary_text`
- `confidence`
- `rationale`

## Rules

- keep the summary scoped to one workflow only
- use 2 to 4 plain-English sentences
- use business language instead of click-by-click UI language
- do not produce bullet points
- confidence must be one of `high`, `medium`, `low`, `unknown`
