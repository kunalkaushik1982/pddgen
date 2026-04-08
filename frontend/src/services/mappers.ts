import type { User } from "../types/auth";
import type { AdminUserSummary } from "../types/admin";
import type { Meeting } from "../types/meeting";
import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramLayoutNodePosition,
  DiagramModel,
} from "../types/diagram";
import type { CandidateScreenshot, ProcessNote, ProcessStep, StepScreenshot } from "../types/process";
import type { ActionLogEntry, DraftSession, DraftSessionListItem, InputArtifact, OutputDocument, PendingEvidenceBundle, ProcessGroup, SessionAnswer } from "../types/session";
import type {
  BackendActionLog,
  BackendAdminUserSummary,
  BackendArtifact,
  BackendCandidateScreenshot,
  BackendDiagramLayoutResponse,
  BackendDiagramModel,
  BackendDraftSession,
  BackendDraftSessionListItem,
  BackendMeeting,
  BackendOutputDocument,
  BackendPendingEvidenceBundle,
  BackendProcessGroup,
  BackendProcessNote,
  BackendProcessStep,
  BackendSessionAnswer,
  BackendStepScreenshot,
  BackendUser,
} from "./contracts";

export function mapArtifact(artifact: BackendArtifact): InputArtifact {
  return {
    id: artifact.id,
    meetingId: artifact.meeting_id ?? null,
    uploadBatchId: artifact.upload_batch_id ?? null,
    uploadPairIndex: artifact.upload_pair_index ?? null,
    name: artifact.name,
    kind: artifact.kind,
    storagePath: artifact.storage_path,
    contentType: artifact.content_type ?? null,
    previewUrl: artifact.preview_url ?? null,
    previewExpiresAt: artifact.preview_expires_at ?? null,
    sizeBytes: artifact.size_bytes ?? 0,
    createdAt: artifact.created_at ?? null,
  };
}

export function mapOutputDocument(output: BackendOutputDocument): OutputDocument {
  return {
    id: output.id,
    kind: output.kind === "pdf" ? "pdf" : "docx",
    storagePath: output.storage_path,
    exportedAt: output.exported_at,
  };
}

export function mapStepScreenshot(stepScreenshot: BackendStepScreenshot): StepScreenshot {
  return {
    id: stepScreenshot.id,
    artifactId: stepScreenshot.artifact_id,
    role: stepScreenshot.role,
    sequenceNumber: stepScreenshot.sequence_number,
    timestamp: stepScreenshot.timestamp,
    selectionMethod: stepScreenshot.selection_method,
    isPrimary: stepScreenshot.is_primary,
    artifact: {
      id: stepScreenshot.artifact.id,
      name: stepScreenshot.artifact.name,
      kind: "screenshot",
      storagePath: stepScreenshot.artifact.storage_path,
      previewUrl: stepScreenshot.artifact.preview_url ?? null,
      previewExpiresAt: stepScreenshot.artifact.preview_expires_at ?? null,
    },
  };
}

export function mapCandidateScreenshot(candidateScreenshot: BackendCandidateScreenshot): CandidateScreenshot {
  return {
    id: candidateScreenshot.id,
    artifactId: candidateScreenshot.artifact_id,
    sequenceNumber: candidateScreenshot.sequence_number,
    timestamp: candidateScreenshot.timestamp,
    sourceRole: candidateScreenshot.source_role,
    selectionMethod: candidateScreenshot.selection_method,
    isSelected: candidateScreenshot.is_selected,
    artifact: {
      id: candidateScreenshot.artifact.id,
      name: candidateScreenshot.artifact.name,
      kind: "screenshot",
      storagePath: candidateScreenshot.artifact.storage_path,
      previewUrl: candidateScreenshot.artifact.preview_url ?? null,
      previewExpiresAt: candidateScreenshot.artifact.preview_expires_at ?? null,
    },
  };
}

export function mapProcessStep(step: BackendProcessStep): ProcessStep {
  return {
    id: step.id,
    processGroupId: step.process_group_id ?? null,
    meetingId: step.meeting_id ?? null,
    stepNumber: step.step_number,
    applicationName: step.application_name,
    actionText: step.action_text,
    sourceDataNote: step.source_data_note,
    timestamp: step.timestamp,
    startTimestamp: step.start_timestamp,
    endTimestamp: step.end_timestamp,
    supportingTranscriptText: step.supporting_transcript_text,
    screenshotId: step.screenshot_id,
    confidence: step.confidence,
    evidenceReferences: step.evidence_references.map((reference) => ({
      id: reference.id,
      artifactId: reference.artifact_id,
      kind: reference.kind as ProcessStep["evidenceReferences"][number]["kind"],
      locator: reference.locator,
    })),
    screenshots: step.screenshots.map(mapStepScreenshot),
    candidateScreenshots: step.candidate_screenshots.map(mapCandidateScreenshot),
    editedByBa: step.edited_by_ba,
  };
}

export function mapProcessNote(note: BackendProcessNote): ProcessNote {
  return {
    id: note.id,
    processGroupId: note.process_group_id ?? null,
    meetingId: note.meeting_id ?? null,
    text: note.text,
    relatedStepIds: note.related_step_ids,
    evidenceReferenceIds: note.evidence_reference_ids,
    confidence: note.confidence,
    inferenceType: note.inference_type,
  };
}

export function mapMeeting(meeting: BackendMeeting): Meeting {
  return {
    id: meeting.id,
    sessionId: meeting.session_id,
    title: meeting.title,
    meetingDate: meeting.meeting_date,
    uploadedAt: meeting.uploaded_at,
    orderIndex: meeting.order_index,
  };
}

