r"""
Registered enrichment field ids and mapping by session ``document_type``.

Only fields for the session's document type are requested in the single batched LLM call
(PDD → ``pdd.*``, SOP → ``sop.*``, BRD → ``brd.*``) to avoid generating unused copy.

BRD uses one field id per row in ``brd.canonical_sections`` (22 outline rows including §4.1 / §4.2).
Keep ``BRD_CANONICAL_SLUGS`` aligned with
``BrdDocumentExportContextBuilder._build_brd_canonical_sections``.

Add a new placeholder: register the field id under the right document type in
``_FIELDS_BY_DOCUMENT_TYPE``, add ``instructions/<doc>/<name>.md``, merge in the context builder.
"""

from __future__ import annotations

# One id per ``canonical_sections`` slug (see BRD_DOCXTPL_REFERENCE.md).
BRD_CANONICAL_SLUGS: tuple[str, ...] = (
    "executive_summary",
    "business_objectives",
    "background_problem_statement",
    "scope_of_the_project",
    "in_scope",
    "out_of_scope",
    "stakeholders",
    "business_requirements",
    "functional_requirements",
    "non_functional_requirements",
    "process_flow_workflow",
    "use_cases_user_stories",
    "data_requirements",
    "assumptions",
    "constraints",
    "dependencies",
    "risks_and_mitigation",
    "success_criteria_kpis",
    "acceptance_criteria",
    "implementation_timeline",
    "change_management_communication",
    "approval_sign_off",
)

BRD_ENRICHMENT_FIELD_IDS: tuple[str, ...] = tuple(f"brd.{s}" for s in BRD_CANONICAL_SLUGS)

# All known field ids (documentation / tests / union of per-type sets).
ENRICHMENT_FIELD_IDS: tuple[str, ...] = BRD_ENRICHMENT_FIELD_IDS + (
    "pdd.process_summary",
    "sop.purpose",
)

_FIELDS_BY_DOCUMENT_TYPE: dict[str, tuple[str, ...]] = {
    "pdd": ("pdd.process_summary",),
    "sop": ("sop.purpose",),
    "brd": BRD_ENRICHMENT_FIELD_IDS,
}


def field_ids_for_document_type(document_type: str | None) -> tuple[str, ...]:
    """
    Return which enrichment keys to request for one LLM call.

    Unknown or empty types fall back to ``pdd`` (same as session default).
    """
    key = (document_type or "pdd").strip().lower()
    return _FIELDS_BY_DOCUMENT_TYPE.get(key, _FIELDS_BY_DOCUMENT_TYPE["pdd"])
