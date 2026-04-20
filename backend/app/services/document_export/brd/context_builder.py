r"""
BRD export: business-requirements-oriented context from session evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.documents.document_context_builder_interfaces import DocumentContextBuilder
from app.services.document_export.brd import process_summary_narrative
from app.services.document_export.common.prompts import load_document_prompt, render_prompt_template
from app.services.document_export.enrichment.store import enrich_brd_canonical_section_bodies
from app.services.document_export.common.workflow_context import SharedWorkflowExportContextBuilder
from app.storage.storage_service import StorageService


class BrdDocumentExportContextBuilder(SharedWorkflowExportContextBuilder, DocumentContextBuilder):
    """Build the BRD-specific render context from shared workflow primitives."""

    document_type = "brd"

    def _workflow_section_summary(
        self,
        process_name: str,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        return process_summary_narrative.build_brd_section_summary(
            process_name=process_name,
            process_steps=process_steps,
            process_notes=process_notes,
        )

    def _workflow_process_summary(
        self,
        draft_session: DraftSessionModel,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        return process_summary_narrative.build_brd_process_summary(draft_session, process_steps, process_notes)

    @staticmethod
    def _resolve_brd_business_objective(session_title: str) -> str:
        """Prefer ``brd/prompts/business_objective.md``; fallback to inline default."""
        raw = load_document_prompt("brd", "business_objective")
        if raw:
            return render_prompt_template(raw, title=session_title or "the initiative")
        return (
            f"Document the business requirements for {session_title} "
            "using the structured session evidence as the agreed baseline for scope and needs."
        )

    def build(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        template_document: DocxTemplate,
        *,
        asset_root: Path,
        storage_service: StorageService,
    ) -> dict[str, Any]:
        shared_context = self.build_shared_context(
            db,
            draft_session,
            template_document,
            asset_root=asset_root,
            storage_service=storage_service,
        )
        process_steps = shared_context["process_steps"]
        process_notes = shared_context["process_notes"]
        process_sections = shared_context["process_sections"]
        process_summary = self._workflow_process_summary(draft_session, process_steps, process_notes)
        multi_process = len(process_sections) > 1

        applications = SharedWorkflowExportContextBuilder.collect_unique_values(process_steps, "application_name")
        stakeholders = self._build_brd_stakeholders(draft_session, applications)
        requirements = self._build_brd_requirements(process_steps, process_notes, applications)
        business_rules = self._build_brd_business_rules(process_notes)
        assumptions = self._build_brd_assumptions(applications, process_sections)
        risks = self._build_brd_risks(process_notes)
        evidence_summary = self._build_brd_evidence_summary(process_steps, process_notes, process_sections)

        overview = {
            "process_name": draft_session.title,
            "document_owner": draft_session.owner_id,
            "document_status": draft_session.status,
            "generated_at": shared_context["generated_at"],
            "process_summary": process_summary,
        }
        process_flow = {
            "mermaid_source": shared_context["diagram_source"],
            "diagram_source": shared_context["diagram_source"],
            "diagram_path": shared_context["rendered_diagram_path"],
            "diagram_image": self._build_process_diagram_image(
                template_document,
                shared_context["rendered_diagram_path"],
            ),
            "rendered": bool(shared_context["rendered_diagram_path"]),
        }
        workflow_sections = [
            {
                "title": section["title"],
                "summary": section["summary"],
                "step_count": len(section.get("steps", [])),
                "steps": section.get("steps", []),
                "notes": section.get("notes", []),
                "step_bullets": section.get("step_bullets", []),
                "diagram_source": section.get("diagram_source", ""),
                "diagram_path": section.get("diagram_path", ""),
                "diagram_image": section.get("diagram_image"),
                "diagram_rendered": bool(section.get("diagram_path")),
            }
            for section in process_sections
        ]
        brd_business_objective = BrdDocumentExportContextBuilder._resolve_brd_business_objective(draft_session.title)
        brd_scope = BrdDocumentExportContextBuilder._build_brd_scope(
            draft_session.title,
            process_sections,
            process_steps,
        )
        canonical_sections = BrdDocumentExportContextBuilder._build_brd_canonical_sections(
            overview=overview,
            business_objective=brd_business_objective,
            scope=brd_scope,
            current_state_summary=process_summary,
            stakeholders=stakeholders,
            applications=applications,
            requirements=requirements,
            assumptions=assumptions,
            risks=risks,
            process_flow=process_flow,
            workflow_sections=workflow_sections,
            process_steps=process_steps,
        )
        enrich_brd_canonical_section_bodies(draft_session, canonical_sections)
        overview["process_summary"] = (
            BrdDocumentExportContextBuilder._brd_body_by_slug(canonical_sections, "executive_summary") or process_summary
        )
        brd_business_objective = (
            BrdDocumentExportContextBuilder._brd_body_by_slug(canonical_sections, "business_objectives") or brd_business_objective
        )
        brd_scope = BrdDocumentExportContextBuilder._brd_body_by_slug(canonical_sections, "scope_of_the_project") or brd_scope
        process_summary = (
            BrdDocumentExportContextBuilder._brd_body_by_slug(canonical_sections, "background_problem_statement") or process_summary
        )

        process_document_blocks: list[dict[str, Any]] = []
        if multi_process:
            process_document_blocks = [
                self._build_brd_process_document_block(
                    draft_session,
                    shared_context=shared_context,
                    section=section,
                )
                for section in process_sections
            ]

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": process_steps,
            "process_notes": process_notes,
            "process_sections": process_sections,
            "brd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "diagram_type": getattr(draft_session, "diagram_type", None) or "flowchart",
                "generated_at": shared_context["generated_at"],
                "multi_process": multi_process,
                "process_document_blocks": process_document_blocks,
                "overview": overview,
                "business_objective": brd_business_objective,
                "scope": brd_scope,
                "current_state_summary": process_summary,
                "stakeholders": stakeholders,
                "applications": applications,
                "requirements": requirements if not multi_process else [],
                "business_rules": business_rules if not multi_process else [],
                "assumptions": assumptions if not multi_process else [],
                "risks_and_exceptions": risks if not multi_process else [],
                "process_flow": process_flow if not multi_process else {
                    "mermaid_source": "",
                    "diagram_source": "",
                    "diagram_path": "",
                    "diagram_image": None,
                    "rendered": False,
                },
                "workflow_sections": workflow_sections if not multi_process else [],
                "evidence_summary": evidence_summary if not multi_process else {},
                "canonical_sections": canonical_sections if not multi_process else [],
            },
        }

    def _build_brd_process_document_block(
        self,
        draft_session: DraftSessionModel,
        *,
        shared_context: dict[str, Any],
        section: dict[str, Any],
    ) -> dict[str, Any]:
        """One full BRD body (canonical + appendix) scoped to a single workflow section / process group."""
        process_steps = section["steps"]
        process_notes = section["notes"]
        workflow_sections = [
            {
                "title": section["title"],
                "summary": section["summary"],
                "step_count": len(section.get("steps", [])),
                "steps": section.get("steps", []),
                "notes": section.get("notes", []),
                "step_bullets": section.get("step_bullets", []),
                "diagram_source": section.get("diagram_source", ""),
                "diagram_path": section.get("diagram_path", ""),
                "diagram_image": section.get("diagram_image"),
                "diagram_rendered": bool(section.get("diagram_path")),
            }
        ]
        applications = SharedWorkflowExportContextBuilder.collect_unique_values(process_steps, "application_name")
        stakeholders = self._build_brd_stakeholders(draft_session, applications)
        requirements = self._build_brd_requirements(process_steps, process_notes, applications)
        business_rules = self._build_brd_business_rules(process_notes)
        assumptions = self._build_brd_assumptions(applications, workflow_sections)
        risks = self._build_brd_risks(process_notes)
        evidence_summary = self._build_brd_evidence_summary(process_steps, process_notes, workflow_sections)

        overview = {
            "process_name": section.get("title") or draft_session.title,
            "document_owner": draft_session.owner_id,
            "document_status": draft_session.status,
            "generated_at": shared_context["generated_at"],
            "process_summary": section["summary"],
        }
        process_flow = {
            "mermaid_source": section.get("diagram_source", ""),
            "diagram_source": section.get("diagram_source", ""),
            "diagram_path": section.get("diagram_path", ""),
            "diagram_image": section.get("diagram_image"),
            "rendered": bool(section.get("diagram_path")),
        }
        brd_business_objective = BrdDocumentExportContextBuilder._resolve_brd_business_objective(draft_session.title)
        brd_scope = BrdDocumentExportContextBuilder._build_brd_scope(
            draft_session.title,
            workflow_sections,
            process_steps,
        )
        canonical_sections = BrdDocumentExportContextBuilder._build_brd_canonical_sections(
            overview=overview,
            business_objective=brd_business_objective,
            scope=brd_scope,
            current_state_summary=section["summary"],
            stakeholders=stakeholders,
            applications=applications,
            requirements=requirements,
            assumptions=assumptions,
            risks=risks,
            process_flow=process_flow,
            workflow_sections=workflow_sections,
            process_steps=process_steps,
        )
        enrich_brd_canonical_section_bodies(draft_session, canonical_sections)
        base_summary = str(section.get("summary") or "")
        overview["process_summary"] = (
            BrdDocumentExportContextBuilder._brd_body_by_slug(canonical_sections, "executive_summary") or base_summary
        )

        return {
            "process_title": str(section.get("title") or draft_session.title),
            "canonical_sections": canonical_sections,
            "overview": overview,
            "requirements": requirements,
            "business_rules": business_rules,
            "assumptions": assumptions,
            "risks_and_exceptions": risks,
            "workflow_sections": workflow_sections,
            "process_flow": process_flow,
            "evidence_summary": evidence_summary,
        }

    @staticmethod
    def _brd_body_by_slug(sections: list[dict[str, str]], slug: str) -> str:
        for row in sections:
            if row.get("slug") == slug:
                return str(row.get("body") or "").strip()
        return ""

    @staticmethod
    def _build_brd_canonical_sections(
        *,
        overview: dict[str, Any],
        business_objective: str,
        scope: str,
        current_state_summary: str,
        stakeholders: list[dict[str, str]],
        applications: list[str],
        requirements: list[dict[str, str]],
        assumptions: list[str],
        risks: list[str],
        process_flow: dict[str, Any],
        workflow_sections: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """Align export text with a 20-part BRD outline (plus in/out scope under section 4).

        Mirrors the structure in ``BRD_Index_Definitions_Examples.docx`` / ``CRM_BRD_Detailed.docx``:
        auto-filled where session data exists; otherwise short placeholders for authors.
        """
        src = str(process_flow.get("diagram_source") or "").strip()
        if len(src) > 4000:
            src = src[:3997] + "..."

        in_scope_lines: list[str] = []
        for sec in workflow_sections:
            title = str(sec.get("title") or "").strip()
            if title:
                in_scope_lines.append(f"- {title}")
        in_scope_body = (
            "Documented workflow areas for this session:\n" + "\n".join(in_scope_lines)
            if in_scope_lines
            else "No named workflow sections were captured; confirm in-scope processes with stakeholders."
        )

        business_req_bullets: list[str] = []
        for step in process_steps[:12]:
            action = str(step.get("action_text") or "").strip()
            if action:
                business_req_bullets.append(f"- {action}")
        business_req_body = (
            "\n".join(business_req_bullets)
            if business_req_bullets
            else "No session steps were recorded; capture business needs in collaboration with the process owner."
        )

        functional_lines = [
            f"- {r['statement']}"
            for r in requirements
            if str(r.get("category") or "") == "Functional"
        ]
        functional_body = (
            "\n".join(functional_lines)
            if functional_lines
            else "No functional requirements were derived from steps; refine after discovery."
        )

        nfr_lines = [
            f"- ({r.get('category', '')}) {r['statement']}"
            for r in requirements
            if str(r.get("category") or "") != "Functional"
        ]
        non_functional_body = (
            "\n".join(nfr_lines)
            if nfr_lines
            else (
                "Non-functional requirements (performance, availability, security, etc.) were not "
                "auto-derived from the session evidence; define them explicitly for implementation."
            )
        )

        stakeholder_lines = [
            f"- {s.get('name', '')} ({s.get('role', '')}): {s.get('interest', '')}"
            for s in stakeholders
        ]
        stakeholders_body = "\n".join(stakeholder_lines) if stakeholder_lines else "Stakeholders to be confirmed."

        use_case_fragments = [
            str(step.get("action_text") or "").strip()
            for step in process_steps[:15]
            if str(step.get("action_text") or "").strip()
        ]
        use_cases_body = (
            "Observed user–system interactions from the session include: "
            + "; ".join(use_case_fragments)
            + "."
            if use_case_fragments
            else "Describe primary user stories once the target solution is defined."
        )

        data_body = (
            "Applications and systems referenced in the session: "
            + (", ".join(applications) if applications else "none recorded")
            + ". Validate required data entities, retention, and integrations with owners."
        )

        approval_lines = [f"- {s.get('name', '')} — {s.get('role', '')}" for s in stakeholders[:8]]
        approval_body = (
            "\n".join(approval_lines)
            if approval_lines
            else "Record approvers and sign-off dates prior to go-live."
        )

        sections: list[dict[str, str]] = [
            {
                "ref": "1",
                "slug": "executive_summary",
                "title": "Executive Summary",
                "body": str(overview.get("process_summary") or "").strip()
                or "Executive summary not available; add a concise overview of purpose and outcomes.",
            },
            {
                "ref": "2",
                "slug": "business_objectives",
                "title": "Business Objectives",
                "body": business_objective,
            },
            {
                "ref": "3",
                "slug": "background_problem_statement",
                "title": "Background / Problem Statement",
                "body": current_state_summary.strip()
                or "Describe the current situation and drivers for change.",
            },
            {
                "ref": "4",
                "slug": "scope_of_the_project",
                "title": "Scope of the Project",
                "body": scope.strip() or "Define overall scope boundaries.",
            },
            {
                "ref": "4.1",
                "slug": "in_scope",
                "title": "In-Scope",
                "body": in_scope_body,
            },
            {
                "ref": "4.2",
                "slug": "out_of_scope",
                "title": "Out-of-Scope",
                "body": (
                    "Out-of-scope items are not captured automatically from the session evidence. "
                    "List explicit exclusions (e.g. systems, regions, or processes not in this phase)."
                ),
            },
            {
                "ref": "5",
                "slug": "stakeholders",
                "title": "Stakeholders",
                "body": stakeholders_body,
            },
            {
                "ref": "6",
                "slug": "business_requirements",
                "title": "Business Requirements",
                "body": business_req_body,
            },
            {
                "ref": "7",
                "slug": "functional_requirements",
                "title": "Functional Requirements",
                "body": functional_body,
            },
            {
                "ref": "8",
                "slug": "non_functional_requirements",
                "title": "Non-Functional Requirements",
                "body": non_functional_body,
            },
            {
                "ref": "9",
                "slug": "process_flow_workflow",
                "title": "Process Flow / Workflow",
                "body": (
                    (src + "\n\n")
                    if src
                    else "Process diagram source was not available; attach or describe the end-to-end flow.\n\n"
                )
                + (
                    "A rendered process diagram image is included in the export when diagram rendering succeeds "
                    "(see `brd.process_flow.diagram_image` in templates that support inline images)."
                    if process_flow.get("rendered")
                    else "Render a process diagram in the product or attach one in the final BRD."
                ),
            },
            {
                "ref": "10",
                "slug": "use_cases_user_stories",
                "title": "Use Cases / User Stories",
                "body": use_cases_body,
            },
            {
                "ref": "11",
                "slug": "data_requirements",
                "title": "Data Requirements",
                "body": data_body,
            },
            {
                "ref": "12",
                "slug": "assumptions",
                "title": "Assumptions",
                "body": "\n".join(f"- {a}" for a in assumptions) if assumptions else "No assumptions were listed.",
            },
            {
                "ref": "13",
                "slug": "constraints",
                "title": "Constraints",
                "body": (
                    "Budget, timeline, regulatory, and organizational constraints are not inferred from the "
                    "session evidence; document them explicitly."
                ),
            },
            {
                "ref": "14",
                "slug": "dependencies",
                "title": "Dependencies",
                "body": (
                    "Dependencies may include vendor delivery, upstream/downstream systems, and data readiness. "
                    + (
                        f"Applications referenced in this session: {', '.join(applications)}."
                        if applications
                        else "No application dependencies were recorded."
                    )
                ),
            },
            {
                "ref": "15",
                "slug": "risks_and_mitigation",
                "title": "Risks and Mitigation Plan",
                "body": "\n".join(f"- {r}" for r in risks) if risks else "Risks to be assessed.",
            },
            {
                "ref": "16",
                "slug": "success_criteria_kpis",
                "title": "Success Criteria / KPIs",
                "body": (
                    "Quantitative success measures were not auto-derived; align KPIs with business objectives "
                    "and baseline metrics before implementation."
                ),
            },
            {
                "ref": "17",
                "slug": "acceptance_criteria",
                "title": "Acceptance Criteria",
                "body": (
                    "Define acceptance tests and go-live readiness checks with stakeholders "
                    "(e.g. UAT completion, performance targets, data migration sign-off)."
                ),
            },
            {
                "ref": "18",
                "slug": "implementation_timeline",
                "title": "Implementation Approach / Timeline",
                "body": (
                    "Phases and milestones are not generated from the session evidence; add a delivery plan "
                    "appropriate to your organization."
                ),
            },
            {
                "ref": "19",
                "slug": "change_management_communication",
                "title": "Change Management & Communication Plan",
                "body": (
                    "Describe training, communication cadence, and governance for changes to scope or design."
                ),
            },
            {
                "ref": "20",
                "slug": "approval_sign_off",
                "title": "Approval & Sign-off",
                "body": approval_body,
            },
        ]
        return sections

    @staticmethod
    def _build_brd_scope(
        process_name: str,
        process_sections: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
    ) -> str:
        """Project scope wording for BRD (not SOP-style 'current-state execution')."""
        if process_sections:
            section_names = ", ".join(
                section["title"] for section in process_sections[:3] if section.get("title")
            )
            if len(process_sections) > 3:
                section_names += ", and related workflow areas"
            return (
                f"The initiative covers {process_name} across {len(process_sections)} workflow area(s) "
                f"and {len(process_steps)} documented activities from the session, including areas such as {section_names}."
            )
        return (
            f"The scope includes {process_name} as represented by {len(process_steps)} documented activities "
            "in the session evidence."
        )

    @staticmethod
    def _build_brd_stakeholders(
        draft_session: DraftSessionModel,
        applications: list[str],
    ) -> list[dict[str, str]]:
        stakeholders = [
            {
                "name": draft_session.owner_id or "Process owner",
                "role": "Process owner",
                "interest": "Approves the documented requirements and interpretation of the session evidence.",
            },
            {
                "name": "Operational user",
                "role": "Business user",
                "interest": "Executes the workflow and relies on accurate procedural and system requirements.",
            },
        ]
        if applications:
            stakeholders.append(
                {
                    "name": ", ".join(applications),
                    "role": "System landscape",
                    "interest": "Provides the application context and integration boundaries for the business process.",
                }
            )
        return stakeholders

    @staticmethod
    def _build_brd_requirements(
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
        applications: list[str],
    ) -> list[dict[str, str]]:
        requirements: list[dict[str, str]] = []
        for index, step in enumerate(process_steps[:8], start=1):
            requirement_id = f"BR-{index:03d}"
            requirement_text = str(step.get("action_text", "") or "").strip()
            if not requirement_text:
                continue
            requirements.append(
                {
                    "id": requirement_id,
                    "category": "Functional",
                    "statement": f"The solution must support users to {requirement_text.lower().rstrip('.')}.",
                    "rationale": (
                        str(step.get("source_data_note", "") or "").strip()
                        or "Derived from documented session activity."
                    ),
                }
            )
        if applications:
            requirements.append(
                {
                    "id": f"BR-{len(requirements) + 1:03d}",
                    "category": "System",
                    "statement": "The solution must preserve access to the required application landscape.",
                    "rationale": "Observed process execution depends on " + ", ".join(applications) + ".",
                }
            )
        if process_notes:
            requirements.append(
                {
                    "id": f"BR-{len(requirements) + 1:03d}",
                    "category": "Control",
                    "statement": "The solution must enforce the documented business controls and validation steps.",
                    "rationale": "Derived from the supporting business rules and notes captured during review.",
                }
            )
        return requirements

    @staticmethod
    def _build_brd_business_rules(process_notes: list[dict[str, Any]]) -> list[str]:
        rules = [
            str(note.get("text", "") or "").strip()
            for note in process_notes
            if str(note.get("text", "") or "").strip()
        ]
        if rules:
            return rules[:8]
        return ["Business rules were not explicitly captured; validate rules with the process owner during review."]

    @staticmethod
    def _build_brd_assumptions(
        applications: list[str],
        process_sections: list[dict[str, Any]],
    ) -> list[str]:
        assumptions = [
            "The recorded session evidence reflects how the process is operated for the scope under review.",
            "Required users have access to the necessary systems and source records.",
        ]
        if applications:
            assumptions.append("The documented process continues to rely on " + ", ".join(applications) + ".")
        if len(process_sections) > 1:
            assumptions.append("Workflow sections are reviewed independently but still form part of one business scenario.")
        return assumptions

    @staticmethod
    def _build_brd_risks(process_notes: list[dict[str, Any]]) -> list[str]:
        if process_notes:
            return [
                "Incomplete adherence to documented controls may cause data quality or compliance issues.",
                "Implicit business rules identified in session notes should be validated before implementation decisions are finalized.",
            ]
        return [
            "Uncaptured exceptions or business rules may require follow-up validation with stakeholders.",
        ]

    @staticmethod
    def _build_brd_evidence_summary(
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
        process_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "workflow_sections": len(process_sections),
            "observed_steps": len(process_steps),
            "captured_notes": len(process_notes),
        }

