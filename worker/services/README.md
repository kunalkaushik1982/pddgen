# Worker Services Map

This folder is organized by execution layer rather than by random helpers.

Main runtime entrypoints:
- `worker/tasks/draft_generation.py`
  Calls `worker.services.draft_generation.worker.DraftGenerationWorker`
- `worker/tasks/screenshot_generation.py`
  Calls `worker.services.screenshot_generation.worker.ScreenshotGenerationWorker`

Top-level flow:
1. Task entrypoint creates a thin worker adapter.
2. Worker adapter asks `worker.services.orchestration.composition` for a use case.
3. Use case runs inside `worker.services.orchestration.use_cases`.
4. Ordered stages execute through `worker.services.orchestration.pipeline`.
5. Stages delegate to draft, screenshot, workflow-intelligence, media, and AI-skill modules.

Package guide:
- `orchestration/`
  Application flow, composition root, repository/UoW abstractions, and stage runner.
- `draft_generation/`
  Draft-generation worker plus input/process/output stages and context models.
- `screenshot_generation/`
  Screenshot-only worker plus persisted-step context rebuilding.
- `workflow_intelligence/`
  Evidence segmentation, workflow grouping, canonical merge, strategy contracts/registry, and shared dataclasses.
- `media/`
  Transcript normalization and video-frame extraction helpers.
- `ai_skills/`
  Structured AI skill wrappers, prompts, request/response schemas, and registry/runtime support.

Important cross-package dependencies:
- `draft_generation.input_stages`
  uses `AITranscriptInterpreter` and `workflow_intelligence.segmentation_service`
- `draft_generation.process_stages`
  uses `workflow_intelligence.grouping_service` and `workflow_intelligence.canonical_merge`
- `draft_generation.output_stages`
  uses `AITranscriptInterpreter`, `media.video_frame_extractor`, and persistence models
- `screenshot_generation.context_builder`
  rebuilds `DraftGenerationContext` from persisted `ProcessStepModel` records
- `orchestration.composition`
  is the main place where concrete implementations are wired together

Shared typed contracts:
- `generation_types.py`
  Shared `StepRecord`, `NoteRecord`, and screenshot record types used across packages.
- `workflow_intelligence/__init__.py`
  Shared segment/boundary dataclasses used by workflow-intelligence services and tests.
