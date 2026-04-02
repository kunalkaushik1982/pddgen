from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

COMPOSITION_PATH = Path(__file__).resolve().parents[1] / "services" / "worker_composition.py"


def load_worker_composition_module():
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    observability_module = types.ModuleType("app.core.observability")
    observability_module.get_logger = lambda name: type("Logger", (), {"info": lambda *args, **kwargs: None})()

    action_log_module = types.ModuleType("app.models.action_log")
    action_log_module.ActionLogModel = type("ActionLogModel", (), {})

    job_dispatcher_module = types.ModuleType("app.services.job_dispatcher")
    job_dispatcher_module.JobDispatcherService = type(
        "JobDispatcherService",
        (),
        {"release_screenshot_generation_lock": lambda self, session_id: None},
    )

    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    bootstrap_module = types.ModuleType("worker.bootstrap")
    worker_module.bootstrap = bootstrap_module
    services_module = types.ModuleType("worker.services")
    services_module.__path__ = []  # type: ignore[attr-defined]

    class FakeEvidenceSegmentationStage:
        def __init__(self, *, segmentation_service=None) -> None:
            self.segmentation_service = segmentation_service

    stage_services_module = types.ModuleType("worker.services.draft_generation_stage_services")
    stage_services_module.CanonicalMergeStage = type("CanonicalMergeStage", (), {})
    stage_services_module.DiagramAssemblyStage = type("DiagramAssemblyStage", (), {})
    stage_services_module.EvidenceSegmentationStage = FakeEvidenceSegmentationStage
    stage_services_module.FailureStage = type("FailureStage", (), {"mark_failed": lambda self, db, session_id, detail=None: None})
    stage_services_module.PersistenceStage = type("PersistenceStage", (), {"run": lambda self, db, context: {}, "_persist_step_screenshots": lambda self, db, step_models, all_steps: None})
    stage_services_module.ProcessGroupingStage = type("ProcessGroupingStage", (), {})
    stage_services_module.SessionPreparationStage = type("SessionPreparationStage", (), {"load_and_prepare": lambda self, db, session: object()})
    stage_services_module.ScreenshotDerivationStage = type("ScreenshotDerivationStage", (), {})
    stage_services_module.TranscriptInterpretationStage = type("TranscriptInterpretationStage", (), {})

    screenshot_context_builder_module = types.ModuleType("worker.services.screenshot_context_builder")
    screenshot_context_builder_module.DefaultScreenshotContextBuilder = type("DefaultScreenshotContextBuilder", (), {})

    worker_repositories_module = types.ModuleType("worker.services.worker_repositories")
    worker_repositories_module.SqlAlchemyDraftSessionRepository = type("SqlAlchemyDraftSessionRepository", (), {})

    worker_uow_module = types.ModuleType("worker.services.worker_uow")
    worker_uow_module.SqlAlchemyWorkerUnitOfWork = type("SqlAlchemyWorkerUnitOfWork", (), {})

    worker_use_cases_module = types.ModuleType("worker.services.worker_use_cases")
    worker_use_cases_module.DraftGenerationUseCase = type("DraftGenerationUseCase", (), {"__init__": lambda self, **kwargs: setattr(self, "kwargs", kwargs)})
    worker_use_cases_module.ScreenshotGenerationUseCase = type("ScreenshotGenerationUseCase", (), {"__init__": lambda self, **kwargs: setattr(self, "kwargs", kwargs)})

    workflow_registry_module = types.ModuleType("worker.services.workflow_strategy_registry")

    class FakeRegistry:
        def register_segmenter(self, key, factory) -> None:
            return None

        def register_enricher(self, key, factory) -> None:
            return None

        def register_boundary_detector(self, key, factory) -> None:
            return None

        def create_strategy_set(self, **kwargs):
            return {"strategy_keys": kwargs}

    workflow_registry_module.WorkflowIntelligenceStrategyRegistry = FakeRegistry

    evidence_segmentation_module = types.ModuleType("worker.services.evidence_segmentation_service")
    evidence_segmentation_module.AISemanticEnrichmentStrategy = type("AISemanticEnrichmentStrategy", (), {"strategy_key": "ai_semantic"})
    evidence_segmentation_module.AIWorkflowBoundaryStrategy = type("AIWorkflowBoundaryStrategy", (), {"strategy_key": "ai_boundary"})
    evidence_segmentation_module.EvidenceSegmentationService = type(
        "EvidenceSegmentationService",
        (),
        {"__init__": lambda self, strategy_set: setattr(self, "strategy_set", strategy_set)},
    )
    evidence_segmentation_module.HeuristicSemanticEnrichmentStrategy = type("HeuristicSemanticEnrichmentStrategy", (), {"strategy_key": "heuristic_semantic"})
    evidence_segmentation_module.ParagraphTranscriptSegmentationStrategy = type("ParagraphTranscriptSegmentationStrategy", (), {"strategy_key": "paragraph"})

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["app.models.action_log"] = action_log_module
    sys.modules["app.services.job_dispatcher"] = job_dispatcher_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["worker.services"] = services_module
    sys.modules["worker.services.draft_generation_stage_services"] = stage_services_module
    sys.modules["worker.services.screenshot_context_builder"] = screenshot_context_builder_module
    sys.modules["worker.services.worker_repositories"] = worker_repositories_module
    sys.modules["worker.services.worker_uow"] = worker_uow_module
    sys.modules["worker.services.worker_use_cases"] = worker_use_cases_module
    sys.modules["worker.services.workflow_strategy_registry"] = workflow_registry_module
    sys.modules["worker.services.evidence_segmentation_service"] = evidence_segmentation_module

    spec = importlib.util.spec_from_file_location("worker_composition_test", COMPOSITION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkerCompositionTests(unittest.TestCase):
    def test_build_default_evidence_segmentation_stage_injects_segmentation_service(self) -> None:
        module = load_worker_composition_module()

        stage = module.build_default_evidence_segmentation_stage()

        self.assertIsNotNone(stage.segmentation_service)
        self.assertEqual(stage.segmentation_service.strategy_set["strategy_keys"]["segmenter_key"], "paragraph")


if __name__ == "__main__":
    unittest.main()
