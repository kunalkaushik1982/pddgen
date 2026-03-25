import React from "react";

import type { ActionLogEntry } from "../../types/session";

export function SessionActionLogPanel({ entries }: { entries: ActionLogEntry[] }): React.JSX.Element {
  const [copyState, setCopyState] = React.useState<"idle" | "copied" | "failed">("idle");

  async function handleCopyActionLog(): Promise<void> {
    const formattedLog = buildActionLogClipboardText(entries);
    try {
      await navigator.clipboard.writeText(formattedLog);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1600);
    } catch {
      setCopyState("failed");
      window.setTimeout(() => setCopyState("idle"), 2200);
    }
  }

  return (
    <section className="review-subsection panel stack" role="tabpanel" aria-label="Action log">
      <div>
        <h3>Action Log</h3>
        <div className="artifact-meta">Meaningful session events that affect the final PDD output.</div>
      </div>

      {entries.length > 0 ? (
        <div className="summary-document">
          <div className="summary-document-label">Session activity</div>
          <div className="summary-document-card action-log-document-card">
            <div className="action-log-card-header">
              <div className="summary-document-title">Review and export activity</div>
              <button
                type="button"
                className="action-log-copy-button"
                onClick={() => void handleCopyActionLog()}
                aria-label="Copy action log"
                title={copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy action log"}
              >
                <CopyIcon />
              </button>
            </div>
            {copyState === "copied" ? <div className="artifact-meta">Action Log copied.</div> : null}
            {copyState === "failed" ? <div className="artifact-meta">Copy failed.</div> : null}
            <ul className="action-log-document-list">
              {entries.map((entry) => (
                <li key={entry.id} className="action-log-document-item">
                  <div className="action-log-document-title">{entry.title}</div>
                  <div className="action-log-document-detail">{entry.detail}</div>
                  <WorkflowIntelligenceMetadata entry={entry} />
                  <div className="artifact-meta">
                    {entry.actor} | {new Date(entry.createdAt).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-state">No session activity is available yet.</div>
      )}
    </section>
  );
}

function WorkflowIntelligenceMetadata({ entry }: { entry: ActionLogEntry }): React.JSX.Element | null {
  const metadata = entry.metadata;
  if (!metadata || Object.keys(metadata).length === 0) {
    return null;
  }

  const conclusion = typeof metadata.conclusion === "string" ? metadata.conclusion : "";
  const strategyKeys = getRecord(metadata.strategy_keys);
  const counts = getRecord(metadata.counts);
  const segmentMethods = getRecord(metadata.segment_methods);
  const enrichmentConfidence = getRecord(metadata.enrichment_confidence);
  const boundaryDecisions = getRecord(metadata.boundary_decisions);
  const boundaryConfidence = getRecord(metadata.boundary_confidence);
  const decisionSources = getRecord(metadata.decision_sources);
  const ambiguitySummary = getRecord(metadata.ambiguity_summary);
  const transcriptAssignments = getRecord(metadata.transcript_assignments);
  const transcriptSummaries = Array.isArray(metadata.transcript_summaries) ? metadata.transcript_summaries.slice(0, 5) : [];
  const assignments = Array.isArray(metadata.assignments) ? metadata.assignments.slice(0, 8) : [];
  const sampleSegments = Array.isArray(metadata.sample_segments) ? metadata.sample_segments.slice(0, 3) : [];
  const hasContent =
    Boolean(conclusion) ||
    Object.keys(strategyKeys).length > 0 ||
    Object.keys(counts).length > 0 ||
    Object.keys(segmentMethods).length > 0 ||
    Object.keys(enrichmentConfidence).length > 0 ||
    Object.keys(boundaryDecisions).length > 0 ||
    Object.keys(boundaryConfidence).length > 0 ||
    Object.keys(decisionSources).length > 0 ||
    Object.keys(ambiguitySummary).length > 0 ||
    transcriptSummaries.length > 0 ||
    assignments.length > 0 ||
    Object.keys(transcriptAssignments).length > 0 ||
    sampleSegments.length > 0;

  if (!hasContent) {
    return null;
  }

  const decisionRows = buildDecisionRows(entry.title, metadata);

  return (
    <div className="action-log-metadata">
      {decisionRows.length > 0 ? (
        <div className="action-log-metadata-section">
          <div className="action-log-metadata-label">Decision trail</div>
          <div className="action-log-table-wrap">
            <table className="action-log-decision-table">
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {decisionRows.map((row, index) => (
                  <tr key={`${row.stage}:${index}`}>
                    <td>{row.stage}</td>
                    <td>{row.decision}</td>
                    <td>{row.confidence}</td>
                    <td>{row.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      <details className="action-log-details-toggle">
        <summary>Show technical reasoning</summary>
        <div className="action-log-details-body">
          {conclusion ? <div className="action-log-conclusion">{conclusion}</div> : null}
          {renderMetadataSection("Document type", metadata.document_type)}
          {renderKeyValueSection("Strategies", strategyKeys)}
          {renderKeyValueSection("Counts", counts)}
          {renderKeyValueSection("Segment methods", segmentMethods)}
          {renderKeyValueSection("Enrichment confidence", enrichmentConfidence)}
          {renderKeyValueSection("Boundary decisions", boundaryDecisions)}
          {renderKeyValueSection("Boundary confidence", boundaryConfidence)}
          {renderKeyValueSection("Decision sources", decisionSources)}
          {renderKeyValueSection("Ambiguity summary", ambiguitySummary)}
          {assignments.length > 0 ? (
            <div className="action-log-metadata-section">
              <div className="action-log-metadata-label">Grouping decisions</div>
              <ul className="action-log-insight-list">
                {assignments.map((assignment, index) => {
                  const record = getRecord(assignment);
                  const goals = getStringArray(record.top_goals);
                  const objects = getStringArray(record.top_objects);
                  const systems = getStringArray(record.top_systems);
                  const actors = getStringArray(record.top_actors);
                  const rules = getStringArray(record.top_rules);
                  const supportingSignals = getStringArray(record.supporting_signals);
                  const candidateMatches = Array.isArray(record.candidate_matches) ? record.candidate_matches.slice(0, 3) : [];
                  const isAmbiguous = Boolean(record.is_ambiguous);
                  const decisionValue = String(record.decision ?? "unknown");
                  const decisionSource = String(record.decision_source ?? inferDecisionSource(decisionValue, isAmbiguous));
                  const resolutionLabel = getResolutionLabel(decisionValue, isAmbiguous);
                  return (
                    <li key={`${String(record.transcript_name ?? index)}:${String(record.assigned_group_title ?? index)}`} className="action-log-insight-item">
                      <div className="action-log-insight-title">
                        {String(record.transcript_name ?? "Transcript")} {"->"} {String(record.assigned_group_title ?? "Workflow")}
                      </div>
                      <div className="action-log-document-detail">
                        Inferred workflow: {String(record.inferred_workflow ?? "Unknown")} | Decision: {formatMetadataKey(decisionValue)} | Confidence: {String(record.decision_confidence ?? "unknown")}
                      </div>
                      <div className="action-log-document-detail">Decision source: {formatDecisionSource(decisionSource)}</div>
                      <div className="action-log-document-detail">{String(record.rationale ?? "")}</div>
                      <div className="action-log-chip-row">
                        <span className="action-log-chip">{resolutionLabel}</span>
                        {isAmbiguous ? <span className="action-log-chip">Ambiguous</span> : null}
                        {goals.map((value) => (
                          <span key={`goal:${value}`} className="action-log-chip">Goal: {value}</span>
                        ))}
                        {objects.map((value) => (
                          <span key={`object:${value}`} className="action-log-chip">Object: {value}</span>
                        ))}
                        {systems.map((value) => (
                          <span key={`system:${value}`} className="action-log-chip">System: {value}</span>
                        ))}
                        {actors.map((value) => (
                          <span key={`actor:${value}`} className="action-log-chip">Actor: {value}</span>
                        ))}
                        {rules.map((value) => (
                          <span key={`rule:${value}`} className="action-log-chip">Rule: {value}</span>
                        ))}
                        {supportingSignals.map((value) => (
                          <span key={`signal:${value}`} className="action-log-chip">Signal: {formatMetadataKey(value)}</span>
                        ))}
                      </div>
                      {candidateMatches.length > 0 ? (
                        <div className="action-log-document-detail">
                          Candidate matches:{" "}
                          {candidateMatches
                            .map((item) => {
                              const candidate = getRecord(item);
                              return `${String(candidate.group_title ?? "Workflow")} (${String(candidate.score ?? "0")})`;
                            })
                            .join(", ")}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          {transcriptSummaries.length > 0 ? (
            <div className="action-log-metadata-section">
              <div className="action-log-metadata-label">Transcript summaries</div>
              <ul className="action-log-insight-list">
                {transcriptSummaries.map((summary, index) => {
                  const record = getRecord(summary);
                  return (
                    <li key={`${String(record.transcript_name ?? index)}:${index}`} className="action-log-insight-item">
                      <div className="action-log-insight-title">{String(record.transcript_name ?? "Transcript")}</div>
                      <div className="action-log-chip-row">
                        {getStringArray(record.top_goals).map((value) => (
                          <span key={`goal:${value}`} className="action-log-chip">Goal: {value}</span>
                        ))}
                        {getStringArray(record.top_actors).map((value) => (
                          <span key={`actor:${value}`} className="action-log-chip">Actor: {value}</span>
                        ))}
                        {getStringArray(record.top_objects).map((value) => (
                          <span key={`object:${value}`} className="action-log-chip">Object: {value}</span>
                        ))}
                        {getStringArray(record.top_systems).map((value) => (
                          <span key={`system:${value}`} className="action-log-chip">System: {value}</span>
                        ))}
                        {getStringArray(record.top_rules).map((value) => (
                          <span key={`rule:${value}`} className="action-log-chip">Rule: {value}</span>
                        ))}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          {assignments.length === 0 && transcriptSummaries.length === 0 ? renderKeyValueSection("Transcript assignments", transcriptAssignments) : null}
          {sampleSegments.length > 0 ? (
            <div className="action-log-metadata-section">
              <div className="action-log-metadata-label">Sample segments</div>
              <ul className="action-log-segment-list">
                {sampleSegments.map((segment, index) => {
                  const segmentRecord = getRecord(segment);
                  return (
                    <li key={String(segmentRecord.segment_id ?? index)} className="action-log-segment-item">
                      <strong>#{String(segmentRecord.segment_order ?? index + 1)}</strong>
                      <span>{String(segmentRecord.business_object ?? segmentRecord.action_verb ?? "Unlabeled segment")}</span>
                      <span className="artifact-meta">
                        {String(segmentRecord.start_timestamp ?? "--")} to {String(segmentRecord.end_timestamp ?? "--")}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </div>
      </details>
    </div>
  );
}

function renderMetadataSection(label: string, value: unknown): React.JSX.Element | null {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }
  return (
    <div className="action-log-metadata-section">
      <div className="action-log-metadata-label">{label}</div>
      <div className="action-log-chip-row">
        <span className="action-log-chip">{value}</span>
      </div>
    </div>
  );
}

function renderKeyValueSection(label: string, value: Record<string, unknown>): React.JSX.Element | null {
  const entries = Object.entries(value);
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="action-log-metadata-section">
      <div className="action-log-metadata-label">{label}</div>
      <div className="action-log-chip-row">
        {entries.map(([key, itemValue]) => (
          <span key={key} className="action-log-chip">
            {formatMetadataKey(key)}: {String(itemValue)}
          </span>
        ))}
      </div>
    </div>
  );
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function getStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
}

function formatMetadataKey(value: string): string {
  return value.replaceAll("_", " ");
}

function getResolutionLabel(decision: string, isAmbiguous: boolean): string {
  if (decision.startsWith("ai_resolved_")) {
    return "AI tie-break";
  }
  if (decision.startsWith("ai_")) {
    return "AI decision";
  }
  if (isAmbiguous) {
    return "Heuristic fallback";
  }
  return "Heuristic decision";
}

function inferDecisionSource(decision: string, isAmbiguous: boolean): string {
  if (decision.startsWith("ai_resolved_")) {
    return "ai_tiebreak";
  }
  if (decision.startsWith("ai_")) {
    return "ai";
  }
  if (isAmbiguous) {
    return "heuristic_fallback";
  }
  return "heuristic";
}

function formatDecisionSource(value: string): string {
  switch (value) {
    case "ai":
      return "AI";
    case "ai_tiebreak":
      return "AI tie-break";
    case "heuristic_fallback":
      return "Heuristic fallback";
    case "heuristic":
      return "Heuristic";
    default:
      return toSentenceCase(formatMetadataKey(value));
  }
}

type DecisionRow = {
  stage: string;
  decision: string;
  confidence: string;
  why: string;
};

function buildDecisionRows(entryTitle: string, metadata: Record<string, unknown>): DecisionRow[] {
  if (entryTitle === "Segmenting evidence") {
    const counts = getRecord(metadata.counts);
    const boundaryDecisions = getRecord(metadata.boundary_decisions);
    const boundaryConfidence = getRecord(metadata.boundary_confidence);
    const transcriptCount = String(counts.transcript_artifacts ?? "0");
    const segmentCount = String(counts.segments ?? "0");
    const boundaryDecisionKey = Object.keys(boundaryDecisions)[0]
      ? String(Object.keys(boundaryDecisions)[0])
      : "";
    const boundaryDecisionCount = Object.values(boundaryDecisions)[0];
    const confidenceLabel = Object.keys(boundaryConfidence)[0]
      ? toSentenceCase(formatMetadataKey(String(Object.keys(boundaryConfidence)[0])))
      : "Medium";
    return [
      {
        stage: "Uploaded transcripts",
        decision: `The system found ${segmentCount} evidence block(s) from ${transcriptCount} transcript(s)`,
        confidence: "Medium",
        why: "It first separated the uploaded transcript content into smaller blocks so it could compare the workflows more clearly.",
      },
      {
        stage: "Workflow comparison",
        decision: describeBoundaryDecision(boundaryDecisionKey, boundaryDecisionCount),
        confidence: confidenceLabel,
        why: describeBoundaryReason(boundaryDecisionKey, transcriptCount),
      },
    ];
  }

  if (entryTitle === "Grouping processes") {
    const assignments = Array.isArray(metadata.assignments) ? metadata.assignments.slice(0, 8) : [];
    return assignments.map((assignment) => {
      const record = getRecord(assignment);
      const transcriptName = String(record.transcript_name ?? "Transcript");
      const assignedWorkflow = String(record.assigned_group_title ?? "Workflow");
      const inferredWorkflow = String(record.inferred_workflow ?? assignedWorkflow);
      const decision = String(record.decision ?? "unknown");
      const confidence = toSentenceCase(String(record.decision_confidence ?? "unknown"));
      const isAmbiguous = Boolean(record.is_ambiguous);
      return {
        stage: transcriptName,
        decision: describeGroupingDecision(decision, isAmbiguous, assignedWorkflow, inferredWorkflow),
        confidence,
        why: toLaymanReason(String(record.rationale ?? "No rationale available."), inferredWorkflow, assignedWorkflow),
      };
    });
  }

  return [];
}

function describeBoundaryDecision(decisionKey: string, count: unknown): string {
  const suffix = count ? ` (${String(count)})` : "";
  if (decisionKey === "new_workflow") {
    return `The system treated the compared transcript blocks as separate workflows${suffix}`;
  }
  if (decisionKey === "same_workflow") {
    return `The system treated the compared transcript blocks as one continuing workflow${suffix}`;
  }
  if (decisionKey === "uncertain") {
    return `The system could not clearly tell whether the workflow continued or changed${suffix}`;
  }
  return `The system compared the transcript blocks to understand workflow continuity${suffix}`;
}

function describeBoundaryReason(decisionKey: string, transcriptCount: string): string {
  if (decisionKey === "new_workflow") {
    return `The compared transcript blocks looked different enough to be treated as separate workflows across the ${transcriptCount} uploaded transcript(s).`;
  }
  if (decisionKey === "same_workflow") {
    return "The compared transcript blocks looked similar enough to be treated as one continuous workflow.";
  }
  if (decisionKey === "uncertain") {
    return "The compared transcript blocks showed mixed signals, so the system could not make a fully clear workflow decision.";
  }
  return "The system compared business clues such as workflow goal, business object, and system context.";
}

function describeGroupingDecision(decision: string, isAmbiguous: boolean, assignedWorkflow: string, inferredWorkflow: string): string {
  if (decision === "ai_resolved_ambiguous_match") {
    return `AI helped confirm that this transcript belongs to the existing workflow "${assignedWorkflow}"`;
  }
  if (decision === "ai_resolved_ambiguous_new_group") {
    return `AI helped decide that this transcript should become a new workflow "${inferredWorkflow}"`;
  }
  if (isAmbiguous) {
    return `The system made a temporary workflow choice for "${assignedWorkflow}" because the match was not fully clear`;
  }
  if (decision.includes("matched_existing_group") || decision === "continued_previous_group") {
    return `The system linked this transcript to the existing workflow "${assignedWorkflow}"`;
  }
  return `The system created a separate workflow "${assignedWorkflow}" for this transcript`;
}

function toLaymanReason(reason: string, inferredWorkflow: string, assignedWorkflow: string): string {
  const normalized = reason.trim();
  if (!normalized) {
    return `The system compared this transcript with existing workflows and decided on "${assignedWorkflow}".`;
  }
  if (normalized.startsWith("No strong existing workflow match was found")) {
    return `It did not find a close enough match with any existing workflow, so it created "${assignedWorkflow}" as a separate workflow.`;
  }
  if (normalized.startsWith("Matched to existing workflow") && normalized.includes("another plausible workflow")) {
    return `It found a likely match with "${assignedWorkflow}", but another workflow also looked possible.`;
  }
  if (normalized.startsWith("Matched to existing workflow")) {
    return `It found enough similarity to place this transcript under "${assignedWorkflow}" instead of creating a separate workflow.`;
  }
  if (normalized.startsWith("No confident workflow match was found")) {
    return `It was not confident enough to place this transcript into an existing workflow, so it created "${inferredWorkflow}" separately.`;
  }
  if (normalized.startsWith("Reused the previous workflow group")) {
    return `It carried this transcript forward into "${assignedWorkflow}" because the previous transcript looked like part of the same ongoing workflow.`;
  }
  return normalized;
}

function toSentenceCase(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function buildActionLogClipboardText(entries: ActionLogEntry[]): string {
  return entries
    .map((entry) => {
      const parts = [
        entry.title,
        entry.detail,
        `${entry.actor} | ${new Date(entry.createdAt).toLocaleString()}`,
      ];
      const metadataText = buildMetadataClipboardText(entry.metadata);
      if (metadataText) {
        parts.push(metadataText);
      }
      return parts.filter(Boolean).join("\n");
    })
    .join("\n\n");
}

function buildMetadataClipboardText(metadata: Record<string, unknown>): string {
  const lines: string[] = [];
  const conclusion = typeof metadata.conclusion === "string" ? metadata.conclusion.trim() : "";
  if (conclusion) {
    lines.push(`Conclusion: ${conclusion}`);
  }

  const documentType = typeof metadata.document_type === "string" ? metadata.document_type.trim() : "";
  if (documentType) {
    lines.push(`Document type: ${documentType}`);
  }

  appendRecordLines(lines, "Counts", getRecord(metadata.counts));
  appendRecordLines(lines, "Strategies", getRecord(metadata.strategy_keys));
  appendRecordLines(lines, "Boundary decisions", getRecord(metadata.boundary_decisions));
  appendRecordLines(lines, "Decision sources", getRecord(metadata.decision_sources));
  appendRecordLines(lines, "Ambiguity summary", getRecord(metadata.ambiguity_summary));

  const assignments = Array.isArray(metadata.assignments) ? metadata.assignments.slice(0, 8) : [];
  if (assignments.length > 0) {
    lines.push("Grouping decisions:");
    for (const assignment of assignments) {
      const record = getRecord(assignment);
      const decisionSource = String(record.decision_source ?? inferDecisionSource(String(record.decision ?? "unknown"), Boolean(record.is_ambiguous)));
      lines.push(
        `- ${String(record.transcript_name ?? "Transcript")} -> ${String(record.assigned_group_title ?? "Workflow")} | ${String(record.decision ?? "unknown")} | confidence=${String(record.decision_confidence ?? "unknown")} | source=${formatDecisionSource(decisionSource)}`
      );
      const rationale = String(record.rationale ?? "").trim();
      if (rationale) {
        lines.push(`  rationale: ${rationale}`);
      }
    }
  }

  return lines.join("\n");
}

function appendRecordLines(lines: string[], label: string, record: Record<string, unknown>): void {
  const entries = Object.entries(record);
  if (entries.length === 0) {
    return;
  }
  lines.push(`${label}:`);
  for (const [key, value] of entries) {
    lines.push(`- ${formatMetadataKey(key)}: ${String(value)}`);
  }
}

function CopyIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="action-log-copy-icon">
      <rect x="9" y="7" width="11" height="11" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <rect x="4" y="4" width="11" height="11" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
