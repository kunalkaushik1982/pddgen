# Processing Status

This document captures what the system currently achieves in end-to-end processing, what is only partially in place, and what still remains to be built.

It is intended as an implementation status note, not as the target-state design spec.

For the target multi-process design, see:

- [multi-process-session-design.md](C:\Users\work\Documents\PddGenerator\docs\multi-process-session-design.md)

## Current Processing Model

The system now supports:

- one session as the main engagement container
- multiple uploaded recordings over time within the same session
- process-aware review of derived outputs inside one session
- one export file per session, even when the session contains multiple detected processes

At a high level, processing currently works like this:

1. upload session evidence
2. pair transcript/video inputs by upload batch metadata
3. generate transcript-driven draft content
4. group content into process-aware review surfaces
5. derive screenshots from video evidence
6. review, edit, ask, and export from one session

## Achieved

### 1. Session As The Main Container

The system now treats a session as:

- the evidence container
- the review container
- the export container

This is a material improvement over the earlier flat one-session-one-process assumption.

### 2. Multi-Meeting Session Support

The system supports multiple evidence uploads over time in the same session.

That includes:

- transcript uploads
- video uploads
- session template usage
- resumable uploaded draft sessions in Workspace

### 3. Process-Aware Session Review

Within a session, the UI now supports detected process separation for:

- Summary
- Process
- Diagram
- Ask

This means the session can show multiple workflows separately in review, instead of forcing one flat combined reading surface.

### 4. Session-Level Artifacts View

Artifacts are now shown as a session-level evidence inventory, not mixed into process-specific tabs.

That inventory can show:

- video/transcript pairs
- the template used for the session

This is the correct scope because raw artifacts belong to the session, not inherently to one process.

### 5. Ask Is Process-Scoped

The Ask surface now follows the selected process context instead of using one global session-wide answer space.

That reduces cross-process contamination in answers.

### 6. Diagram Is Process-Scoped In Review

Diagram content shown in Session Detail review now follows the selected process group.

This is a major improvement over earlier mixed or session-wide diagram behavior.

### 7. Diagram Layout Persistence Support

Diagram layout persistence is now process-group aware.

That means:

- process-specific diagrams can be edited
- process-specific layout no longer leaks as badly across other processes

### 8. Evidence Pairing Is Stronger Than Before

The system no longer relies only on loose artifact ordering.

It now has stronger pairing support using:

- upload batch metadata
- upload pair index
- evidence bundle concepts

This materially improves video/transcript alignment for fresh sessions.

### 9. Screenshot Processing Is More Provenance-Aware

Screenshot generation now behaves materially better for fresh sessions because it is tied more closely to persisted provenance instead of broad inference.

This has reduced cross-process screenshot contamination in new clean sessions.

### 10. Single Session Export Rule

The current direction is now aligned with:

- one session
- one export file

Even when a session contains multiple processes, the session remains the export container.

### 11. Workspace Draft Handling Is Stronger

Workspace now supports:

- upload inputs
- continue uploaded draft later
- delete draft
- resumable uploaded draft sessions
- removal of selected uploaded evidence rows
- app-native confirmation modals instead of browser prompts
- prevention of duplicate draft creation from repeated upload clicks

### 12. My Projects And Session Detail UX Are More Aligned

Current UX improvements include:

- `Extend` flow from `My Projects`
- `Generate Screenshots` available from `My Projects` and Session Detail
- Session Detail top-level mode separation into:
  - View
  - Edit
  - Artifacts
- export grouped under one `Export` action in Session Detail

### 13. Theme System Is Externalized And Persistent

Theme support now includes:

- env-driven theme presets
- persisted user selection
- startup theme bootstrap before first paint
- improved light-theme contrast in shared UI surfaces

## Partial

### 1. Process Grouping Logic Exists, But Is Not Yet Enterprise-Grade

The system now has process-aware review behavior, but the classifier logic is still not strong enough to be considered a full workflow-boundary engine.

It can handle many simpler same-vs-different process cases, but it is not yet a robust segment-level enterprise workflow classifier.

### 2. Screenshot Counts Can Be Misleading For Older Sessions

For sessions created before the recent worker-side screenshot count fix:

- `My Projects` can still show stale screenshot counts from old action-log values

New reruns after worker restart should align better, but old historical values are not automatically rewritten.

### 3. Screenshot Lineage Is Stronger For Fresh Sessions Than For Old Contaminated Sessions

Fresh sessions now behave materially better.

Older sessions that already went through multiple generations, regroupings, and screenshot reruns may still contain legacy contamination.

### 4. Export Structure Has Improved, But The Full Multi-Process Export Path Is Still Maturing

The product direction is now clearly:

- one session
- one export
- process-wise sections inside that export

That rule is established, and parts of the implementation support it, but this should still be treated as an evolving area rather than fully complete architecture.

## Not Yet Achieved

### 1. True Incremental Rebuild

Current regeneration is still effectively full rebuild behavior.

That means when new evidence is added, the session is still broadly rebuilt rather than only updating the affected process group.

Target future behavior is:

- same-process evidence updates only that process group
- different-process evidence creates a new process group
- unrelated groups remain untouched

### 2. Strong Workflow-Boundary Classification

The system does not yet have a strong classifier that can reliably reason over:

- business goal
- action continuity
- handoff relationship
- whether later steps are downstream of earlier steps

That remains a planned capability.

### 3. Segment-Level Multi-Workflow Handling In One Long Recording

The target behavior for one long recording containing multiple workflows is not yet fully implemented at the segment level.

That remains an important future architecture step.

### 4. AI + HITL Process Resolution

The product direction now favors:

- AI-assisted process resolution
- human-in-the-loop confirmation for ambiguous cases

This is the right approach, but it is not yet fully implemented as a durable end-to-end interaction model.

## Practical Status Summary

The system has moved from:

- one flat session-wide process interpretation

to:

- one session as a container for multi-process review and export
- stronger evidence pairing
- process-aware review surfaces
- cleaner workspace and project workflows

This is a meaningful architectural and product improvement.

The major remaining gap is not basic session handling anymore.

The major remaining gap is:

- stronger process resolution
- stronger incremental regeneration
- stronger workflow-boundary intelligence

## Recommended Next Steps

### 1. Build The Stronger Workflow-Boundary Strategy

Focus on:

- segment extraction
- semantic enrichment
- process boundary detection
- AI + HITL classification

### 2. Move From Full Rebuild To Incremental Rebuild

Target:

- process-group-scoped regeneration
- leave unrelated processes untouched

### 3. Tighten Historical Session Consistency

Introduce a safer path for:

- rerun from clean evidence
- repair stale derived counts
- reduce legacy contamination in old sessions

### 4. Keep Improving BA-Facing UX

Continue improving:

- wording
- confirmation patterns
- evidence visibility
- progress clarity

The architecture is now strong enough that UX polish is worth the effort.

### 5. Upgrade Artifact Delivery For Production-Grade Screenshot Performance

Near-term target for current VPS/local-storage deployments:

- backend-authorized artifact access
- nginx-served local screenshot delivery
- direct image URL rendering instead of blob-fetch rendering

Future hardening scope:

- object storage + signed URLs
- immutable cache headers
- artifact access audit logging where needed
- thumbnail support for large screenshot sets
- lazy loading in screenshot-heavy review surfaces
- short-lived URL expiry
- no public exposure of raw storage paths
