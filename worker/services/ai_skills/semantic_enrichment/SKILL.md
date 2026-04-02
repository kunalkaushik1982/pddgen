# Semantic Enrichment

## Purpose

Interpret one workflow evidence segment into workflow-relevant business labels.

## Inputs

- `transcript_name`
- `segment_text`
- `segment_context`

## Outputs

- `actor`
- `actor_role`
- `system_name`
- `action_verb`
- `action_type`
- `business_object`
- `workflow_goal`
- `rule_hints`
- `domain_terms`
- `confidence`
- `rationale`

## Rules

- use only the provided segment evidence
- prefer operationally meaningful workflow labels over vague generic labels
- use `null` for unknown scalar fields
- keep `rule_hints` and `domain_terms` as arrays
- confidence must be one of `high`, `medium`, `low`, `unknown`
- do not invent precise workflow meaning when evidence is weak
