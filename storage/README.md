# Storage Notes

This folder represents the pilot storage boundary for local filesystem-based artifacts.

## Purpose

For the first test cycle, the application stores all artifacts on the local filesystem. This includes:

- uploaded videos
- uploaded transcripts
- uploaded PDD templates
- derived screenshots generated from video frames
- exported DOCX files

The local filesystem is a pilot-only storage implementation. The rest of the app should treat storage through abstraction layers so the backend can later switch to:

- internal shared storage
- SharePoint-style document storage
- S3-compatible object storage

## Local Storage Layout

The expected directory shape is:

```text
storage/
  local/
    <session-id>/
      video/
      transcript/
      template/
      sop/
      diagram/
      screenshot/
      generated-screenshots/
      exports/
```

### Folder Meanings

- `video/`: uploaded source recordings
- `transcript/`: uploaded transcript files such as `.txt`, `.vtt`, `.docx`
- `template/`: uploaded DOCX template used for rendering the PDD
- `sop/`: optional SOP documents
- `diagram/`: optional diagrams or supporting visuals
- `screenshot/`: user-provided screenshots if that path is used later
- `generated-screenshots/`: frames extracted from source videos by the worker
- `exports/`: generated DOCX outputs

## Naming Convention

Files should be stored with generated unique prefixes to avoid collisions.

Example:

```text
<uuid>_<original-filename>
```

Generated screenshots should use stable step-based names where possible.

Example:

```text
step_001.png
step_002.png
```

## Storage Rules for the Pilot

- Every artifact must belong to exactly one draft session.
- Session folders are the top-level isolation boundary.
- Raw uploads and derived artifacts must not be mixed into the same folder.
- Exported documents must be written into `exports/`.
- Generated screenshots must be written into `generated-screenshots/`.

## Retention Guidance

The pilot does not yet implement automated retention cleanup in code, but the system should assume the following operating model:

- raw uploads are temporary working artifacts
- generated screenshots are reproducible artifacts
- exported DOCX files are business outputs

Recommended initial retention policy:

- keep active session artifacts until manual review is complete
- keep exported documents longer than intermediate processing artifacts
- define a manual cleanup process for abandoned draft sessions

## Migration Path

The storage abstraction should keep the rest of the application unaware of the physical storage medium.

Future storage implementations should preserve the same conceptual structure:

- session-scoped isolation
- artifact kind separation
- stable storage paths returned to the application
- ability to read text transcripts
- ability to write binary outputs and generated screenshots

## Operational Notes

- local storage is suitable only for pilot and local development use
- production should not rely on local disk as the final long-term storage strategy
- if multiple app instances are introduced later, local storage must be replaced by shared or object-backed storage
