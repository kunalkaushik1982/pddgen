# Tasks Call Map

## Purpose

`worker/tasks/` contains the Celery entrypoints.
These files are the runtime boundary between the app queue and the worker service layer.

## Public Entrypoints

| File | Entrypoint | Called by | Returns |
|---|---|---|---|
| `worker/tasks/draft_generation.py` | `run_draft_generation(session_id)` | Celery task `draft_generation.run` | `dict[str, int | str]` with created artifact counts |
| `worker/tasks/screenshot_generation.py` | `run_screenshot_generation(session_id)` | Celery task `screenshot_generation.run` | `dict[str, int | str]` with updated screenshot counts |

## Downstream Calls

- `draft_generation.py`
  calls `worker.services.draft_generation.worker.DraftGenerationWorker`
- `screenshot_generation.py`
  calls `worker.services.screenshot_generation.worker.ScreenshotGenerationWorker`

## Error Handling

- Both tasks convert `ValueError` into `RuntimeError` for Celery retry behavior.
- Both tasks bind `task_id` and `session_id` into logging context.
