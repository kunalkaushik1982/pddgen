from __future__ import annotations

from worker.services.workflow_intelligence.grouping_models import TranscriptWorkflowProfile


def merge_profile_lists(
    workflow_profiles: list[TranscriptWorkflowProfile],
    attribute_name: str,
    *,
    limit: int,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for profile in workflow_profiles:
        for value in getattr(profile, attribute_name):
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
            if len(ordered) >= limit:
                return ordered
    return ordered
