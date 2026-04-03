from __future__ import annotations

import re
from uuid import uuid4

from worker.services.draft_generation.support import ACTION_VERB_PATTERNS, TIMESTAMP_PATTERN, classify_action_type
from worker.services.workflow_intelligence import EvidenceSegment, SemanticEnrichment, WorkflowBoundaryDecision


class ParagraphTranscriptSegmentationStrategy:
    """Default transcript chunking strategy based on paragraph and timestamp continuity."""

    strategy_key = "paragraph_v1"

    def segment(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        chunks = [chunk.strip() for chunk in re.split(r"(?:\r?\n){2,}", transcript_text) if chunk.strip()]
        if not chunks:
            chunks = [line.strip() for line in transcript_text.splitlines() if line.strip()]

        segments: list[EvidenceSegment] = []
        for index, chunk in enumerate(chunks, start=1):
            timestamps = self._extract_timestamps(chunk)
            segments.append(
                EvidenceSegment(
                    id=str(uuid4()),
                    transcript_artifact_id=transcript_artifact_id,
                    meeting_id=meeting_id,
                    segment_order=index,
                    text=chunk,
                    start_timestamp=timestamps[0] if timestamps else None,
                    end_timestamp=timestamps[-1] if timestamps else None,
                    segmentation_method="timestamp_paragraph" if timestamps else "paragraph_fallback",
                    confidence="medium" if timestamps else "low",
                )
            )
        return segments

    @staticmethod
    def _extract_timestamps(text: str) -> list[str]:
        timestamps: list[str] = []
        for match in TIMESTAMP_PATTERN.finditer(text):
            hours_group, minutes_group, seconds_group = match.groups()
            hours = int(hours_group or 0)
            minutes = int(minutes_group)
            seconds = int(seconds_group)
            timestamps.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return timestamps


class HeuristicSemanticEnrichmentStrategy:
    """Default semantic enrichment strategy using lightweight text heuristics."""

    strategy_key = "heuristic_v2"

    SYSTEM_PATTERNS = (
        re.compile(r"\b(sap gui|sap|oracle|salesforce|sfdc|excel|outlook|portal|application|app)\b", re.IGNORECASE),
        re.compile(r"\b(transaction code|t[\-\s]?code|screen|menu|form)\b", re.IGNORECASE),
    )
    OBJECT_PATTERN = re.compile(
        r"\b(purchase order|sales order|vendor master|vendor|invoice|claim|patient record|patient|matter|contract|account|record|case|order|request)\b",
        re.IGNORECASE,
    )
    ACTOR_PATTERNS = (
        (re.compile(r"\b(user|operator|analyst|employee|processor)\b", re.IGNORECASE), "operator"),
        (re.compile(r"\b(approver|reviewer|manager|lead)\b", re.IGNORECASE), "approver"),
        (re.compile(r"\b(customer|client|patient|vendor)\b", re.IGNORECASE), "external_party"),
        (re.compile(r"\b(system|application)\b", re.IGNORECASE), "system"),
    )
    RULE_PATTERNS = (
        re.compile(r"\bmust\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bshould\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\brequired\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bvalidate\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\breview\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bensure\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bif\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bbefore\b.*?(?:\.|$)", re.IGNORECASE),
    )
    DOMAIN_STOPWORDS = {
        "the", "and", "then", "into", "from", "with", "that", "this", "your", "their",
        "record", "screen", "field", "system", "application", "process", "transaction",
        "details", "review", "validate",
    }

    def enrich(self, segment: EvidenceSegment) -> SemanticEnrichment:
        lowered = segment.text.lower()
        action_verb = next((pattern for patterns in ACTION_VERB_PATTERNS.values() for pattern in patterns if pattern in lowered), None)
        action_type = classify_action_type(segment.text)
        system_name = self._extract_system_name(segment.text)
        object_match = self.OBJECT_PATTERN.search(segment.text)
        actor, actor_role = self._extract_actor(segment.text)
        business_object = object_match.group(1).title() if object_match else None
        workflow_goal = self._build_workflow_goal(action_verb, business_object)
        rule_hints = self._extract_rule_hints(segment.text)
        domain_terms = self._extract_domain_terms(segment.text, business_object=business_object)
        signal_count = sum(1 for item in (actor, system_name, action_verb, business_object, workflow_goal) if item) + len(rule_hints)
        return SemanticEnrichment(
            actor=actor,
            actor_role=actor_role,
            system_name=system_name,
            action_verb=action_verb,
            action_type=action_type,
            business_object=business_object,
            workflow_goal=workflow_goal,
            rule_hints=rule_hints,
            domain_terms=domain_terms,
            confidence=self._confidence_from_signal_count(signal_count),
            enrichment_source="heuristic",
        )

    def _extract_system_name(self, text: str) -> str | None:
        for pattern in self.SYSTEM_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper()
        return None

    def _extract_actor(self, text: str) -> tuple[str | None, str | None]:
        for pattern, actor_role in self.ACTOR_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).title(), actor_role
        return None, None

    @staticmethod
    def _build_workflow_goal(action_verb: str | None, business_object: str | None) -> str | None:
        if action_verb and business_object:
            return f"{action_verb.title()} {business_object}".strip()
        return business_object

    def _extract_rule_hints(self, text: str) -> list[str]:
        rule_hints: list[str] = []
        for pattern in self.RULE_PATTERNS:
            for match in pattern.findall(text):
                normalized = re.sub(r"\s+", " ", match.strip().rstrip("."))
                if normalized and normalized not in rule_hints:
                    rule_hints.append(normalized)
        return rule_hints[:4]

    def _extract_domain_terms(self, text: str, *, business_object: str | None) -> list[str]:
        normalized = re.sub(r"[^a-z0-9\s]+", " ", text.lower())
        tokens = [token for token in normalized.split() if len(token) > 3 and token not in self.DOMAIN_STOPWORDS]
        ordered_terms: list[str] = []
        seen: set[str] = set()
        if business_object:
            normalized_object = business_object.lower()
            ordered_terms.append(normalized_object)
            seen.add(normalized_object)
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            ordered_terms.append(token)
            if len(ordered_terms) >= 6:
                break
        return ordered_terms

    @staticmethod
    def _confidence_from_signal_count(signal_count: int) -> str:
        if signal_count >= 5:
            return "high"
        if signal_count >= 2:
            return "medium"
        return "low"


