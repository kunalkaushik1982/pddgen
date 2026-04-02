# Transcript To Steps

## Purpose

Convert one grounded transcript into structured process steps and business-rule notes.

## Inputs

- `transcript_artifact_id`
- `transcript_text`

## Outputs

- `steps`
- `notes`

## Rules

- use only transcript evidence provided
- do not invent timestamps
- do not invent application names not supported by transcript text
- ignore greetings, filler talk, and non-process chatter
- `supporting_transcript_text` must contain the exact supporting transcript snippet
- confidence must be one of `high`, `medium`, `low`, `unknown`
