# Hybrid AI Skills Session Grounded QA Design

## Purpose

This document defines the final major AI-skill migration slice for the hybrid AI architecture in `PddGenerator`.

The previous slices established:

- the worker-side hybrid AI skill framework
- `transcript_to_steps`
- `semantic_enrichment`
- `workflow_boundary_detection`
- `workflow_title_resolution`
- `workflow_group_match`
- `process_summary_generation`
- `diagram_generation`
- `workflow_capability_tagging`

This slice migrates the remaining major AI capability:

- `session_grounded_qa`

This capability answers grounded business analyst questions about one session using session evidence such as:

- steps
- notes
- transcript chunks

## Scope

This slice will implement:

- one new backend-side hybrid AI skill for grounded session Q&A
- backend-side skill wiring so the session chat service delegates the AI request/response behavior
- preservation of the current evidence-building, citation filtering, and API response shape
- focused tests and runtime logs

This slice will not implement:

- database changes
- API route changes
- UI changes
- retry or rate-limit redesign
- retrieval redesign
- evidence-model redesign

## Why This Skill Last

All previous migrations on this branch were worker-side capabilities in the draft-generation and grouping pipeline.

`session_grounded_qa` is the remaining major AI behavior outside that pipeline. It lives in the backend and has a different responsibility:

- user-facing grounded question answering

Migrating it last is appropriate because:

- it is logically separate from worker orchestration
- it already has a strong service boundary in [backend/app/services/session_chat_service.py](C:/Users/work/Documents/PddGenerator/backend/app/services/session_chat_service.py)
- its evidence-building and citation shaping should remain stable while the AI call path is extracted

## Current Architecture Snapshot

Current grounded Q&A behavior lives in:

- [backend/app/services/session_chat_service.py](C:/Users/work/Documents/PddGenerator/backend/app/services/session_chat_service.py)

That file currently does all of the following:

- checks whether AI is configured
- validates the user question
- builds bounded evidence items from steps, notes, and transcript chunks
- constructs the chat-completions payload
- calls the OpenAI-compatible endpoint
- parses JSON response
- filters citation ids against known evidence ids
- maps the result into the response returned to the API route

This slice should reduce that AI sprawl by moving only the AI request/response behavior into a skill while keeping the service as the orchestration and grounding layer.

## Goal Of This Slice

Move the AI request/response behavior for grounded session Q&A into an explicit skill module while preserving:

- current question validation behavior
- current evidence item construction
- current transcript chunking behavior
- current citation filtering against evidence ids
- current response shape:
  - `answer`
  - `confidence`
  - `citations`
- current insufficient-evidence fallback answer behavior

## Proposed Folder Structure

Add one new backend-side skill folder:

```text
backend/app/services/ai_skills/
  session_grounded_qa/
    README.md
    prompt.md
    schemas.py
    skill.py
```

If needed, a small backend-side local helper can be added later, but this slice should avoid building a full second backend skill framework unless it is truly necessary. The preferred approach is the smallest backend-side implementation that still matches the hybrid pattern:

- markdown prompt/instructions
- explicit schemas
- dedicated skill module

## Skill: Session Grounded QA

### Purpose

Answer one grounded question about one session using only the bounded evidence prepared by the service.

### Current source behavior

Today this AI behavior lives in:

- `SessionChatService.ask(...)`

### Input

The new `session_grounded_qa` skill input should include:

- `session_title`
- `process_group_id`
- `question`
- `evidence`

Where `evidence` is the bounded list of evidence items already produced by the service.

### Output

The new skill output should include:

- `answer`
- `confidence`
- `citation_ids`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the OpenAI-compatible API
- parse strict JSON through a local runtime helper or small inline helper
- normalize confidence to the existing enum:
  - `high`
  - `medium`
  - `low`
- normalize citation ids as strings

The skill should not:

- build evidence items
- read transcript files
- map citations into snippets
- decide which evidence ids are valid

Those remain service responsibilities.

## Integration Behavior

`SessionChatService.ask(...)` should:

1. continue checking AI configuration
2. continue rejecting blank questions
3. continue building evidence items through `_build_evidence_items(...)`
4. continue failing early when no grounded evidence exists
5. delegate the AI request/response behavior to `session_grounded_qa`
6. continue filtering returned citation ids against known evidence ids
7. continue building the final API response with:
   - `answer`
   - `confidence`
   - `citations`

This keeps product policy and grounding in the service while moving the AI behavior into a skill.

## Compatibility Strategy

Compatibility rules:

- keep [backend/app/services/session_chat_service.py](C:/Users/work/Documents/PddGenerator/backend/app/services/session_chat_service.py) as the orchestration and grounding layer
- do not change the draft session API route contract
- do not change the existing evidence-item shape
- do not change transcript chunking limits in this slice
- move only the AI request/response behavior into a skill

This matches the pattern already used throughout this branch:

- service owns policy and orchestration
- skill owns AI-specific behavior

## Files To Modify

### New files

- `backend/app/services/ai_skills/session_grounded_qa/README.md`
- `backend/app/services/ai_skills/session_grounded_qa/prompt.md`
- `backend/app/services/ai_skills/session_grounded_qa/schemas.py`
- `backend/app/services/ai_skills/session_grounded_qa/skill.py`
- `backend/tests/test_session_grounded_qa_skill.py`

### Existing files to modify

- [backend/app/services/session_chat_service.py](C:/Users/work/Documents/PddGenerator/backend/app/services/session_chat_service.py)

### Reference files

- [backend/app/api/routes/draft_sessions.py](C:/Users/work/Documents/PddGenerator/backend/app/api/routes/draft_sessions.py)
- [backend/app/schemas/draft_session.py](C:/Users/work/Documents/PddGenerator/backend/app/schemas/draft_session.py)

## Logging Expectations

This slice should follow the same runtime-proof pattern as earlier slices.

Expected logs should include:

- session-chat-service delegation log for `session_grounded_qa`
- skill execution log from the new skill module

This will make later backend verification straightforward.

## Testing Strategy

This slice should add focused tests for:

- grounded-Q&A request/response schemas
- prompt/message building
- confidence and citation-id normalization
- session-chat-service compatibility wiring
- citation filtering staying in the service layer

The tests should follow the same direct-file runnable pattern used in the earlier skill migrations where possible.

## Success Criteria

This slice is successful when:

- grounded session Q&A AI behavior lives in `session_grounded_qa`
- `SessionChatService` still controls evidence building and citation shaping
- focused tests pass
- later backend runs can prove the new skill path through logs
