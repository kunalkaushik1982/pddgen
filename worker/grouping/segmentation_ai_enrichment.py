from __future__ import annotations

import logging

from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.ai_skills.semantic_enrichment.schemas import SemanticEnrichmentRequest
from worker.ai_skills.semantic_enrichment.skill import SemanticEnrichmentSkill
from worker.services.workflow_intelligence import EvidenceSegment, SemanticEnrichment
from worker.grouping.segmentation_enrichment_heuristics import HeuristicSemanticEnrichmentStrategy
from worker.grouping.segmentation_interpreter_adapters import InterpreterSemanticEnrichmentSkill

logger = logging.getLogger(__name__)


class AISemanticEnrichmentStrategy:
    """AI-first segment enrichment strategy with deterministic fallback."""

    strategy_key = "ai_plus_heuristic_v1"

    def __init__(
        self,
        *,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        fallback_strategy: HeuristicSemanticEnrichmentStrategy | None = None,
    ) -> None:
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.fallback_strategy = fallback_strategy or HeuristicSemanticEnrichmentStrategy()
        self._semantic_enrichment_skill = (
            InterpreterSemanticEnrichmentSkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else SemanticEnrichmentSkill()
        )

    def enrich(self, segment: EvidenceSegment) -> SemanticEnrichment:
        fallback_enrichment = self.fallback_strategy.enrich(segment)
        logger.info(
            "Delegating semantic enrichment to AI skill.",
            extra={
                "skill_id": self._semantic_enrichment_skill.skill_id,
                "skill_version": self._semantic_enrichment_skill.version,
                "segment_id": segment.id,
                "transcript_artifact_id": segment.transcript_artifact_id,
            },
        )
        ai_result = self._semantic_enrichment_skill.run(
            SemanticEnrichmentRequest(
                transcript_name=segment.transcript_artifact_id,
                segment_text=segment.text,
                segment_context={
                    "segment_order": segment.segment_order,
                    "start_timestamp": segment.start_timestamp or "",
                    "end_timestamp": segment.end_timestamp or "",
                    "segmentation_method": segment.segmentation_method,
                },
            )
        )
        if ai_result is None:
            return fallback_enrichment
        if ai_result.confidence not in {"high", "medium"}:
            fallback_enrichment.enrichment_source = "heuristic_fallback"
            return fallback_enrichment
        resolved = SemanticEnrichment(
            actor=ai_result.actor or fallback_enrichment.actor,
            actor_role=ai_result.actor_role or fallback_enrichment.actor_role,
            system_name=ai_result.system_name or fallback_enrichment.system_name,
            action_verb=ai_result.action_verb or fallback_enrichment.action_verb,
            action_type=ai_result.action_type or fallback_enrichment.action_type,
            business_object=ai_result.business_object or fallback_enrichment.business_object,
            workflow_goal=ai_result.workflow_goal or fallback_enrichment.workflow_goal,
            rule_hints=ai_result.rule_hints or fallback_enrichment.rule_hints,
            domain_terms=ai_result.domain_terms or fallback_enrichment.domain_terms,
            confidence=ai_result.confidence,
            enrichment_source="ai",
        )
        if not self._has_meaningful_ai_signal(resolved):
            fallback_enrichment.enrichment_source = "heuristic_fallback"
            return fallback_enrichment
        return resolved

    @staticmethod
    def _has_meaningful_ai_signal(enrichment: SemanticEnrichment) -> bool:
        return any((enrichment.business_object, enrichment.workflow_goal, enrichment.system_name, enrichment.action_verb, enrichment.actor)) or bool(enrichment.domain_terms)
