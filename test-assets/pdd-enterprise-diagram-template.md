# PROCESS DESIGN DOCUMENT

Process Name: `{{ pdd.overview.process_name }}`

Document Owner: `{{ pdd.overview.document_owner }}`

Generated At: `{{ pdd.overview.generated_at }}`

Draft Session ID: `{{ pdd.session_id }}`

Document Status: `{{ pdd.overview.document_status }}`

## 1. Document Overview

This document captures the AS-IS process observed during the discovery walkthrough and provides draft TO-BE recommendations.

## 2. AS-IS Overview

Total Steps Identified: `{{ pdd.step_count }}`

Total Business Rules Identified: `{{ pdd.note_count }}`

## 3. AS-IS Steps

{% for step in pdd.as_is_steps %}

### Step {{ step.step_number }}

Application: `{{ step.application_name }}`

Action: `{{ step.action_text }}`

Source Data: `{{ step.source_data_note }}`

Timestamp: `{{ step.timestamp }}`

Evidence Window: `{{ step.start_timestamp }} to {{ step.end_timestamp }}`

Confidence: `{{ step.confidence }}`

{% if step.supporting_transcript_text %}
Transcript Evidence: `{{ step.supporting_transcript_text }}`
{% endif %}

{% if step.screenshots %}
Screenshots:
{% for shot in step.screenshots %}

{{ shot.role }} | {{ shot.timestamp }}

{{ shot.image }}

{% endfor %}
{% elif step.screenshot_image %}
Primary Screenshot:

{{ step.screenshot_image }}
{% endif %}

{% endfor %}

## 4. TO-BE Suggestions

{% for item in pdd.to_be_recommendations %}
- **{{ item.title }}**: {{ item.recommendation }}
{% endfor %}

## 5. Process Flow Diagram

{% if pdd.process_flow.diagram_image %}
{{ pdd.process_flow.diagram_image }}
{% else %}
Mermaid Source:

`{{ pdd.process_flow.mermaid_source }}`
{% endif %}

## 6. Business Rules and Notes

{% for rule in pdd.business_rules %}
- {{ rule.text }} ({{ rule.inference_type }}, {{ rule.confidence }})
{% endfor %}
