# Workflow Intelligence Call Map

## Purpose

`worker/services/workflow_intelligence/` owns workflow reasoning logic used by the draft pipeline:
- evidence segmentation
- semantic enrichment
- workflow-boundary detection
- transcript grouping into processes
- canonical merge across transcripts

## Public Entrypoints

| File | Public entrypoint | Called by | Returns |
|---|---|---|---|
| `worker/services/workflow_intelligence/segmentation_service.py` | `EvidenceSegmentationService.segment_transcript(...)` | `EvidenceSegmentationStage` | `list[EvidenceSegment]` |
| `worker/services/workflow_intelligence/segmentation_service.py` | `EvidenceSegmentationService.infer_boundary_decisions(...)` | `EvidenceSegmentationStage` | `list[WorkflowBoundaryDecision]` |
| `worker/services/workflow_intelligence/grouping_service.py` | `ProcessGroupingService.assign_groups(...)` | `ProcessGroupingStage` | `ProcessGroupingResult` |
| `worker/services/workflow_intelligence/canonical_merge.py` | `CanonicalProcessMergeService.merge(...)` | `CanonicalMergeStage` | canonical merge result with steps/notes maps |
| `worker/services/workflow_intelligence/strategy_registry.py` | `WorkflowIntelligenceStrategyRegistry.create_strategy_set(...)` | orchestration composition | `WorkflowIntelligenceStrategySet` |

## Who Calls Whom

- `segmentation_service.py`
  uses segmenter, enricher, and boundary-detector strategies
- `grouping_service.py`
  uses AI-skill adapters, heuristics, and `ProcessGroupService`
- `canonical_merge.py`
  consolidates transcript-level outputs into one canonical process view
- `strategy_registry.py`
  builds the configured strategy set used by `EvidenceSegmentationService`

## Returned Data

- segmentation produces `EvidenceSegment`
- boundary inference produces `WorkflowBoundaryDecision`
- grouping produces `ProcessGroupingResult`
- canonical merge produces canonicalized steps/notes plus per-transcript maps
