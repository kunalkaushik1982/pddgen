/**
 * Purpose: Upload form for required and optional draft session artifacts.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\UploadPage.tsx
 */

import React from "react";

import type {
  ArtifactUploadProgressItem,
  ArtifactUploadState,
  DiagramType,
} from "../types/workflow";

type UploadPageProps = {
  title: string;
  ownerId: string;
  diagramType: DiagramType;
  uploads: ArtifactUploadState;
  uploadItems: ArtifactUploadProgressItem[];
  disabled?: boolean;
  canUploadInputs?: boolean;
  canGenerateDraft?: boolean;
  showHeader?: boolean;
  ownerLocked?: boolean;
  showSubmitButton?: boolean;
  submitLabel?: string;
  actionBar?: React.ReactNode;
  onTitleChange: (value: string) => void;
  onOwnerIdChange: (value: string) => void;
  onDiagramTypeChange: (value: DiagramType) => void;
  onFilesChange: (field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", files: FileList | null) => void;
  onUploadInputs?: () => void;
  onSubmit: () => void;
};

export function UploadPage({
  title,
  ownerId,
  diagramType,
  uploads,
  uploadItems,
  disabled,
  canUploadInputs = false,
  canGenerateDraft = false,
  showHeader = true,
  ownerLocked = false,
  showSubmitButton = true,
  submitLabel = "Create session and upload artifacts",
  actionBar,
  onTitleChange,
  onOwnerIdChange,
  onDiagramTypeChange,
  onFilesChange,
  onUploadInputs,
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
        <label className="field-group">
          <span>Diagram type</span>
          <select value={diagramType} onChange={(event) => onDiagramTypeChange(event.target.value as DiagramType)}>
            <option value="flowchart">Flowchart</option>
            <option value="sequence">Sequence</option>
          </select>
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

      {uploadItems.length > 0 ? (
        <div className="upload-progress-panel">
          <div className="upload-progress-header">
            <strong>Upload status</strong>
            <span className="artifact-meta">
              {uploadItems.filter((item) => item.status === "uploaded").length}/{uploadItems.length} uploaded
            </span>
          </div>
          <div className="upload-progress-list">
            {uploadItems.map((item) => (
              <div key={item.key} className="upload-progress-card">
                <div className="upload-progress-main">
                  <div className="upload-progress-title-row">
                    <strong>{item.name}</strong>
                    <span className={`upload-progress-badge upload-progress-${item.status}`}>{getStatusLabel(item.status)}</span>
                  </div>
                  <div className="artifact-meta">
                    {formatArtifactKind(item.artifactKind)} | {formatFileSize(item.size)}
                  </div>
                  <div className="upload-progress-track" aria-hidden="true">
                    <div className={`upload-progress-fill upload-progress-${item.status}`} style={{ width: `${item.progress}%` }} />
                  </div>
                  <div className="artifact-meta">
                    {item.status === "failed" && item.error ? item.error : `${item.progress}%`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {actionBar ? <div className="session-inline-actions">{actionBar}</div> : null}

      {showSubmitButton ? (
        <div className="button-row">
          {onUploadInputs ? (
            <button type="button" className="button-secondary" onClick={onUploadInputs} disabled={disabled || !canUploadInputs}>
              Upload inputs
            </button>
          ) : null}
          <button type="button" className="button-primary" onClick={onSubmit} disabled={disabled}>
            {onUploadInputs ? "Generate Draft" : submitLabel}
          </button>
        </div>
      ) : null}
    </section>
  );
}

function formatArtifactKind(kind: ArtifactUploadProgressItem["artifactKind"]): string {
  switch (kind) {
    case "video":
      return "Video";
    case "transcript":
      return "Transcript";
    case "template":
      return "Template";
    case "sop":
      return "SOP";
    case "diagram":
      return "Diagram";
    case "screenshot":
      return "Screenshot";
    default:
      return kind;
  }
}

function getStatusLabel(status: ArtifactUploadProgressItem["status"]): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "uploading":
      return "Uploading";
    case "uploaded":
      return "Uploaded";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

function formatFileSize(size: number): string {
  if (size >= 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (size >= 1024) {
    return `${Math.round(size / 1024)} KB`;
  }
  return `${size} B`;
}
