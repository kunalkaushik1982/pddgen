r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\process_grouping_service.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.services.process_group_service import ProcessGroupService
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter

logger = get_logger(__name__)


@dataclass(slots=True)
class ProcessGroupingResult:
    process_groups: list[ProcessGroupModel]
    transcript_group_ids: dict[str, str]


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups."""

    _STOPWORDS = {
        "a",
        "an",
        "and",
        "the",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "into",
        "from",
        "then",
        "after",
        "before",
        "click",
        "select",
        "enter",
        "open",
        "go",
        "navigate",
        "screen",
        "field",
        "data",
        "details",
        "form",
        "tab",
        "save",
        "submit",
        "create",
        "creation",
        "process",
    }

    def __init__(
        self,
        *,
        process_group_service: ProcessGroupService | None = None,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
    ) -> None:
        self.process_group_service = process_group_service or ProcessGroupService()
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()

    def assign_groups(
        self,
        *,
        db,
        session: DraftSessionModel,
        transcript_artifacts: list[ArtifactModel],
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
    ) -> ProcessGroupingResult:
        process_groups: list[ProcessGroupModel] = []
        transcript_group_ids: dict[str, str] = {}

        for transcript in self._sort_transcripts(transcript_artifacts):
            transcript_steps = steps_by_transcript.get(transcript.id, [])
            transcript_notes = notes_by_transcript.get(transcript.id, [])
            inferred_title, inferred_slug, matched_group = self._resolve_group_identity(
                transcript=transcript,
                steps=transcript_steps,
                notes=transcript_notes,
                existing_groups=process_groups,
            )

            if matched_group is None:
                matched_group = self.process_group_service.create_process_group(
                    db,
                    session=session,
                    title=inferred_title,
                    canonical_slug=inferred_slug,
                    display_order=len(process_groups) + 1,
                )
                process_groups.append(matched_group)

            matched_group.summary_text = self._group_summary_seed(inferred_title=inferred_title, steps=transcript_steps, notes=transcript_notes)
            db.commit()

            transcript_group_ids[transcript.id] = matched_group.id
            for step in transcript_steps:
                step["process_group_id"] = matched_group.id
            for note in transcript_notes:
                note["process_group_id"] = matched_group.id

        return ProcessGroupingResult(process_groups=process_groups, transcript_group_ids=transcript_group_ids)

    def _resolve_group_identity(
        self,
        *,
        transcript: ArtifactModel,
        steps: list[dict],
        notes: list[dict],
        existing_groups: list[ProcessGroupModel],
    ) -> tuple[str, str, ProcessGroupModel | None]:
        existing_titles = [group.title for group in existing_groups]
        ai_result = self.ai_transcript_interpreter.infer_process_group(
            transcript_name=transcript.name,
            steps=steps,
            notes=notes,
            existing_titles=existing_titles,
        )
        if ai_result is not None:
            matched_group = next(
                (group for group in existing_groups if group.title == ai_result.matched_existing_title),
                None,
            )
            title = ai_result.process_title.strip() or self._fallback_title(transcript=transcript, steps=steps)
            slug = self._slugify(ai_result.canonical_slug or title)
            return title, slug, matched_group

        title = self._fallback_title(transcript=transcript, steps=steps)
        slug = self._slugify(title)
        matched_group = self._match_existing_group(slug=slug, title=title, steps=steps, existing_groups=existing_groups)
        return title, slug, matched_group

    def _match_existing_group(
        self,
        *,
        slug: str,
        title: str,
        steps: list[dict],
        existing_groups: list[ProcessGroupModel],
    ) -> ProcessGroupModel | None:
        for group in existing_groups:
            if slug and group.canonical_slug == slug:
                return group

        normalized_title = self._normalize_text(title)
        candidate_signature = self._signature_tokens(steps)
        best_group: ProcessGroupModel | None = None
        best_score = 0.0
        for group in existing_groups:
            title_ratio = SequenceMatcher(None, normalized_title, self._normalize_text(group.title)).ratio()
            signature_overlap = 0.0
            if getattr(group, "summary_text", ""):
                group_tokens = {token for token in self._normalize_text(group.summary_text).split() if token and token not in self._STOPWORDS}
                signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
            score = (title_ratio * 0.8) + (signature_overlap * 0.2)
            if score > best_score:
                best_score = score
                best_group = group
        return best_group if best_score >= 0.82 else None

    def _fallback_title(self, *, transcript: ArtifactModel, steps: list[dict]) -> str:
        combined = " ".join(
            [
                transcript.name,
                *[str(step.get("action_text", "") or "") for step in steps[:8]],
                *[str(step.get("supporting_transcript_text", "") or "") for step in steps[:3]],
            ]
        )
        normalized = self._normalize_text(combined)

        explicit_patterns = [
            r"\b(sales order(?: creation)?)\b",
            r"\b(purchase order(?: creation)?)\b",
            r"\b(goods receipt)\b",
            r"\b(invoice(?: creation| posting)?)\b",
        ]
        for pattern in explicit_patterns:
            match = re.search(pattern, normalized)
            if match:
                return match.group(1).title()

        signature = list(self._signature_tokens(steps))
        if signature:
            phrase = " ".join(signature[:3]).strip()
            if phrase:
                return phrase.title()
        return transcript.name.rsplit(".", 1)[0].strip() or "Process"

    def _group_summary_seed(self, *, inferred_title: str, steps: list[dict], notes: list[dict]) -> str:
        parts = [inferred_title]
        parts.extend(str(step.get("action_text", "") or "") for step in steps[:6])
        parts.extend(str(note.get("text", "") or "") for note in notes[:3])
        return " ".join(part for part in parts if part).strip()

    def _signature_tokens(self, steps: list[dict]) -> set[str]:
        text = " ".join(str(step.get("action_text", "") or "") for step in steps[:12])
        tokens = [token for token in self._normalize_text(text).split() if token and token not in self._STOPWORDS]
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return {token for token, _ in ordered[:5]}

    @staticmethod
    def _sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
        return sorted(
            transcript_artifacts,
            key=lambda artifact: (
                getattr(getattr(artifact, "meeting", None), "order_index", None)
                if getattr(getattr(artifact, "meeting", None), "order_index", None) is not None
                else 1_000_000,
                getattr(getattr(artifact, "meeting", None), "meeting_date", None).isoformat()
                if getattr(getattr(artifact, "meeting", None), "meeting_date", None) is not None
                else "",
                getattr(getattr(artifact, "meeting", None), "uploaded_at", None).isoformat()
                if getattr(getattr(artifact, "meeting", None), "uploaded_at", None) is not None
                else "",
                artifact.id,
            ),
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s-]+", " ", value.lower())
        collapsed = re.sub(r"\s+", "-", normalized.strip())
        return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"
