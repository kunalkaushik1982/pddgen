# DOCX Template Guide

This file describes the exact template structure the current renderer supports.

## Rendering Engine

The backend uses `docxtpl`, which means your Word template must use Jinja-style placeholders.

Normal text like:

```text
<Process Name>
[AS-IS STEPS]
```

will not be replaced automatically.

You must use placeholders like:

```text
{{ pdd.title }}
{{ pdd.owner_id }}
```

## Supported Template Context

The renderer currently sends this structure into the DOCX template:

```text
pdd.title
pdd.owner_id
pdd.session_id
pdd.status
pdd.diagram_type
pdd.generated_at
pdd.step_count
pdd.note_count
pdd.overview.process_name
pdd.overview.document_owner
pdd.overview.document_status
pdd.overview.generated_at
pdd.as_is_steps
pdd.to_be_recommendations
pdd.process_flow.mermaid_source
pdd.process_flow.diagram_path
pdd.process_flow.diagram_image
pdd.process_flow.detailed_path
pdd.process_flow.detailed_image
pdd.process_flow.rendered
pdd.business_rules
```

Each entry in `pdd.as_is_steps` supports:

```text
step.step_number
step.application_name
step.action_text
step.source_data_note
step.timestamp
step.start_timestamp
step.end_timestamp
step.supporting_transcript_text
step.confidence
step.screenshot_path
step.screenshot_image
step.screenshots
```

Each item in `step.screenshots` supports:

```text
shot.role
shot.timestamp
shot.selection_method
shot.path
shot.image
shot.is_primary
```

Each entry in `pdd.business_rules` supports:

```text
rule.text
rule.inference_type
rule.confidence
```

Each entry in `pdd.to_be_recommendations` supports:

```text
item.title
item.recommendation
```

Backward-compatible aliases also exist:

```text
session_title
owner_id
process_steps
process_notes
```

## Enterprise-Style Template Structure

Use this exact content in a Word document if you want a more realistic PDD layout:

```text
PROCESS DESIGN DOCUMENT

Process Name: {{ pdd.overview.process_name }}
Document Owner: {{ pdd.overview.document_owner }}
Generated At: {{ pdd.overview.generated_at }}
Draft Session ID: {{ pdd.session_id }}
Document Status: {{ pdd.overview.document_status }}
Diagram Type: {{ pdd.diagram_type }}

1. Document Overview
This document captures the AS-IS process observed during the discovery walkthrough.

2. AS-IS Overview
Total Steps Identified: {{ pdd.step_count }}
Total Business Rules Identified: {{ pdd.note_count }}

3. AS-IS Steps
{% for step in pdd.as_is_steps %}
Step {{ step.step_number }}
Application: {{ step.application_name }}
Action: {{ step.action_text }}
Source Data: {{ step.source_data_note }}
Timestamp: {{ step.timestamp }}
Evidence Window: {{ step.start_timestamp }} to {{ step.end_timestamp }}
Confidence: {{ step.confidence }}
{% if step.supporting_transcript_text %}
Transcript Evidence: {{ step.supporting_transcript_text }}
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

4. TO-BE Suggestions
{% for item in pdd.to_be_recommendations %}
- {{ item.title }}: {{ item.recommendation }}
{% endfor %}

5. Detailed Flow Diagram
{% if pdd.process_flow.detailed_image %}
{{ pdd.process_flow.detailed_image }}
{% elif pdd.process_flow.diagram_image %}
{{ pdd.process_flow.diagram_image }}
{% else %}
Diagram Source:
{{ pdd.process_flow.diagram_source }}
{% endif %}

6. Business Rules and Notes
{% for rule in pdd.business_rules %}
- {{ rule.text }} ({{ rule.inference_type }}, {{ rule.confidence }})
{% endfor %}
```

## Important Notes for Word

- Put each loop block on its own line.
- Keep `{% for ... %}`, `{% endfor %}`, `{% if ... %}`, and `{% endif %}` as plain text in the Word document.
- Do not use smart quotes.
- Do not break one placeholder across multiple text runs manually if possible.
- `{{ step.screenshot_image }}` is the image placeholder for the exported screenshot.
- `step.screenshots` is the multi-screenshot list for each step.
- `{{ pdd.process_flow.detailed_image }}` is the recommended image placeholder for the detailed flow.
- `{{ pdd.process_flow.diagram_image }}` remains as the backward-compatible single-diagram alias.
- If a diagram image is unavailable, use `{{ pdd.process_flow.diagram_source }}` as a fallback text block.

## Ready-To-Use Template

You already have a ready-to-use enterprise-style template here:

- [pdd-enterprise-template.docx](C:\Users\work\Documents\PddGenerator\test-assets\pdd-enterprise-template.docx)
- [pdd-enterprise-multishot-template.docx](C:\Users\work\Documents\PddGenerator\test-assets\pdd-enterprise-multishot-template.docx)
