/**
 * Purpose: Upload form for required and optional draft session artifacts.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\UploadPage.tsx
 */

import React from "react";

import type { ArtifactUploadState } from "../types/workflow";

type UploadPageProps = {
  title: string;
  ownerId: string;
  uploads: ArtifactUploadState;
  disabled?: boolean;
  onTitleChange: (value: string) => void;
  onOwnerIdChange: (value: string) => void;
  onFilesChange: (field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", files: FileList | null) => void;
  onSubmit: () => void;
};

export function UploadPage({
  title,
  ownerId,
  uploads,
  disabled,
  onTitleChange,
  onOwnerIdChange,
  onFilesChange,
  onSubmit,
}: UploadPageProps): JSX.Element {
  return (
    <section className="panel stack">
      <div>
        <h2>1. Create Draft Session</h2>
        <p className="muted">
          Upload the required evidence: one or more videos, one or more transcripts, and one DOCX template.
        </p>
      </div>

      <div className="field-inline">
        <label className="field-group">
          <span>Session title</span>
          <input value={title} onChange={(event) => onTitleChange(event.target.value)} placeholder="Invoice processing PDD" />
        </label>
        <label className="field-group">
          <span>Owner ID</span>
          <input value={ownerId} onChange={(event) => onOwnerIdChange(event.target.value)} placeholder="pilot-user" />
        </label>
      </div>

      <label className="field-group">
        <span>Process videos</span>
        <input type="file" accept="video/*" multiple onChange={(event) => onFilesChange("videoFiles", event.target.files)} />
      </label>

      <label className="field-group">
        <span>Transcripts (.txt, .vtt, .docx)</span>
        <input
          type="file"
          accept=".txt,.vtt,.docx,text/plain,text/vtt,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          multiple
          onChange={(event) => onFilesChange("transcriptFiles", event.target.files)}
        />
      </label>

      <label className="field-group">
        <span>PDD template (.docx)</span>
        <input
          type="file"
          accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(event) => onFilesChange("templateFile", event.target.files)}
        />
      </label>

      <div className="field-inline">
        <label className="field-group">
          <span>Optional SOP files</span>
          <input type="file" multiple onChange={(event) => onFilesChange("sopFiles", event.target.files)} />
        </label>
        <label className="field-group">
          <span>Optional diagrams</span>
          <input type="file" multiple onChange={(event) => onFilesChange("diagramFiles", event.target.files)} />
        </label>
      </div>

      <div className="artifact-meta">
        Selected: {uploads.videoFiles.length} video(s), {uploads.transcriptFiles.length} transcript(s),{" "}
        {uploads.templateFile ? "1 template" : "0 templates"}
      </div>

      <div className="button-row">
        <button type="button" className="button-primary" onClick={onSubmit} disabled={disabled}>
          Create session and upload artifacts
        </button>
      </div>
    </section>
  );
}
