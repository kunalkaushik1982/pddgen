# Export text enrichment

After draft generation completes, the worker runs **one** LLM call (`document_export_text_enrichment`) that fills all registered fields in `registry.py`.

- Per-field instructions: `instructions/<doc_type>/<field_name>.md` (e.g. `pdd/process_summary.md` → field id `pdd.process_summary`).
- Output is stored as JSON on `draft_sessions.export_text_enrichment_json` with shape `{ "version": 1, "fields": { ... } }`.
- Document export builders merge these strings when present; otherwise deterministic Python text is used.

Disable via settings: `AI_DOCUMENT_EXPORT_ENRICHMENT_ENABLED=false` or `AI_ENABLED=false`.
