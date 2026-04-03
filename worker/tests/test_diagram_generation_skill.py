from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "diagram_generation"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "diagram_generation"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "registry.py"
OUTPUT_STAGES_PATH = Path(__file__).resolve().parents[1] / "services" / "draft_generation" / "output_stages.py"
INPUT_STAGES_PATH = Path(__file__).resolve().parents[1] / "services" / "draft_generation" / "input_stages.py"
WORKER_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = WORKER_DIR / "services"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_schemas_module():
    return load_module("diagram_generation_schemas_test", SCHEMAS_PATH)


def load_skill_module():
    return load_module("diagram_generation_skill_test", SKILL_PATH)


def load_client_module():
    return load_module("ai_skill_client_diagram_test", CLIENT_PATH)


def load_runtime_module():
    return load_module("ai_skill_runtime_diagram_test", RUNTIME_PATH)


def load_registry_module():
    return load_module("ai_skill_registry_diagram_test", REGISTRY_PATH)


def load_stage_module(path: Path):
    for module_name in (
        "worker",
        "worker.bootstrap",
        "worker.services",
        "worker.services.draft_generation.input_stages",
        "worker.services.draft_generation.process_stages",
        "worker.services.draft_generation.output_stages",
        "worker.services.draft_generation.stage_context",
    ):
        sys.modules.pop(module_name, None)

    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    observability_module = types.ModuleType("app.core.observability")

    class FakeLogger:
        def info(self, *args, **kwargs):
            return None

    @contextmanager
    def bind_log_context(**kwargs):
        yield

    observability_module.bind_log_context = bind_log_context
    observability_module.get_logger = lambda name: FakeLogger()

    sqlalchemy_module = types.ModuleType("sqlalchemy")
    sqlalchemy_module.delete = lambda *args, **kwargs: None
    sqlalchemy_module.select = lambda *args, **kwargs: None

    action_log_model_module = types.ModuleType("app.models.action_log")
    action_log_model_module.ActionLogModel = type("ActionLogModel", (), {})
    artifact_module = types.ModuleType("app.models.artifact")
    artifact_module.ArtifactModel = type("ArtifactModel", (), {})
    bundle_module = types.ModuleType("app.models.meeting_evidence_bundle")
    bundle_module.MeetingEvidenceBundleModel = type("MeetingEvidenceBundleModel", (), {})
    note_module = types.ModuleType("app.models.process_note")
    note_module.ProcessNoteModel = type("ProcessNoteModel", (), {})
    group_module = types.ModuleType("app.models.process_group")
    group_module.ProcessGroupModel = type("ProcessGroupModel", (), {})
    step_module = types.ModuleType("app.models.process_step")
    step_module.ProcessStepModel = type("ProcessStepModel", (), {})
    screenshot_module = types.ModuleType("app.models.process_step_screenshot")
    screenshot_module.ProcessStepScreenshotModel = type("ProcessStepScreenshotModel", (), {})
    screenshot_candidate_module = types.ModuleType("app.models.process_step_screenshot_candidate")
    screenshot_candidate_module.ProcessStepScreenshotCandidateModel = type("ProcessStepScreenshotCandidateModel", (), {})

    action_log_service_module = types.ModuleType("app.services.action_log_service")

    class ActionLogService:
        def record(self, *args, **kwargs):
            return None

    action_log_service_module.ActionLogService = ActionLogService
    step_extraction_module = types.ModuleType("app.services.step_extraction")
    step_extraction_module.StepExtractionService = type("StepExtractionService", (), {})
    transcript_intelligence_module = types.ModuleType("app.services.transcript_intelligence")
    transcript_intelligence_module.TranscriptIntelligenceService = type("TranscriptIntelligenceService", (), {})

    worker_module = types.ModuleType("worker")
    worker_module.__path__ = [str(WORKER_DIR)]  # type: ignore[attr-defined]
    worker_services_module = types.ModuleType("worker.services")
    worker_services_module.__path__ = [str(SERVICES_DIR)]  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("worker.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    diagram_pkg = types.ModuleType("worker.services.ai_skills.diagram_generation")
    diagram_pkg.__path__ = []  # type: ignore[attr-defined]

    bootstrap_module = types.ModuleType("worker.bootstrap")
    bootstrap_module.get_backend_settings = lambda: None
    canonical_merge_module = types.ModuleType("worker.services.workflow_intelligence.canonical_merge")
    canonical_merge_module.CanonicalProcessMergeService = type("CanonicalProcessMergeService", (), {})

    ai_transcript_module = types.ModuleType("worker.services.ai_transcript_interpreter")

    class AITranscriptInterpreter:
        pass

    ai_transcript_module.AITranscriptInterpreter = AITranscriptInterpreter

    draft_context_module = types.ModuleType("worker.services.draft_generation.stage_context")

    @dataclass(slots=True)
    class DraftGenerationContext:
        session_id: str
        session: object
        document_type: str = "pdd"
        all_steps: list[dict] = field(default_factory=list)
        all_notes: list[dict] = field(default_factory=list)
        overview_diagram_json: str = ""
        detailed_diagram_json: str = ""

    draft_context_module.DraftGenerationContext = DraftGenerationContext

    evidence_module = types.ModuleType("worker.services.workflow_intelligence.segmentation_service")
    evidence_module.AISemanticEnrichmentStrategy = type("AISemanticEnrichmentStrategy", (), {})
    evidence_module.AIWorkflowBoundaryStrategy = type("AIWorkflowBoundaryStrategy", (), {})
    evidence_module.EvidenceSegmentationService = type("EvidenceSegmentationService", (), {})
    evidence_module.HeuristicSemanticEnrichmentStrategy = type("HeuristicSemanticEnrichmentStrategy", (), {})
    evidence_module.ParagraphTranscriptSegmentationStrategy = type("ParagraphTranscriptSegmentationStrategy", (), {})

    support_module = types.ModuleType("worker.services.draft_generation.support")
    support_module.ACTION_OFFSET_WINDOWS = {}
    support_module.SCREENSHOT_ROLE_LOCAL_OFFSETS = {}
    support_module.SCREENSHOT_ROLE_ORDER = []
    support_module.build_pairing_detail = lambda *args, **kwargs: ""
    support_module.classify_action_type = lambda *args, **kwargs: "review"
    support_module.extract_transcript_timestamps = lambda *args, **kwargs: []
    support_module.seconds_to_timestamp = lambda *args, **kwargs: "00:00:00"
    support_module.timestamp_to_seconds = lambda *args, **kwargs: 0

    process_grouping_module = types.ModuleType("worker.services.workflow_intelligence.grouping_service")
    process_grouping_module.ProcessGroupingService = type("ProcessGroupingService", (), {})
    normalizer_module = types.ModuleType("worker.services.media.transcript_normalizer")
    normalizer_module.TranscriptNormalizer = type("TranscriptNormalizer", (), {})
    video_module = types.ModuleType("worker.services.media.video_frame_extractor")
    video_module.ExtractedFrameCandidate = type("ExtractedFrameCandidate", (), {})
    video_module.VideoFrameExtractor = type("VideoFrameExtractor", (), {})
    workflow_registry_module = types.ModuleType("worker.services.workflow_intelligence.strategy_registry")
    workflow_registry_module.WorkflowIntelligenceStrategyRegistry = type("WorkflowIntelligenceStrategyRegistry", (), {})

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["sqlalchemy"] = sqlalchemy_module
    sys.modules["app.models.action_log"] = action_log_model_module
    sys.modules["app.models.artifact"] = artifact_module
    sys.modules["app.models.meeting_evidence_bundle"] = bundle_module
    sys.modules["app.models.process_note"] = note_module
    sys.modules["app.models.process_group"] = group_module
    sys.modules["app.models.process_step"] = step_module
    sys.modules["app.models.process_step_screenshot"] = screenshot_module
    sys.modules["app.models.process_step_screenshot_candidate"] = screenshot_candidate_module
    sys.modules["app.services.action_log_service"] = action_log_service_module
    sys.modules["app.services.step_extraction"] = step_extraction_module
    sys.modules["app.services.transcript_intelligence"] = transcript_intelligence_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.services"] = worker_services_module
    sys.modules["worker.services.ai_skills"] = ai_skills_module
    sys.modules["worker.services.ai_skills.diagram_generation"] = diagram_pkg
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["worker.services.workflow_intelligence.canonical_merge"] = canonical_merge_module
    sys.modules["worker.services.ai_transcript_interpreter"] = ai_transcript_module
    sys.modules["worker.services.draft_generation.stage_context"] = draft_context_module
    sys.modules["worker.services.workflow_intelligence.segmentation_service"] = evidence_module
    sys.modules["worker.services.draft_generation.support"] = support_module
    sys.modules["worker.services.workflow_intelligence.grouping_service"] = process_grouping_module
    sys.modules["worker.services.media.transcript_normalizer"] = normalizer_module
    sys.modules["worker.services.media.video_frame_extractor"] = video_module
    sys.modules["worker.services.workflow_intelligence.strategy_registry"] = workflow_registry_module
    sys.modules["worker.services.ai_skills.client"] = load_client_module()
    sys.modules["worker.services.ai_skills.runtime"] = load_runtime_module()
    sys.modules["worker.services.ai_skills.diagram_generation.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.diagram_generation.skill"] = load_skill_module()
    sys.modules["worker.services.ai_skills.registry"] = load_registry_module()

    return load_module(f"draft_stage_{path.stem}_test", path)


class DiagramGenerationTests(unittest.TestCase):
    def test_diagram_request_keeps_session_inputs(self) -> None:
        schemas = load_schemas_module()
        request = schemas.DiagramGenerationRequest(
            session_title="Vendor Workflow",
            diagram_type="flowchart",
            steps=[{"step_number": 1, "action_text": "Create vendor"}],
            notes=[{"text": "Uses SAP"}],
        )
        self.assertEqual(request.session_title, "Vendor Workflow")
        self.assertEqual(request.diagram_type, "flowchart")

    def test_diagram_response_keeps_overview_and_detailed_views(self) -> None:
        schemas = load_schemas_module()
        response = schemas.DiagramGenerationResponse(
            overview={"title": "Overview", "nodes": [], "edges": []},
            detailed={"title": "Detailed", "nodes": [], "edges": []},
        )
        self.assertEqual(response.overview["title"], "Overview")
        self.assertEqual(response.detailed["title"], "Detailed")

    def test_build_messages_includes_diagram_context(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.DiagramGenerationRequest(
            session_title="Vendor Workflow",
            diagram_type="flowchart",
            steps=[{"step_number": 1, "action_text": "Create vendor"}],
            notes=[],
        )
        messages = skill_module.DiagramGenerationSkill(client=object()).build_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("flowchart graph models", messages[0]["content"])
        self.assertIn("Vendor Workflow", messages[1]["content"])

    def test_normalize_diagram_view_returns_empty_graph_shape(self) -> None:
        skill_module = load_skill_module()
        view = skill_module.normalize_diagram_view({}, "overview", "Vendor Workflow")
        self.assertEqual(view["title"], "Vendor Workflow")
        self.assertEqual(len(view["nodes"]), 1)
        self.assertEqual(view["edges"], [])

    def test_diagram_stage_uses_skill_and_serializes_output(self) -> None:
        stage_module = load_stage_module(OUTPUT_STAGES_PATH)

        class StubDiagramSkill:
            skill_id = "diagram_generation"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.DiagramGenerationResponse(
                    overview={"title": "Overview", "nodes": [], "edges": []},
                    detailed={"title": "Detailed", "nodes": [], "edges": []},
                )

        stage = stage_module.DiagramAssemblyStage()
        stage._diagram_generation_skill = StubDiagramSkill()
        context = stage_module.DraftGenerationContext(
            session_id="session-1",
            session=type("Session", (), {"title": "Vendor Workflow", "diagram_type": "flowchart"})(),
            all_steps=[],
            all_notes=[],
        )

        class FakeDb:
            def commit(self):
                return None

        stage.run(FakeDb(), context)
        self.assertEqual(context.overview_diagram_json, json.dumps({"title": "Overview", "nodes": [], "edges": []}))
        self.assertEqual(context.detailed_diagram_json, json.dumps({"title": "Detailed", "nodes": [], "edges": []}))

    def test_default_registry_creates_diagram_generation_skill(self) -> None:
        registry_module = load_registry_module()
        registry = registry_module.build_default_ai_skill_registry()
        self.assertEqual(registry.create("diagram_generation").skill_id, "diagram_generation")

    def test_segmentation_metadata_builder_counts_summary_fields(self) -> None:
        stage_module = load_stage_module(INPUT_STAGES_PATH)

        class FakeSegmentationService:
            segmenter = type("Segmenter", (), {"strategy_key": "paragraph_v1"})()
            enricher = type("Enricher", (), {"strategy_key": "ai_plus_heuristic_v1"})()
            boundary_detector = type("Boundary", (), {"strategy_key": "ai_plus_heuristic_v1"})()

        stage = stage_module.EvidenceSegmentationStage(segmentation_service=FakeSegmentationService())
        enrichment = type(
            "Enrichment",
            (),
            {
                "actor": "User",
                "actor_role": "operator",
                "system_name": "SAP",
                "action_verb": "create",
                "action_type": "create",
                "business_object": "Purchase Order",
                "workflow_goal": "Purchase Order Creation",
                "rule_hints": ["Validate vendor"],
                "enrichment_source": "ai",
                "confidence": "high",
            },
        )()
        segment = type(
            "Segment",
            (),
            {
                "id": "seg-1",
                "transcript_artifact_id": "artifact-1",
                "segment_order": 1,
                "start_timestamp": "00:00:01",
                "end_timestamp": "00:00:02",
                "segmentation_method": "paragraph_v1",
                "confidence": "high",
                "enrichment": enrichment,
            },
        )()
        decision = type(
            "Decision",
            (),
            {
                "decision": "same_workflow",
                "confidence": "high",
                "decision_source": "ai",
                "conflict_detected": False,
            },
        )()
        context = type(
            "Context",
            (),
            {
                "document_type": "pdd",
                "transcript_artifacts": [type("Artifact", (), {"id": "artifact-1", "name": "Transcript 1"})()],
                "evidence_segments": [segment],
                "workflow_boundary_decisions": [decision],
            },
        )()

        metadata = stage._build_segmentation_metadata(context)

        self.assertEqual(metadata["transcript_summaries"][0]["top_actors"], ["User"])
        self.assertEqual(metadata["transcript_summaries"][0]["top_rules"], ["Validate vendor"])

    def test_sort_artifacts_orders_by_meeting_and_created_timestamps(self) -> None:
        stage_module = load_stage_module(OUTPUT_STAGES_PATH)
        meeting_late = type(
            "Meeting",
            (),
            {
                "order_index": 2,
                "meeting_date": datetime(2026, 4, 2, 10, 0, 0),
                "uploaded_at": datetime(2026, 4, 2, 10, 5, 0),
            },
        )()
        meeting_early = type(
            "Meeting",
            (),
            {
                "order_index": 1,
                "meeting_date": datetime(2026, 4, 2, 9, 0, 0),
                "uploaded_at": datetime(2026, 4, 2, 9, 5, 0),
            },
        )()
        artifact_late = type(
            "Artifact",
            (),
            {
                "id": "artifact-2",
                "meeting": meeting_late,
                "created_at": datetime(2026, 4, 2, 10, 6, 0),
            },
        )()
        artifact_early = type(
            "Artifact",
            (),
            {
                "id": "artifact-1",
                "meeting": meeting_early,
                "created_at": datetime(2026, 4, 2, 9, 6, 0),
            },
        )()

        sorted_artifacts = stage_module.ScreenshotDerivationStage._sort_artifacts([artifact_late, artifact_early])

        self.assertEqual([artifact.id for artifact in sorted_artifacts], ["artifact-1", "artifact-2"])


if __name__ == "__main__":
    unittest.main()