class HeuristicWorkflowBoundaryStrategy:
    """Default adjacent-segment continuity strategy using shared object/system signals."""

    strategy_key = "heuristic_v2"

    def decide(self, left: EvidenceSegment, right: EvidenceSegment) -> WorkflowBoundaryDecision:
        left_enrichment = left.enrichment
        right_enrichment = right.enrichment
        if left_enrichment is None or right_enrichment is None:
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision="uncertain",
                confidence="low",
                reason="One or both segments did not contain enrichment signals.",
                decision_source="heuristic",
                heuristic_decision="uncertain",
                heuristic_confidence="low",
            )

        overlap_score = 0.0
        reasons: list[str] = []
        if left_enrichment.business_object and left_enrichment.business_object == right_enrichment.business_object:
            overlap_score += 0.45
            reasons.append(f"shared object '{left_enrichment.business_object}'")
        elif left_enrichment.business_object and right_enrichment.business_object:
            overlap_score -= 0.35
            reasons.append("different business objects")
        if left_enrichment.workflow_goal and left_enrichment.workflow_goal == right_enrichment.workflow_goal:
            overlap_score += 0.3
            reasons.append(f"shared goal '{left_enrichment.workflow_goal}'")
        elif left_enrichment.workflow_goal and right_enrichment.workflow_goal:
            overlap_score -= 0.2
            reasons.append("different workflow goals")
        if left_enrichment.system_name and left_enrichment.system_name == right_enrichment.system_name:
            overlap_score += 0.2
            reasons.append(f"shared system '{left_enrichment.system_name}'")
        if left_enrichment.action_type and left_enrichment.action_type == right_enrichment.action_type:
            overlap_score += 0.1
            reasons.append(f"shared action type '{left_enrichment.action_type}'")
        left_terms = set(left_enrichment.domain_terms)
        right_terms = set(right_enrichment.domain_terms)
        if left_terms and right_terms:
            shared_terms = left_terms & right_terms
            if shared_terms:
                overlap_score += min(0.2, 0.05 * len(shared_terms))
                reasons.append("shared domain terms: " + ", ".join(sorted(shared_terms)[:3]))
        if self._has_explicit_new_workflow_marker(right.text):
            overlap_score -= 0.4
            reasons.append("explicit new-workflow marker in right segment")
        if self._is_timestamp_contiguous(left, right):
            overlap_score += 0.05
            reasons.append("contiguous evidence timing")

        if overlap_score >= 0.45:
            decision = "same_workflow"
            confidence = "high" if overlap_score >= 0.7 else "medium"
        elif overlap_score <= -0.2:
            decision = "new_workflow"
            confidence = "medium"
        else:
            decision = "uncertain"
            confidence = "low" if overlap_score < 0.2 else "medium"

        reason = "; ".join(reasons) if reasons else "No clear continuity signal."
        return WorkflowBoundaryDecision(
            left_segment_id=left.id,
            right_segment_id=right.id,
            decision=decision,
            confidence=confidence,
            reason=reason,
            decision_source="heuristic",
            heuristic_decision=decision,
            heuristic_confidence=confidence,
        )

    @staticmethod
    def _has_explicit_new_workflow_marker(text: str) -> bool:
        normalized = text.lower()
        markers = ("now we will create", "next we will create", "moving to", "switch to", "another process", "different process", "new workflow")
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _is_timestamp_contiguous(left: EvidenceSegment, right: EvidenceSegment) -> bool:
        if not left.end_timestamp or not right.start_timestamp:
            return False
        return left.end_timestamp == right.start_timestamp
