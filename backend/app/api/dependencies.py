r"""
Purpose: Shared dependency providers for backend routes.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\dependencies.py
"""

from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.demo_generation_runner import DemoGenerationRunnerService
from app.services.document_renderer import DocumentRendererService
from app.services.job_dispatcher import JobDispatcherService
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.storage.storage_service import StorageService


def get_storage_service() -> StorageService:
    """Provide the configured storage service."""
    return StorageService()


def get_artifact_ingestion_service() -> ArtifactIngestionService:
    """Provide the artifact ingestion service."""
    return ArtifactIngestionService(storage_service=get_storage_service())


def get_pipeline_orchestrator_service() -> PipelineOrchestratorService:
    """Provide the pipeline orchestration service."""
    return PipelineOrchestratorService(storage_service=get_storage_service())


def get_document_renderer_service() -> DocumentRendererService:
    """Provide the DOCX rendering service."""
    return DocumentRendererService(storage_service=get_storage_service())


def get_demo_generation_runner_service() -> DemoGenerationRunnerService:
    """Provide the inline demo-mode generation service."""
    return DemoGenerationRunnerService()


def get_job_dispatcher_service() -> JobDispatcherService:
    """Provide the background job dispatcher service."""
    return JobDispatcherService()
