/**
 * Human-readable labels for export enrichment field ids (aligned with backend registry).
 */

export const ENRICHMENT_FIELD_LABELS: Record<string, string> = {
  "brd.executive_summary": "Executive summary",
  "brd.business_objectives": "Business objectives",
  "brd.background_problem_statement": "Background / problem statement",
  "brd.scope_of_the_project": "Scope of the project",
  "brd.in_scope": "In scope",
  "brd.out_of_scope": "Out of scope",
  "brd.stakeholders": "Stakeholders",
  "brd.business_requirements": "Business requirements",
  "brd.functional_requirements": "Functional requirements",
  "brd.non_functional_requirements": "Non-functional requirements",
  "brd.process_flow_workflow": "Process flow / workflow",
  "brd.use_cases_user_stories": "Use cases / user stories",
  "brd.data_requirements": "Data requirements",
  "brd.assumptions": "Assumptions",
  "brd.constraints": "Constraints",
  "brd.dependencies": "Dependencies",
  "brd.risks_and_mitigation": "Risks and mitigation",
  "brd.success_criteria_kpis": "Success criteria / KPIs",
  "brd.acceptance_criteria": "Acceptance criteria",
  "brd.implementation_timeline": "Implementation timeline",
  "brd.change_management_communication": "Change management / communication",
  "brd.approval_sign_off": "Approval / sign-off",
  "sop.purpose": "Purpose",
  "pdd.process_summary": "Process summary",
};

export function labelForEnrichmentField(fieldId: string): string {
  const direct = ENRICHMENT_FIELD_LABELS[fieldId];
  if (direct) {
    return direct;
  }
  return fieldId
    .replace(/^brd\./, "")
    .replace(/^sop\./, "")
    .replace(/^pdd\./, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
