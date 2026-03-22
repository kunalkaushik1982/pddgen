import React from "react";

import { formatFileSize } from "../../selectors/uploadPresentation";
import type { InputArtifact } from "../../types/session";

type SessionArtifactsPanelProps = {
  artifacts: InputArtifact[];
};

type ArtifactPair = {
  key: string;
  video: InputArtifact | null;
  transcript: InputArtifact | null;
  meetingId: string | null;
  sortCreatedAt: string | null;
};

export function SessionArtifactsPanel({ artifacts }: SessionArtifactsPanelProps): React.JSX.Element {
  const videoArtifacts = artifacts.filter((artifact) => artifact.kind === "video");
  const transcriptArtifacts = artifacts.filter((artifact) => artifact.kind === "transcript");
  const templateArtifacts = artifacts.filter((artifact) => artifact.kind === "template");

  const pairedArtifacts = React.useMemo(() => {
    const pairMap = new Map<string, ArtifactPair>();

    function ensurePair(artifact: InputArtifact, kind: "video" | "transcript") {
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
              <h3 className="summary-document-title">PDD Template Used</h3>
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
