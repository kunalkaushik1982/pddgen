# Templates

This folder contains sample uploadable Word templates for document-output testing.

Current sample templates:

- `flowlens-pdd-template.docx`
  - sample PDD template for the `pdd` document builder (single- and multi-process)
  - regenerate via `python docs/templates/build_flowlens_pdd_template.py` (also refreshes `test-assets/pdd-enterprise-multishot-template.docx`)
  - uses `pdd.multi_process` to choose `pdd.process_sections` loops vs `pdd.as_is_steps`
- `flowlens-sop-template.docx`
  - sample SOP template for the `sop` document builder (single- and multi-process)
  - regenerate via `python docs/templates/build_flowlens_sop_template.py`
  - uses `sop.multi_process` to choose `sop.process_document_blocks` vs top-level `sop.*`
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
    - **`brd.canonical_sections`** — full 1–20 outline plus 4.1 / 4.2 (index-style BRD)
    - appendix: `brd.overview`, structured requirements (`BR-###`), business rules
    - `brd.workflow_sections` (per-section summaries)
    - `brd.process_flow` (combined diagram image)
    - evidence summary
