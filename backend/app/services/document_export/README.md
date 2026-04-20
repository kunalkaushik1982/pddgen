# Document export

- **`common/`** — `SharedWorkflowExportContextBuilder` (session → steps/sections/diagrams), `DocumentExportPipeline` (ordered stages per `document_type`), `load_document_prompt` / `render_prompt_template`.
- **`pdd/`** — PDD template context + `DocumentExportContextBuilder` alias; multi-process PDD uses `pdd.multi_process` + `pdd.process_sections` in the bundled template (`docs/templates/build_flowlens_pdd_template.py`); `template_preparation.py` is a no-op hook.
- **`sop/`** — SOP template context; multi-process SOP uses `sop.multi_process` + `sop.process_document_blocks` in the bundled template (`docs/templates/build_flowlens_sop_template.py`); `template_preparation.py` is a no-op hook.
- **`brd/`** — BRD template context; `brd/prompts/*.md` for editable strings; `template_preparation.py` is a no-op (multi-process BRD uses `brd.multi_process` + `brd.process_document_blocks` in the bundled template).

Legacy imports: `app.services.document_export_context_builder` re-exports the same symbols.
