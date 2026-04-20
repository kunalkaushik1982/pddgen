# BRD Word template (docxtpl) — context reference

Exports use **docxtpl** (Jinja2 inside `.docx`). Set session **Document output** to **BRD** and upload your template as the **template** artifact.

## Top-level keys (same as other workflow exports)

| Key | Description |
|-----|-------------|
| `session_title` | Draft session title |
| `owner_id` | Owner username |
| `process_steps` | Full step list (shared shape) |
| `process_notes` | Full notes list |
| `process_sections` | Per–process-group sections with diagrams (shared shape) |

## `brd` — primary namespace for BRD templates

Use `{{ brd.<field> }}` in your Word document.

### Identity & metadata

| Field | Type | Description |
|-------|------|-------------|
| `brd.title` | string | Session title |
| `brd.owner_id` | string | Owner |
| `brd.session_id` | string | Draft session id |
| `brd.status` | string | Session status |
| `brd.diagram_type` | string | e.g. `flowchart`, `sequence` |
| `brd.generated_at` | string | UTC timestamp string |

### `brd.overview` — cover-style block

| Field | Description |
|-------|-------------|
| `brd.overview.process_name` | Same as session title |
| `brd.overview.document_owner` | Owner id |
| `brd.overview.document_status` | Session status |
| `brd.overview.generated_at` | Same as `brd.generated_at` |
| `brd.overview.process_summary` | Business-facing executive summary from session evidence (multi-section aware; not PDD “AS-IS” wording) |

### Narrative sections

| Field | Description |
|-------|-------------|
| `brd.business_objective` | Auto-generated BRD objective paragraph |
| `brd.scope` | BRD scope paragraph (initiative / workflow areas; not SOP-style scope) |
| `brd.current_state_summary` | Same text as `brd.overview.process_summary` (alias for template flexibility) |

### Structured lists

**Stakeholders** — `{% for s in brd.stakeholders %}`

| Key | Description |
|-----|-------------|
| `s.name` | Name or label |
| `s.role` | Role |
| `s.interest` | Interest / concern |

**Applications** — `{% for app in brd.applications %}` — short strings (application names).

**Requirements** — `{% for req in brd.requirements %}`

| Key | Description |
|-----|-------------|
| `req.id` | e.g. `BR-001` |
| `req.category` | e.g. `Functional`, `System`, `Control` |
| `req.statement` | Requirement statement |
| `req.rationale` | Rationale |

**Business rules** — `{% for rule in brd.business_rules %}` — each `rule` is a **string** (note text), not an object.

**Assumptions** — `{% for a in brd.assumptions %}` — string lines.

**Risks** — `{% for r in brd.risks_and_exceptions %}` — string lines.

### Workflow evidence

**`brd.workflow_sections`** — one entry per process group / section:

| Key | Description |
|-----|-------------|
| `sec.title` | Section title |
| `sec.summary` | Section narrative |
| `sec.step_count` | Integer |
| `sec.steps` | Step dicts (same shape as `process_steps` entries) |
| `sec.notes` | Notes scoped to section |
| `sec.step_bullets` | Bullet strings |
| `sec.diagram_source` | Mermaid/text source |
| `sec.diagram_path` | Rendered image path |
| `sec.diagram_image` | Inline image for Word (or empty) |
| `sec.diagram_rendered` | Boolean |

Example:

```jinja
{% for sec in brd.workflow_sections %}
{{ sec.title }}
{{ sec.summary }}
{% for step in sec.steps %}
{{ step.bullet_entry }}
{% endfor %}
{% endfor %}
```

### Combined process flow

**`brd.process_flow`** — whole-session diagram (combined when multiple sections):

| Key | Description |
|-----|-------------|
| `brd.process_flow.diagram_source` | Combined diagram source text |
| `brd.process_flow.diagram_image` | **InlineImage** for Word — use on its own paragraph |
| `brd.process_flow.rendered` | Whether a combined image path exists |

```jinja
{% if brd.process_flow.diagram_image %}
{{ brd.process_flow.diagram_image }}
{% endif %}
```

### Evidence summary

| Key | Description |
|-----|-------------|
| `brd.evidence_summary.workflow_sections` | Count |
| `brd.evidence_summary.observed_steps` | Count |
| `brd.evidence_summary.captured_notes` | Count |

### `brd.canonical_sections` — 20-section outline (matches index + CRM sample)

Reference assets under `input/BRD/brdtemplatedefinitiontranscriptgeneratedbrd/` use the same headings: **BRD_Index_Definitions_Examples.docx** (definitions/examples per section) and **CRM_BRD_Detailed.docx** (filled example).

`brd.canonical_sections` is a **list of 22** rows (sections **4.1** and **4.2** sit under section 4). Each item has:

| Key | Description |
|-----|-------------|
| `ref` | `"1"` … `"20"` or `"4.1"`, `"4.2"` |
| `slug` | Stable id, e.g. `executive_summary`, `in_scope`, `functional_requirements` |
| `title` | Heading text without the leading number |
| `body` | Auto-filled from session data where possible; short placeholders otherwise |

Example — one heading per section:

```jinja
{% for row in brd.canonical_sections %}
{{ row.ref }} {{ row.title }}
{{ row.body }}

{% endfor %}
```

Rough mapping from walkthrough-backed fields: summary → §1–3; scope → §4; workflow section titles → §4.1; §4.2 placeholder; stakeholders → §5; step text → §6; `brd.requirements` (Functional) → §7; other requirement categories → §8; diagram source + image hint → §9; step actions narrative → §10; applications → §11; assumptions / risks → §12 / §15; §13–14, §16–§19 placeholders; stakeholder list → §20.

## Shipping a custom BRD template

1. Build your layout in Word with the placeholders above (Jinja loops on their own lines; see `build_flowlens_brd_template.py` for a minimal structure).
2. In Workspace, choose **BRD** as document output and upload the `.docx` as **template**.
3. Run export as usual.

## Regenerate the bundled sample

From repo root:

```bash
python docs/templates/build_flowlens_brd_template.py
```

Writes `docs/templates/flowlens-brd-template.docx`.
