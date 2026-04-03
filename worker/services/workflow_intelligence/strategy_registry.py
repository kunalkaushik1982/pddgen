r"""
Purpose: Registry and factory helpers for workflow-intelligence strategies.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\workflow_strategy_registry.py
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from worker.services.workflow_intelligence.strategy_interfaces import (
    SegmentEnrichmentStrategy,
    TranscriptSegmentationStrategy,
    WorkflowBoundaryStrategy,
    WorkflowIntelligenceStrategySet,
)

TStrategy = TypeVar("TStrategy")


class WorkflowIntelligenceStrategyRegistry:
    """Resolve typed workflow-intelligence strategies by stable registry keys."""

    def __init__(self) -> None:
        self._segmenters: dict[str, Callable[[], TranscriptSegmentationStrategy]] = {}
        self._enrichers: dict[str, Callable[[], SegmentEnrichmentStrategy]] = {}
        self._boundary_detectors: dict[str, Callable[[], WorkflowBoundaryStrategy]] = {}

    def register_segmenter(self, key: str, factory: Callable[[], TranscriptSegmentationStrategy]) -> None:
        self._segmenters[key] = factory

    def register_enricher(self, key: str, factory: Callable[[], SegmentEnrichmentStrategy]) -> None:
        self._enrichers[key] = factory

    def register_boundary_detector(self, key: str, factory: Callable[[], WorkflowBoundaryStrategy]) -> None:
        self._boundary_detectors[key] = factory

    def create_strategy_set(
        self,
        *,
        segmenter_key: str,
        enricher_key: str,
        boundary_detector_key: str,
    ) -> WorkflowIntelligenceStrategySet:
        return WorkflowIntelligenceStrategySet(
            segmenter=self._resolve(self._segmenters, segmenter_key, "segmenter"),
            enricher=self._resolve(self._enrichers, enricher_key, "enricher"),
            boundary_detector=self._resolve(self._boundary_detectors, boundary_detector_key, "boundary detector"),
        )

    @staticmethod
    def _resolve(factories: dict[str, Callable[[], TStrategy]], key: str, label: str) -> TStrategy:
        try:
            return factories[key]()
        except KeyError as exc:
            available = ", ".join(sorted(factories)) or "none"
            raise ValueError(f"Unknown workflow-intelligence {label} '{key}'. Available: {available}.") from exc
