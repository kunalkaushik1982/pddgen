/**
 * Purpose: Upload form for required and optional draft session artifacts.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\UploadPage.tsx
 */

import React from "react";

import { uiCopy } from "../constants/uiCopy";
import { formatArtifactKind, formatFileSize, getUploadStatusLabel } from "../selectors/uploadPresentation";
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
  uploadReady?: boolean;
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
  uploadReady = false,
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
}: UploadPageProps): React.JSX.Element {
  const hasUploadItems = uploadItems.length > 0;

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

      <div className={`upload-workspace ${hasUploadItems ? "upload-workspace-with-sidebar" : ""}`}>
        <div className="upload-main-column">
          <div className={`field-inline ${ownerLocked ? "field-inline-single" : ""}`}>
            <label className="field-group">
              <span>Session title</span>
              <input value={title} onChange={(event) => onTitleChange(event.target.value)} placeholder={uiCopy.draftTitlePlaceholder} />
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
                  placeholder={uiCopy.ownerIdPlaceholder}
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

          {uploads.videoFiles.length > 1 || uploads.transcriptFiles.length > 1 ? (
            <div className="artifact-meta">
              Multiple videos and transcripts are paired by upload order during screenshot extraction.
            </div>
          ) : null}

          {uploadReady ? (
            <div className="upload-ready-banner">
              <strong>Inputs uploaded</strong>
              <span className="artifact-meta">All selected files are on the server. Start processing with Generate Draft.</span>
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
              <button type="button" className="button-primary" onClick={onSubmit} disabled={disabled || !canGenerateDraft}>
                {onUploadInputs ? "Generate Draft" : submitLabel}
              </button>
            </div>
          ) : null}
        </div>

        {hasUploadItems ? (
          <aside className="upload-sidebar">
            <div className="upload-progress-panel upload-progress-panel-sticky">
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
                        <span className={`upload-progress-badge upload-progress-${item.status}`}>{getUploadStatusLabel(item.status)}</span>
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
          </aside>
        ) : null}
      </div>
    </section>
  );
}
