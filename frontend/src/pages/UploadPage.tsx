/**
 * Purpose: Upload form for required and optional draft session artifacts.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\UploadPage.tsx
 */

import React from "react";

import { uiCopy } from "../constants/uiCopy";
import { formatFileSize, getUploadStatusLabel } from "../selectors/uploadPresentation";
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
  onRemoveSelectedFile?: (field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", index: number) => void;
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
  onRemoveSelectedFile,
  onUploadInputs,
  onSubmit,
}: UploadPageProps): React.JSX.Element {
  const videoInputRef = React.useRef<HTMLInputElement | null>(null);
  const transcriptInputRef = React.useRef<HTMLInputElement | null>(null);
  const templateInputRef = React.useRef<HTMLInputElement | null>(null);
  const localVideoFiles = uploads.videoFiles;
  const localTranscriptFiles = uploads.transcriptFiles;
  const localTemplateFile = uploads.templateFile;
  const displayVideoFiles =
    localVideoFiles.length > 0
      ? localVideoFiles.map((file) => ({ name: file.name, size: file.size }))
      : uploadItems
          .filter((item) => item.artifactKind === "video")
          .map((item) => ({ name: item.name, size: item.size }));
  const displayTranscriptFiles =
    localTranscriptFiles.length > 0
      ? localTranscriptFiles.map((file) => ({ name: file.name, size: file.size }))
      : uploadItems
          .filter((item) => item.artifactKind === "transcript")
          .map((item) => ({ name: item.name, size: item.size }));
  const displayTemplateFile =
    localTemplateFile
      ? { name: localTemplateFile.name, size: localTemplateFile.size }
      : (() => {
          const uploadedTemplate = uploadItems.find((item) => item.artifactKind === "template");
          return uploadedTemplate ? { name: uploadedTemplate.name, size: uploadedTemplate.size } : null;
        })();

  function handleRemoveSelectedFile(field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", index: number): void {
    onRemoveSelectedFile?.(field, index);
    if (field === "videoFiles" && videoInputRef.current) {
      videoInputRef.current.value = "";
    }
    if (field === "transcriptFiles" && transcriptInputRef.current) {
      transcriptInputRef.current.value = "";
    }
    if (field === "templateFile" && templateInputRef.current) {
      templateInputRef.current.value = "";
    }
  }

  function handleRemoveSelectedEvidencePair(index: number): void {
    if (displayVideoFiles[index]) {
      handleRemoveSelectedFile("videoFiles", index);
    }
    if (displayTranscriptFiles[index]) {
      handleRemoveSelectedFile("transcriptFiles", index);
    }
  }

  const selectedEvidencePairs = Array.from({
    length: Math.max(displayVideoFiles.length, displayTranscriptFiles.length),
  }).map((_, index) => ({
    index,
    videoFile: displayVideoFiles[index] ?? null,
    transcriptFile: displayTranscriptFiles[index] ?? null,
  }));
  const videoUploadItems = uploadItems.filter((item) => item.artifactKind === "video");
  const transcriptUploadItems = uploadItems.filter((item) => item.artifactKind === "transcript");
  const templateUploadItem = uploadItems.find((item) => item.artifactKind === "template") ?? null;

  function buildCombinedUploadState(items: ArtifactUploadProgressItem[]): {
    tone: ArtifactUploadProgressItem["status"];
    progress: number;
    label: string;
  } {
    if (items.length === 0) {
      return { tone: "pending", progress: 0, label: "Pending" };
    }
    if (items.some((item) => item.status === "failed")) {
      const failedItem = items.find((item) => item.status === "failed");
      return {
        tone: "failed",
        progress: Math.max(...items.map((item) => item.progress)),
        label: failedItem?.error || "Failed",
      };
    }
    if (items.some((item) => item.status === "uploading")) {
      const progress = Math.round(items.reduce((sum, item) => sum + item.progress, 0) / items.length);
      return {
        tone: "uploading",
        progress,
        label: `Uploading ${progress}%`,
      };
    }
    if (items.every((item) => item.status === "uploaded")) {
      return { tone: "uploaded", progress: 100, label: "Uploaded" };
    }
    const progress = Math.round(items.reduce((sum, item) => sum + item.progress, 0) / items.length);
    return { tone: "pending", progress, label: getUploadStatusLabel(items[0].status) };
  }

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

      <div className="upload-workspace">
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
              <input
                ref={videoInputRef}
                type="file"
                accept="video/*"
                multiple
                onChange={(event) => onFilesChange("videoFiles", event.target.files)}
              />
            </label>

            <label className="field-group upload-field-card">
              <span>Transcripts (.txt, .vtt, .docx)</span>
              <input
                ref={transcriptInputRef}
                type="file"
                accept=".txt,.vtt,.docx,text/plain,text/vtt,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                multiple
                onChange={(event) => onFilesChange("transcriptFiles", event.target.files)}
              />
            </label>

            <label className="field-group upload-field-card">
              <span>PDD template (.docx)</span>
              <input
                ref={templateInputRef}
                type="file"
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => onFilesChange("templateFile", event.target.files)}
              />
            </label>
          </div>

          <div className="artifact-meta">
            Selected: {displayVideoFiles.length} video(s), {displayTranscriptFiles.length} transcript(s),{" "}
            {displayTemplateFile ? "1 template" : "0 templates"}
          </div>

          {selectedEvidencePairs.length > 0 && onRemoveSelectedFile ? (
            <div className="selected-evidence-list">
              {selectedEvidencePairs.map((pair) => (
                <div key={`pair:${pair.index}`} className="selected-evidence-item selected-evidence-item-with-progress">
                  <div className="selected-evidence-copy">
                    <span className="selected-evidence-label">
                      {pair.videoFile ? (
                        <>
                          <span className="selected-evidence-kind">Video:</span>
                          <span className="selected-evidence-name" title={pair.videoFile.name}>
                            {pair.videoFile.name}
                          </span>
                          <span className="selected-evidence-size">({formatFileSize(pair.videoFile.size)})</span>
                        </>
                      ) : (
                        <span className="selected-evidence-missing">No video selected</span>
                      )}
                      <span className="selected-evidence-divider">|</span>
                      {pair.transcriptFile ? (
                        <>
                          <span className="selected-evidence-kind">Transcript:</span>
                          <span className="selected-evidence-name" title={pair.transcriptFile.name}>
                            {pair.transcriptFile.name}
                          </span>
                          <span className="selected-evidence-size">({formatFileSize(pair.transcriptFile.size)})</span>
                        </>
                      ) : (
                        <span className="selected-evidence-missing">No transcript selected</span>
                      )}
                    </span>
                    {(() => {
                      const uploadState = buildCombinedUploadState(
                        [videoUploadItems[pair.index], transcriptUploadItems[pair.index]].filter(Boolean) as ArtifactUploadProgressItem[],
                      );
                      return (
                        <div className="selected-evidence-progress-block">
                          <div className="selected-evidence-progress-track" aria-hidden="true">
                            <div
                              className={`selected-evidence-progress-fill selected-evidence-progress-${uploadState.tone}`}
                              style={{ width: `${uploadState.progress}%` }}
                            />
                          </div>
                          <div className={`selected-evidence-progress-label selected-evidence-progress-label-${uploadState.tone}`}>
                            {uploadState.label}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                  <div className="selected-evidence-actions">
                    <button
                      type="button"
                      className="button-icon"
                      aria-label={`Remove selected evidence pair ${pair.index + 1}`}
                      onClick={() => handleRemoveSelectedEvidencePair(pair.index)}
                    >
                      X
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {displayTemplateFile && onRemoveSelectedFile ? (
            <div className="selected-evidence-list">
              <div className="selected-evidence-item selected-evidence-item-with-progress">
                <div className="selected-evidence-copy">
                  <span className="selected-evidence-label">
                    <span className="selected-evidence-kind">Template:</span>
                    <span className="selected-evidence-name" title={displayTemplateFile.name}>
                      {displayTemplateFile.name}
                    </span>
                    <span className="selected-evidence-size">({formatFileSize(displayTemplateFile.size)})</span>
                  </span>
                  {(() => {
                    const uploadState = buildCombinedUploadState(templateUploadItem ? [templateUploadItem] : []);
                    return (
                      <div className="selected-evidence-progress-block">
                        <div className="selected-evidence-progress-track" aria-hidden="true">
                          <div
                            className={`selected-evidence-progress-fill selected-evidence-progress-${uploadState.tone}`}
                            style={{ width: `${uploadState.progress}%` }}
                          />
                        </div>
                        <div className={`selected-evidence-progress-label selected-evidence-progress-label-${uploadState.tone}`}>
                          {uploadState.label}
                        </div>
                      </div>
                    );
                  })()}
                </div>
                <button
                  type="button"
                  className="button-icon"
                  aria-label={`Remove ${displayTemplateFile.name}`}
                  onClick={() => handleRemoveSelectedFile("templateFile", 0)}
                >
                  X
                </button>
              </div>
            </div>
          ) : null}

          {displayVideoFiles.length > 1 || displayTranscriptFiles.length > 1 ? (
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
      </div>
    </section>
  );
}
