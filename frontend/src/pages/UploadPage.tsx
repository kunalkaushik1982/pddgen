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
  showHeader?: boolean;
  ownerLocked?: boolean;
  showSubmitButton?: boolean;
  submitLabel?: string;
  actionBar?: React.ReactNode;
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
  showHeader = true,
  ownerLocked = false,
  showSubmitButton = true,
  submitLabel = "Create session and upload artifacts",
  actionBar,
  onTitleChange,
  onOwnerIdChange,
  onFilesChange,
  onSubmit,
}: UploadPageProps): JSX.Element {
  return (
    <section className="panel stack">
      {showHeader ? (
        <div>
          <h2>1. Create Draft Session</h2>
          <p className="muted">
            Upload the required evidence: one or more videos, one or more transcripts, and one DOCX template.
          </p>
        </div>
      ) : null}

      <div className={`field-inline ${ownerLocked ? "field-inline-single" : ""}`}>
        <label className="field-group">
          <span>Session title</span>
          <input value={title} onChange={(event) => onTitleChange(event.target.value)} placeholder="Invoice processing PDD" />
        </label>
        {!ownerLocked ? (
          <label className="field-group">
            <span>Owner ID</span>
            <input
              value={ownerId}
              onChange={(event) => onOwnerIdChange(event.target.value)}
              placeholder="pilot-user"
            />
          </label>
        ) : null}
      </div>

      <div className="upload-grid">
        <label className="field-group upload-field-card">
          <span>Process videos</span>
          <input type="file" accept="video/*" multiple onChange={(event) => onFilesChange("videoFiles", event.target.files)} />
        </label>

        <label className="field-group upload-field-card">
          <span>Transcripts (.txt, .vtt, .docx)</span>
          <input
            type="file"
            accept=".txt,.vtt,.docx,text/plain,text/vtt,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            multiple
            onChange={(event) => onFilesChange("transcriptFiles", event.target.files)}
          />
        </label>

        <label className="field-group upload-field-card">
          <span>PDD template (.docx)</span>
          <input
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => onFilesChange("templateFile", event.target.files)}
          />
        </label>
      </div>

      <div className="artifact-meta">
        Selected: {uploads.videoFiles.length} video(s), {uploads.transcriptFiles.length} transcript(s),{" "}
        {uploads.templateFile ? "1 template" : "0 templates"}
      </div>

      {actionBar ? <div className="session-inline-actions">{actionBar}</div> : null}

      {showSubmitButton ? (
        <div className="button-row">
          <button type="button" className="button-primary" onClick={onSubmit} disabled={disabled}>
            {submitLabel}
          </button>
        </div>
      ) : null}
    </section>
  );
}
