# Draft Generation Call Map

## Purpose

`worker/services/draft_generation/` owns the main business pipeline for transcript-to-draft generation.

## Public Entrypoints

| File | Public entrypoint | Called by | Returns |
|---|---|---|---|
| `worker/services/draft_generation/worker.py` | `DraftGenerationWorker.run(session_id)` | `worker/tasks/draft_generation.py` | `dict[str, int | str]` |
| `worker/services/draft_generation/input_stages.py` | `SessionPreparationStage.load_and_prepare(db, session)` | orchestration composition/use case | `DraftGenerationContext` |
| `worker/services/draft_generation/input_stages.py` | `TranscriptInterpretationStage.run(db, context)` | `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/input_stages.py` | `EvidenceSegmentationStage.run(db, context)` | `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/process_stages.py` | `ProcessGroupingStage.run(db, context)` | `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/process_stages.py` | `CanonicalMergeStage.run(db, context)` | `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/diagram_assembly.py` | `DiagramAssemblyStage.run(db, context)` | `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/screenshot_derivation.py` | `ScreenshotDerivationStage.run(db, context)` | screenshot use case `OrderedStageRunner` | `None` |
| `worker/services/draft_generation/persistence.py` | `PersistenceStage.run(db, context)` | orchestration persister adapter | `dict[str, int | str]` |
| `worker/services/draft_generation/failure.py` | `FailureStage.mark_failed(db, session_id, detail)` | orchestration failure adapter | `None` |

## Who Calls Whom

- `worker.py`
  calls `orchestration.composition.build_draft_generation_use_case`
- `input_stages.py`
  calls transcript normalizer, `AITranscriptInterpreter`, fallback extractors, and `EvidenceSegmentationService`
- `process_stages.py`
  calls `ProcessGroupingService` and `CanonicalProcessMergeService`
- `diagram_assembly.py`
  calls the diagram AI skill through the AI skill registry
- `screenshot_derivation.py`
  calls `VideoFrameExtractor` and screenshot selection helpers
- `persistence.py`
  writes steps, notes, screenshot relations, diagrams, and final session status

## Shared State

- `stage_context.py`
  defines `DraftGenerationContext`, the mutable state object passed across stages
- `support.py`
  provides deterministic timestamp/action/screenshot helper functions
