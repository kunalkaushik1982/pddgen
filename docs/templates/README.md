# Templates

This folder contains sample uploadable Word templates for document-output testing.

Current sample templates:

- `flowlens-sop-template.docx`
  - sample SOP template for the `sop` document builder
  - upload this in Workspace when `Document output` is set to `SOP`
  - renders SOP-specific sections:
    - purpose
    - scope
    - responsibilities
    - applications
    - prerequisites
    - control requirements
    - procedure sections with numbered instructions
    - expected outcomes
    - evidence summary
- `flowlens-brd-template.docx`
  - sample BRD template for the `brd` document builder
  - upload this in Workspace when `Document output` is set to `BRD`
  - regenerate via `python docs/templates/build_flowlens_brd_template.py`
  - full placeholder list: **`BRD_DOCXTPL_REFERENCE.md`**
  - renders BRD-specific sections:
    - `brd.overview`, business objective, scope, current-state summary
    - stakeholders, application landscape, requirements (`BR-###`)
    - business rules, assumptions, risks
    - `brd.workflow_sections` (per-section steps + diagrams)
    - `brd.process_flow` (combined diagram image)
    - evidence summary
