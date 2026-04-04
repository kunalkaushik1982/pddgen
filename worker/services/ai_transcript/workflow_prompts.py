PROCESS_GROUP_INFERENCE_PROMPT = (
    "You classify transcript-derived steps into business process groups. "
    "Return strict JSON with keys: process_title, canonical_slug, matched_existing_title. "
    "process_title must be a concise business workflow title such as Sales Order Creation. "
    "canonical_slug must be lowercase kebab-case and stable. "
    "matched_existing_title must be either one exact title from existing_titles or an empty string. "
    "Only match an existing title when the process is genuinely the same workflow. "
    "If the process is different, return an empty matched_existing_title."
)

AMBIGUOUS_PROCESS_GROUP_PROMPT = (
    "You resolve ambiguous workflow-group assignments for transcript-derived evidence. "
    "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
    "matched_existing_title must be either one exact title from candidate_titles or an empty string if a new workflow should be created. "
    "recommended_title must be the workflow title that should be used. "
    "recommended_slug must be lowercase kebab-case. "
    "confidence must be one of high, medium, low, unknown. "
    "Prefer matching an existing workflow only if the evidence clearly supports the same business workflow. "
    "If the evidence is materially different, return an empty matched_existing_title and recommend a new workflow title."
)

WORKFLOW_TITLE_PROMPT = (
    "You normalize workflow evidence into a concise business workflow title. "
    "Return strict JSON with keys: workflow_title, canonical_slug, confidence, rationale. "
    "workflow_title must be a concise business noun phrase such as Sales Order Creation. "
    "Prefer the stable operational workflow identity over raw UI phrasing. "
    "Use the business object, workflow goal, system context, and repeated action pattern to infer the title. "
    "Avoid UI action labels like Open, Go To, Click, Navigate, Select, or Enter as the leading verb. "
    "Do not use a broad domain label such as Legal Analysis or Procurement unless the evidence does not support a more specific operational workflow title. "
    "Use tool names only when the tool materially defines a different operational workflow identity. "
    "canonical_slug must be lowercase kebab-case. "
    "confidence must be one of high, medium, low, unknown."
)

WORKFLOW_BOUNDARY_PROMPT = (
    "You classify whether two adjacent evidence segments belong to the same business workflow. "
    "Return strict JSON with keys: decision, confidence, rationale. "
    "decision must be one of same_workflow, new_workflow, uncertain. "
    "confidence must be one of high, medium, low, unknown. "
    "Use the workflow goal, business object, actor, system, action type, domain terms, rule hints, and transcript wording. "
    "Prefer same_workflow only when the business workflow clearly continues. "
    "Prefer new_workflow when the adjacent segment appears to start a materially different business activity. "
    "Use uncertain when the evidence conflicts or remains genuinely ambiguous."
)

WORKFLOW_GROUP_MATCH_PROMPT = (
    "You decide whether new transcript-derived workflow evidence matches an existing workflow group. "
    "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
    "matched_existing_title must be either one exact title from existing_group_titles or an empty string. "
    "recommended_title must be the workflow title that should be used. "
    "recommended_slug must be lowercase kebab-case. "
    "confidence must be one of high, medium, low, unknown. "
    "Only choose an existing workflow when the operational workflow is materially the same. "
    "Do not merge workflows only because they belong to the same business domain or professional function. "
    "Different tools, different application contexts, or materially different interaction sequences should usually remain separate workflows. "
    "Operational sameness should be evaluated using system context, business object flow, entry point, repeated action pattern, and outcome. "
    "If only broad domain overlap exists, prefer creating a separate workflow and lower confidence."
)

WORKFLOW_ENRICHMENT_PROMPT = (
    "You enrich one workflow evidence segment with business workflow labels. "
    "Return strict JSON with keys: actor, actor_role, system_name, action_verb, action_type, "
    "business_object, workflow_goal, rule_hints, domain_terms, confidence, rationale. "
    "actor_role should be a concise role like operator, approver, reviewer, external_party, or system. "
    "action_type should be a concise business action category such as navigate, create, update, review, approve, validate, extract, or submit. "
    "workflow_goal should be a concise business goal phrase, not a raw UI action. "
    "rule_hints and domain_terms must be arrays. "
    "Prefer operationally meaningful labels over generic domain labels. "
    "Use null for unknown scalar fields rather than guessing. "
    "confidence must be one of high, medium, low, unknown. "
    "Lower confidence when the segment does not contain enough evidence to support a precise operational interpretation."
)

PROCESS_SUMMARY_PROMPT = (
    "You generate a concise business summary for one resolved workflow group. "
    "Return strict JSON with keys: summary_text, confidence, rationale. "
    "summary_text must be 2 to 4 plain-English sentences that describe the workflow purpose, the main business actions, "
    "and the business outcome. "
    "Do not produce bullet points. "
    "Do not zigzag across unrelated workflows. "
    "Keep the summary scoped only to the provided workflow evidence. "
    "Use business language instead of UI click-by-click language when possible. "
    "Prefer the operational workflow identity and business outcome over raw transcript wording. "
    "confidence must be one of high, medium, low, unknown."
)

WORKFLOW_CAPABILITY_PROMPT = (
    "You classify broader business capability tags for one workflow. "
    "Return strict JSON with keys: capability_tags, confidence, rationale. "
    "capability_tags must be a short list of 1 to 3 business capability labels such as Contract Review, Legal Document Analysis, Sales Operations, or Procurement. "
    "These tags describe broad business capability and must not redefine workflow identity. "
    "Do not return tool names, exact workflow titles, or low-value generic labels. "
    "Prefer reusable cross-tool business capability labels. "
    "confidence must be one of high, medium, low, unknown."
)
