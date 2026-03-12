# Retention Policy Draft

This document defines a practical retention baseline for pilot usage.

## Artifact Categories

- Raw uploads
  Includes source videos, transcripts, templates, SOPs, and diagrams.
- Derived artifacts
  Includes generated screenshots and any normalized intermediate files created later.
- Output documents
  Includes exported DOCX files.

## Suggested Policy

- Active draft sessions: retain all artifacts
- Completed exported sessions: retain DOCX outputs, review whether raw uploads should be retained
- Failed or abandoned sessions: review and clean up after an agreed grace period

## Cleanup Strategy

Pilot phase:

- manual cleanup is acceptable
- cleanup should be done by session, not by individual files

Later phase:

- scheduled cleanup job
- session state aware cleanup rules
- configurable retention windows by artifact type

## Important Constraint

Do not delete artifacts that are still needed for BA review, export regeneration, or auditability within the pilot period.
