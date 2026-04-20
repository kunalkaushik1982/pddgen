# BRD prompt sections (editable)

One file per logical section used when building the BRD export context. File name = section id (slug).

| Section id | Used for |
|------------|----------|
| `business_objective.md` | §2 Business Objectives body (`brd.business_objective`) |

Placeholders use `{{variable}}` syntax (see `render_prompt_template` in `common/prompts.py`).

Add more `.md` files as builders start loading them (e.g. `executive_summary.md`, `diagram_mermaid.md`).
