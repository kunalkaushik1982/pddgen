# Orchestration Call Map

## Purpose

`worker/services/orchestration/` owns worker application flow:
- build use cases
- define contracts
- run stages in order
- separate composition from business logic

## Public Entrypoints

| File | Public entrypoint | Called by | Returns |
|---|---|---|---|
| `worker/services/orchestration/composition.py` | `build_draft_generation_use_case(task_id)` | `draft_generation/worker.py` | `DraftGenerationUseCase` |
| `worker/services/orchestration/composition.py` | `build_screenshot_generation_use_case(task_id)` | `screenshot_generation/worker.py` | `ScreenshotGenerationUseCase` |
| `worker/services/orchestration/use_cases.py` | `DraftGenerationUseCase.run(session_id=...)` | draft worker adapter | `dict[str, int | str]` |
| `worker/services/orchestration/use_cases.py` | `ScreenshotGenerationUseCase.run(session_id=...)` | screenshot worker adapter | `dict[str, int | str]` |
| `worker/services/orchestration/pipeline.py` | `OrderedStageRunner.run(db, context)` | both use cases | `None` |

## Who Calls Whom

- `composition.py`
  wires repositories, context builders/loaders, stages, persisters, and failure/lock adapters
- `use_cases.py`
  opens unit of work, loads session, builds context, runs stages, persists result
- `pipeline.py`
  loops through the injected ordered stage list and calls `stage.run(db, context)`
- `repositories.py`
  loads the draft session from SQLAlchemy
- `uow.py`
  owns DB session lifecycle for worker execution

## Returned Data

- Draft flow returns counts for created steps, notes, and screenshots.
- Screenshot flow returns counts for created screenshots and updated steps.
