# Multi-Meeting Implementation Notes

This document describes the current implementation approach on branch `feature/multi-meeting`.

## What is implemented (MVP)
- Adds `meetings` as a first-class entity under a `draft_session`.
- Links `artifacts`, `process_steps`, and `process_notes` to a meeting via `meeting_id`.
- Upload endpoints accept an optional `meeting_id` and default to the first meeting when omitted.
- Worker persists `meeting_id` onto generated steps/notes based on the transcript artifact that produced them.
- Frontend shows a simple Meetings panel in Session Detail:
  - list/create meetings
  - upload additional transcript/video evidence into a selected meeting

## API (backend)

### Meetings
- `GET /api/draft-sessions/{session_id}/meetings`
  - returns ordered list of meetings
  - guarantees at least one meeting exists (creates default meeting lazily for older sessions)
- `POST /api/draft-sessions/{session_id}/meetings`
  - creates a meeting at the end of the order
- `PATCH /api/draft-sessions/{session_id}/meetings/reorder`
  - sets explicit meeting order based on the provided id list
- `PATCH /api/draft-sessions/{session_id}/meetings/{meeting_id}`
  - updates title/date/order_index when those fields are provided

### Uploads
- `POST /api/uploads/sessions`
  - creates the session and ensures a default meeting exists
- `POST /api/uploads/sessions/{session_id}/artifacts`
  - accepts optional `meeting_id` (form field)
  - if omitted, backend assigns the default meeting for the session

## Default behavior (no BA review)
- Meeting order is stable via:
  - explicit `order_index` when set
  - otherwise meeting timestamps
- Steps/notes retain provenance through `meeting_id`.
- Canonical merge logic (latest-wins conflict resolution) is not implemented yet; this MVP focuses on evidence grouping and provenance.

## Migration
Alembic revision:
- `20260319_0002` adds the `meetings` table and `meeting_id` columns.

For existing DBs:
- apply migrations via `alembic upgrade head` (or stamp then upgrade if your DB was pre-Alembic).