export function mapActionLog(actionLog: BackendActionLog): ActionLogEntry {
  return {
    id: actionLog.id,
    eventType: actionLog.event_type,
    title: actionLog.title,
    detail: actionLog.detail,
    metadata: actionLog.metadata ?? {},
    actor: actionLog.actor,
    createdAt: actionLog.created_at,
  };
}

export function mapPendingEvidenceBundle(bundle: BackendPendingEvidenceBundle): PendingEvidenceBundle {
  return {
    id: bundle.id,
    meetingId: bundle.meeting_id,
    meetingTitle: bundle.meeting_title,
    uploadedAt: bundle.uploaded_at,
    pairIndex: bundle.pair_index,
    transcriptArtifactId: bundle.transcript_artifact_id ?? null,
    transcriptName: bundle.transcript_name ?? null,
    videoArtifactId: bundle.video_artifact_id ?? null,
    videoName: bundle.video_name ?? null,
  };
}

export function mapProcessGroup(processGroup: BackendProcessGroup): ProcessGroup {
  return {
    id: processGroup.id,
    sessionId: processGroup.session_id,
    title: processGroup.title,
    canonicalSlug: processGroup.canonical_slug,
    status: processGroup.status,
    displayOrder: processGroup.display_order,
    summaryText: processGroup.summary_text,
    capabilityTags: processGroup.capability_tags ?? [],
    overviewDiagramJson: processGroup.overview_diagram_json,
    detailedDiagramJson: processGroup.detailed_diagram_json,
  };
}

export function mapDraftSession(session: BackendDraftSession): DraftSession {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    diagramType: session.diagram_type,
    documentType: session.document_type,
    draftGenerationStartedAt: session.draft_generation_started_at ?? null,
    draftGenerationCompletedAt: session.draft_generation_completed_at ?? null,
    screenshotGenerationStartedAt: session.screenshot_generation_started_at ?? null,
    screenshotGenerationCompletedAt: session.screenshot_generation_completed_at ?? null,
    draftGenerationDurationSeconds: session.draft_generation_duration_seconds ?? null,
    screenshotGenerationDurationSeconds: session.screenshot_generation_duration_seconds ?? null,
    hasUnprocessedEvidence: session.has_unprocessed_evidence,
    pendingEvidenceBundles: session.pending_evidence_bundles.map(mapPendingEvidenceBundle),
    processGroups: session.process_groups.map(mapProcessGroup),
    inputArtifacts: session.artifacts.map(mapArtifact),
    processSteps: session.process_steps.map(mapProcessStep),
    processNotes: session.process_notes.map(mapProcessNote),
    outputDocuments: session.output_documents.map(mapOutputDocument),
    actionLogs: session.action_logs.map(mapActionLog),
  };
}

export function mapDraftSessionListItem(session: BackendDraftSessionListItem): DraftSessionListItem {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    diagramType: session.diagram_type,
    documentType: session.document_type,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
    draftGenerationStartedAt: session.draft_generation_started_at ?? null,
    draftGenerationCompletedAt: session.draft_generation_completed_at ?? null,
    screenshotGenerationStartedAt: session.screenshot_generation_started_at ?? null,
    screenshotGenerationCompletedAt: session.screenshot_generation_completed_at ?? null,
    draftGenerationDurationSeconds: session.draft_generation_duration_seconds ?? null,
    screenshotGenerationDurationSeconds: session.screenshot_generation_duration_seconds ?? null,
    latestStageTitle: session.latest_stage_title,
    latestStageDetail: session.latest_stage_detail,
    failureDetail: session.failure_detail,
    resumeReady: session.resume_ready,
    canRetry: session.can_retry,
  };
}

export function mapSessionAnswer(answer: BackendSessionAnswer): SessionAnswer {
  return {
    answer: answer.answer,
    confidence: answer.confidence,
    citations: answer.citations.map((citation) => ({
      id: citation.id,
      sourceType: citation.source_type,
      title: citation.title,
      snippet: citation.snippet,
    })),
  };
}

export function mapDiagramModel(diagram: BackendDiagramModel): DiagramModel {
  return {
    diagramType: diagram.diagram_type,
    viewType: diagram.view_type,
    title: diagram.title,
    nodes: diagram.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      category: node.category,
      stepRange: node.step_range,
      width: node.width,
      height: node.height,
    })),
    edges: diagram.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      sourceHandle: edge.source_handle,
      targetHandle: edge.target_handle,
    })),
  };
}

export function mapDiagramLayout(layout: BackendDiagramLayoutResponse): {
  nodes: DiagramLayoutNodePosition[];
  exportPreset: DiagramExportPreset;
  canvasSettings: DiagramCanvasSettings;
} {
  return {
    nodes: layout.nodes,
    exportPreset: layout.export_preset,
    canvasSettings: {
      theme: layout.canvas_settings?.theme ?? "dark",
      showGrid: layout.canvas_settings?.show_grid ?? true,
      gridDensity: layout.canvas_settings?.grid_density ?? "medium",
    },
  };
}

export function mapUser(user: BackendUser): User {
  return {
    id: user.id,
    username: user.username,
    email: user.email ?? null,
    emailVerified: user.email_verified ?? false,
    createdAt: user.created_at,
    isAdmin: user.is_admin,
  };
}

export function mapAdminUserSummary(user: BackendAdminUserSummary): AdminUserSummary {
  return {
    id: user.id,
    username: user.username,
    createdAt: user.created_at,
    isAdmin: user.is_admin,
    totalJobs: user.total_jobs,
    activeJobs: user.active_jobs,
  };
}
