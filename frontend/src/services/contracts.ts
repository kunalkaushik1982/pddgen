import type { User } from "../types/auth";
import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramModel,
} from "../types/diagram";
import type { ProcessNote, ProcessStep } from "../types/process";
import type { DraftSession, InputArtifact, SessionAnswer } from "../types/session";
import type { AdminUserSummary } from "../types/admin";

export type BackendArtifact = {
  id: string;
  name: string;
  kind: InputArtifact["kind"];
  storage_path: string;
};

export type BackendEvidenceReference = {
  id: string;
  artifact_id: string;
  kind: string;
  locator: string;
};

export type BackendStepScreenshot = {
  id: string;
  artifact_id: string;
  role: string;
  sequence_number: number;
  timestamp: string;
  selection_method: string;
  is_primary: boolean;
  artifact: BackendArtifact;
};

export type BackendCandidateScreenshot = {
  id: string;
  artifact_id: string;
  sequence_number: number;
  timestamp: string;
  source_role: string;
  selection_method: string;
  is_selected: boolean;
  artifact: BackendArtifact;
};

export type BackendProcessStep = {
  id: string;
  step_number: number;
  application_name: string;
  action_text: string;
  source_data_note: string;
  timestamp: string;
  start_timestamp: string;
  end_timestamp: string;
  supporting_transcript_text: string;
  screenshot_id: string;
  confidence: ProcessStep["confidence"];
  evidence_references: BackendEvidenceReference[];
  screenshots: BackendStepScreenshot[];
  candidate_screenshots: BackendCandidateScreenshot[];
  edited_by_ba: boolean;
};

export type BackendProcessNote = {
  id: string;
  text: string;
  related_step_ids: string[];
  evidence_reference_ids: string[];
  confidence: ProcessNote["confidence"];
  inference_type: string;
};

export type BackendOutputDocument = {
  id: string;
  kind: string;
  storage_path: string;
  exported_at: string;
};

export type BackendActionLog = {
  id: string;
  event_type: string;
  title: string;
  detail: string;
  actor: string;
  created_at: string;
};

export type BackendDraftSession = {
  id: string;
  title: string;
  status: DraftSession["status"];
  owner_id: string;
  diagram_type: DraftSession["diagramType"];
  artifacts: BackendArtifact[];
  process_steps: BackendProcessStep[];
  process_notes: BackendProcessNote[];
  output_documents: BackendOutputDocument[];
  action_logs: BackendActionLog[];
};

export type BackendDraftSessionListItem = {
  id: string;
  title: string;
  status: DraftSession["status"];
  owner_id: string;
  diagram_type: DraftSession["diagramType"];
  created_at: string;
  updated_at: string;
  latest_stage_title: string;
  latest_stage_detail: string;
  failure_detail: string;
  resume_ready: boolean;
  can_retry: boolean;
};

export type BackendSessionAnswerCitation = {
  id: string;
  source_type: string;
  title: string;
  snippet: string;
};

export type BackendSessionAnswer = {
  answer: string;
  confidence: SessionAnswer["confidence"];
  citations: BackendSessionAnswerCitation[];
};

export type BackendUser = {
  id: string;
  username: string;
  created_at: string;
  is_admin: boolean;
};

export type BackendAdminUserSummary = {
  id: string;
  username: string;
  created_at: string;
  is_admin: boolean;
  total_jobs: number;
  active_jobs: number;
};

export type BackendAuthResponse = {
  auth_status?: string;
  challenge_type?: string | null;
  challenge_token?: string | null;
  token?: string | null;
  user?: BackendUser;
};

export type BackendDiagramNode = {
  id: string;
  label: string;
  category: DiagramModel["nodes"][number]["category"];
  step_range: string;
  width?: number;
  height?: number;
};

export type BackendDiagramEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  source_handle?: string;
  target_handle?: string;
};

export type BackendDiagramModel = {
  diagram_type: DiagramModel["diagramType"];
  view_type: DiagramModel["viewType"];
  title: string;
  nodes: BackendDiagramNode[];
  edges: BackendDiagramEdge[];
};

export type BackendDiagramLayoutResponse = {
  session_id: string;
  view_type: DiagramModel["viewType"];
  export_preset: DiagramExportPreset;
  canvas_settings: {
    theme: DiagramCanvasSettings["theme"];
    show_grid: boolean;
    grid_density: DiagramCanvasSettings["gridDensity"];
  };
  nodes: Array<{
    id: string;
    x: number;
    y: number;
    label?: string;
    width?: number;
    height?: number;
  }>;
};

export type CreateSessionPayload = {
  title: string;
  ownerId: string;
  diagramType: DraftSession["diagramType"];
};

export type StepUpdatePayload = Partial<{
  applicationName: string;
  actionText: string;
  sourceDataNote: string;
  timestamp: string;
  startTimestamp: string;
  endTimestamp: string;
  supportingTranscriptText: string;
  screenshotId: string;
  confidence: ProcessStep["confidence"];
  editedByBa: boolean;
}>;

export type BackendMappedUser = User;
export type BackendMappedAdminUserSummary = AdminUserSummary;
