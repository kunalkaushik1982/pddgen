import React from "react";

import { formatFileSize } from "../../selectors/uploadPresentation";
import type { DocumentType, InputArtifact } from "../../types/session";
import { formatDiagramTypeLabel, formatDocumentTypeLabel, formatIncludeDiagramInDraft } from "../../utils/sessionDraftLabels";

type SessionArtifactsPanelProps = {
  artifacts: InputArtifact[];
  documentType: DocumentType;
  diagramType: "flowchart" | "sequence";
  /** From latest `generation_queued` log when available */
  includeDiagramInLastDraft: boolean | null;
};

type ArtifactPair = {
  key: string;
  video: InputArtifact | null;
  transcript: InputArtifact | null;
  meetingId: string | null;
  sortCreatedAt: string | null;
};

export function SessionArtifactsPanel({
  artifacts,
  documentType,
  diagramType,
  includeDiagramInLastDraft,
}: SessionArtifactsPanelProps): React.JSX.Element {
  const videoArtifacts = artifacts.filter((artifact) => artifact.kind === "video");
  const transcriptArtifacts = artifacts.filter((artifact) => artifact.kind === "transcript");
  const templateArtifacts = artifacts.filter((artifact) => artifact.kind === "template");

  const pairedArtifacts = React.useMemo(() => {
    const pairMap = new Map<string, ArtifactPair>();
    const legacyVideos: InputArtifact[] = [];
    const legacyTranscripts: InputArtifact[] = [];

    function ensurePair(artifact: InputArtifact, kind: "video" | "transcript") {
      const hasExplicitPairing = artifact.uploadBatchId !== null || artifact.uploadPairIndex !== null;
      if (!hasExplicitPairing) {
        if (kind === "video") {
          legacyVideos.push(artifact);
        } else {
          legacyTranscripts.push(artifact);
        }
        return;
      }

      const batchPart = artifact.uploadBatchId ?? artifact.meetingId ?? "session";
      const pairPart = artifact.uploadPairIndex ?? 0;
      const key = `${batchPart}:${pairPart}`;
      const existing = pairMap.get(key) ?? {
        key,
        video: null,
        transcript: null,
        meetingId: artifact.meetingId ?? null,
        sortCreatedAt: artifact.createdAt ?? null,
      };
      if (kind === "video") {
        existing.video = artifact;
      } else {
        existing.transcript = artifact;
      }
      if (!existing.sortCreatedAt || (artifact.createdAt && artifact.createdAt < existing.sortCreatedAt)) {
        existing.sortCreatedAt = artifact.createdAt ?? existing.sortCreatedAt;
      }
      pairMap.set(key, existing);
    }

    for (const artifact of videoArtifacts) {
      ensurePair(artifact, "video");
    }
    for (const artifact of transcriptArtifacts) {
      ensurePair(artifact, "transcript");
    }

    const legacySortedVideos = [...legacyVideos].sort((left, right) => (left.createdAt ?? "").localeCompare(right.createdAt ?? ""));
    const legacySortedTranscripts = [...legacyTranscripts].sort((left, right) =>
      (left.createdAt ?? "").localeCompare(right.createdAt ?? ""),
    );
    const legacyPairCount = Math.max(legacySortedVideos.length, legacySortedTranscripts.length);
    for (let index = 0; index < legacyPairCount; index += 1) {
      const video = legacySortedVideos[index] ?? null;
      const transcript = legacySortedTranscripts[index] ?? null;
      const sortCreatedAt = video?.createdAt ?? transcript?.createdAt ?? null;
      pairMap.set(`legacy:${index}`, {
        key: `legacy:${index}`,
        video,
        transcript,
        meetingId: video?.meetingId ?? transcript?.meetingId ?? null,
        sortCreatedAt,
      });
    }

    return [...pairMap.values()].sort((left, right) => {
      const leftDate = left.sortCreatedAt ?? "";
      const rightDate = right.sortCreatedAt ?? "";
      return leftDate.localeCompare(rightDate);
    });
  }, [transcriptArtifacts, videoArtifacts]);

  return (
    <section className="panel review-subsection">
      <div className="summary-document">
        <div>
          <h3>Session Evidence</h3>
          <p className="artifact-meta">Source recordings, transcripts, and template used to build this session.</p>
        </div>
        <div className="summary-document-card artifacts-document-card">
          <div className="artifacts-section">
            <div>
              <div className="summary-document-label">Draft generation</div>
              <h3 className="summary-document-title">Document and diagram settings</h3>
            </div>
            <ul className="artifacts-settings-list artifact-meta">
              <li>
                <span className="artifacts-pair-label">Document type</span>
                <span className="artifacts-pair-value">{formatDocumentTypeLabel(documentType)}</span>
              </li>
              <li>
                <span className="artifacts-pair-label">Diagram type</span>
                <span className="artifacts-pair-value">{formatDiagramTypeLabel(diagramType)}</span>
              </li>
              <li>
                <span className="artifacts-pair-label">Include diagram in draft generation</span>
                <span className="artifacts-pair-value">{formatIncludeDiagramInDraft(includeDiagramInLastDraft)}</span>
              </li>
            </ul>
          </div>

          <div className="artifacts-section">
            <div>
              <div className="summary-document-label">Evidence Pairs</div>
              <h3 className="summary-document-title">Video and Transcript Inputs</h3>
            </div>
            {pairedArtifacts.length > 0 ? (
              <div className="artifacts-pair-list">
                {pairedArtifacts.map((pair, index) => (
                  <div key={pair.key} className="artifacts-pair-card">
                    <div className="artifacts-pair-header">
                      <strong>Evidence Pair {index + 1}</strong>
                      <span className="artifact-meta">
                        {pair.sortCreatedAt ? new Date(pair.sortCreatedAt).toLocaleString() : "Upload time unavailable"}
                      </span>
                    </div>
                    <div className="artifacts-pair-row">
                      <span className="artifacts-pair-label">Video</span>
                      <span className="artifacts-pair-value" title={pair.video?.name ?? "No video"}>
                        {pair.video?.name ?? "Not available"}
                      </span>
                      <span className="artifact-meta">{pair.video ? formatFileSize(pair.video.sizeBytes ?? 0) : ""}</span>
                    </div>
                    <div className="artifacts-pair-row">
                      <span className="artifacts-pair-label">Transcript</span>
                      <span className="artifacts-pair-value" title={pair.transcript?.name ?? "No transcript"}>
                        {pair.transcript?.name ?? "Not available"}
                      </span>
                      <span className="artifact-meta">
                        {pair.transcript ? formatFileSize(pair.transcript.sizeBytes ?? 0) : ""}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No video/transcript inputs are associated with this session.</div>
            )}
          </div>

          <div className="artifacts-section">
            <div>
              <div className="summary-document-label">Template</div>
              <h3 className="summary-document-title">{formatDocumentTypeLabel(documentType)} template used</h3>
            </div>
            {templateArtifacts.length > 0 ? (
              <div className="artifacts-template-list">
                {templateArtifacts.map((artifact) => (
                  <div key={artifact.id} className="artifacts-template-card">
                    <strong title={artifact.name}>{artifact.name}</strong>
                    <span className="artifact-meta">{formatFileSize(artifact.sizeBytes ?? 0)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No template artifact is available for this session.</div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
