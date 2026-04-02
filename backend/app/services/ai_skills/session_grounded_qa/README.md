# Session Grounded QA

## Purpose

Answer one grounded question about a session using only the bounded evidence supplied by the service.

## Inputs

- `session_title`
- `process_group_id`
- `question`
- `evidence`

## Output

- `answer`
- `confidence`
- `citation_ids`

## Rules

- Use only the supplied evidence.
- Return citation ids that refer only to evidence items actually used.
- If the evidence is insufficient, say so directly.
- Confidence must be one of `high`, `medium`, or `low`.
