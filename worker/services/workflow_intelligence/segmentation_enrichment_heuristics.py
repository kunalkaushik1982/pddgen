from __future__ import annotations

import re

from worker.services.draft_generation.support import ACTION_VERB_PATTERNS, classify_action_type
from worker.services.workflow_intelligence import EvidenceSegment, SemanticEnrichment


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
        "the","and","then","into","from","with","that","this","your","their","record","screen","field","system",
        "application","process","transaction","details","review","validate",
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
