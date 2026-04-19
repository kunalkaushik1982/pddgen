r"""
Generate docs/templates/flowlens-brd-template.docx for docxtpl BRD export tests.

Run from repo root: python docs/templates/build_flowlens_brd_template.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def p(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def main() -> None:
    out = Path(__file__).resolve().parent / "flowlens-brd-template.docx"
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("FlowLens Business Requirements Document")
    run.bold = True
    run.font.size = Pt(18)

    p(doc, "")
    p(doc, "Business Requirements")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{{ brd.title }}")
    p(doc, "Owner: {{ brd.owner_id }} · Session: {{ brd.session_id }} · Status: {{ brd.status }}")
    p(doc, "Generated: {{ brd.generated_at }} · Diagram: {{ brd.diagram_type }}")

    p(doc, "")
    p(doc, "Document overview")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{{ brd.overview.process_name }}")
    p(doc, "{{ brd.overview.document_owner }}")
    p(doc, "{{ brd.overview.document_status }}")
    p(doc, "{{ brd.overview.process_summary }}")

    p(doc, "")
    p(doc, "Business objective")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{{ brd.business_objective }}")

    p(doc, "")
    p(doc, "Scope")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{{ brd.scope }}")

    p(doc, "")
    p(doc, "Current-state summary")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{{ brd.current_state_summary }}")

    p(doc, "")
    p(doc, "Stakeholders")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for s in brd.stakeholders %}")
    p(doc, "{{ s.name }} — {{ s.role }}: {{ s.interest }}")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Application landscape")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for app in brd.applications %}{{ app }}{% if not loop.last %}, {% endif %}{% endfor %}")

    p(doc, "")
    p(doc, "Requirements")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for req in brd.requirements %}")
    p(doc, "{{ req.id }} [{{ req.category }}]: {{ req.statement }} — {{ req.rationale }}")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Business rules and notes")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for rule in brd.business_rules %}")
    p(doc, "{{ rule }}")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Assumptions")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for a in brd.assumptions %}")
    p(doc, "{{ a }}")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Risks and exceptions")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for r in brd.risks_and_exceptions %}")
    p(doc, "{{ r }}")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Workflow evidence (by section)")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% for sec in brd.workflow_sections %}")
    p(doc, "{{ sec.title }}: {{ sec.summary }} ({{ sec.step_count }} steps)")
    p(doc, "{% endfor %}")

    p(doc, "")
    p(doc, "Process flow (combined)")
    doc.paragraphs[-1].runs[0].bold = True
    p(doc, "{% if brd.process_flow.diagram_image %}{{ brd.process_flow.diagram_image }}{% endif %}")

    p(doc, "")
    p(doc, "Evidence summary")
    doc.paragraphs[-1].runs[0].bold = True
    p(
        doc,
        "Sections: {{ brd.evidence_summary.workflow_sections }} · "
        "Steps: {{ brd.evidence_summary.observed_steps }} · "
        "Notes: {{ brd.evidence_summary.captured_notes }}",
    )

    doc.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
