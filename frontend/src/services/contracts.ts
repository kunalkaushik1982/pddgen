import type { User } from "../types/auth";
import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramModel,
} from "../types/diagram";
import type { ProcessNote, ProcessStep } from "../types/process";
import type { DraftSession, InputArtifact, SessionAnswer } from "../types/session";
import type { AdminUserSummary } from "../types/admin";
import type { Meeting } from "../types/meeting";

export type BackendArtifact = {
  id: string;
  meeting_id?: string | null;
  upload_batch_id?: string | null;
  upload_pair_index?: number | null;
  name: string;
  kind: InputArtifact["kind"];
  storage_path: string;
  content_type?: string | null;
  size_bytes?: number;
  created_at?: string;
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
  process_group_id?: string | null;
  meeting_id?: string | null;
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
  process_group_id?: string | null;
  meeting_id?: string | null;
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

export type BackendProcessGroup = {
  id: string;
  session_id: string;
  title: string;
  canonical_slug: string;
  status: string;
  display_order: number;
  summary_text: string;
  overview_diagram_json: string;
  detailed_diagram_json: string;
};

export type BackendActionLog = {
  id: string;
  event_type: string;
  title: string;
  detail: string;
  actor: string;
  created_at: string;
};

export type BackendPendingEvidenceBundle = {
  id: string;
  meeting_id: string;
  meeting_title: string;
  uploaded_at: string;
  pair_index: number;
  transcript_artifact_id?: string | null;
  transcript_name?: string | null;
  video_artifact_id?: string | null;
  video_name?: string | null;
};

export type BackendDraftSession = {
  id: string;
  title: string;
  status: DraftSession["status"];
  owner_id: string;
  diagram_type: DraftSession["diagramType"];
  has_unprocessed_evidence: boolean;
  pending_evidence_bundles: BackendPendingEvidenceBundle[];
  process_groups: BackendProcessGroup[];
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

export type BackendMeeting = {
  id: string;
  session_id: string;
  title: string;
  meeting_date: string | null;
  uploaded_at: string;
  order_index: number | null;
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
  process_group_id?: string | null;
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
export type BackendMappedMeeting = Meeting;
