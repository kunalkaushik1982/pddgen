import type { User } from "../types/auth";
import type { AdminUserSummary } from "../types/admin";
import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramLayoutNodePosition,
  DiagramModel,
} from "../types/diagram";
import type { CandidateScreenshot, ProcessNote, ProcessStep, StepScreenshot } from "../types/process";
import type { ActionLogEntry, DraftSession, DraftSessionListItem, InputArtifact, OutputDocument, SessionAnswer } from "../types/session";
import type {
  BackendActionLog,
  BackendAdminUserSummary,
  BackendArtifact,
  BackendCandidateScreenshot,
  BackendDiagramLayoutResponse,
  BackendDiagramModel,
  BackendDraftSession,
  BackendDraftSessionListItem,
  BackendOutputDocument,
  BackendProcessNote,
  BackendProcessStep,
  BackendSessionAnswer,
  BackendStepScreenshot,
  BackendUser,
} from "./contracts";

export function mapArtifact(artifact: BackendArtifact): InputArtifact {
  return {
    id: artifact.id,
    name: artifact.name,
    kind: artifact.kind,
    storagePath: artifact.storage_path,
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
    },
  };
}

export function mapProcessStep(step: BackendProcessStep): ProcessStep {
  return {
    id: step.id,
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
    text: note.text,
    relatedStepIds: note.related_step_ids,
    evidenceReferenceIds: note.evidence_reference_ids,
    confidence: note.confidence,
    inferenceType: note.inference_type,
  };
}

export function mapActionLog(actionLog: BackendActionLog): ActionLogEntry {
  return {
    id: actionLog.id,
    eventType: actionLog.event_type,
    title: actionLog.title,
    detail: actionLog.detail,
    actor: actionLog.actor,
    createdAt: actionLog.created_at,
  };
}

export function mapDraftSession(session: BackendDraftSession): DraftSession {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    diagramType: session.diagram_type,
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
    createdAt: session.created_at,
    updatedAt: session.updated_at,
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
