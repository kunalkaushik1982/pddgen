r"""
Purpose: Shared dependency providers for backend routes.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\dependencies.py
"""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.observability import set_log_context
from app.db.session import get_db_session
from app.models.user import UserModel
from app.services.platform.action_log_service import ActionLogService
from app.services.platform.csrf_service import CsrfService
from app.services.artifacts.artifact_ingestion import ArtifactIngestionService
from app.services.artifacts.artifact_validation import ArtifactValidationService
from app.portability.auth_registry import build_identity_provider
from app.portability.http_client import build_llm_http_client
from app.services.auth.auth_service import AuthService
from app.services.platform.database_session_service import DatabaseSessionService
from app.services.draft_session.draft_session_diagram_service import DraftSessionDiagramService
from app.services.draft_session.draft_session_review_service import DraftSessionReviewService
from app.portability.job_messaging.locks.redis_lock import build_redis_distributed_lock
from app.portability.job_messaging.run_guards.session_run_guard import build_draft_run_guard, build_screenshot_run_guard
from app.portability.job_messaging.wiring import build_job_enqueue_port
from app.services.documents.document_pdf_converter import DocumentPdfConverter
from app.services.documents.document_renderer import DocumentRendererService
from app.services.documents.document_template_renderer import DocumentTemplateRenderer
from app.services.generation.job_dispatcher import JobDispatcherService
from app.services.draft_session.meeting_service import MeetingService
from app.services.generation.pipeline_orchestrator import PipelineOrchestratorService
from app.services.generation.process_diagram_service import ProcessDiagramService
from app.services.draft_session.process_group_service import ProcessGroupService
from app.services.generation.screenshot_mapping import ScreenshotMappingService
from app.services.chat.session_chat_service import SessionChatService
from app.services.generation.step_extraction import StepExtractionService
from app.services.generation.transcript_intelligence import TranscriptIntelligenceService
from app.portability.payments import DefaultPaymentGatewayFactory, PaymentGatewayFactoryPort, PaymentWebhookProcessorPort
from app.services.billing.billing_checkout_service import BillingCheckoutService
from app.services.billing.billing_webhook_processor import BillingPaymentWebhookProcessor
from app.storage.storage_service import StorageService


def get_csrf_service(request: Request) -> CsrfService:
    """Provide CSRF helpers (same instance as ``app.state.csrf_service``)."""
    return request.app.state.csrf_service


def get_storage_service() -> StorageService:
    """Provide the configured storage service."""
    return StorageService()


def get_artifact_ingestion_service() -> ArtifactIngestionService:
    """Provide the artifact ingestion service."""
    settings = get_settings()
    return ArtifactIngestionService(
        storage_service=get_storage_service(),
        validation_service=ArtifactValidationService(settings=settings),
    )


def get_action_log_service() -> ActionLogService:
    """Provide the audit action-log service."""
    return ActionLogService()


def get_process_diagram_service() -> ProcessDiagramService:
    """Provide the read-model diagram builder for API responses."""
    return ProcessDiagramService()


def get_document_template_renderer_service() -> DocumentTemplateRenderer:
    """Provide the DOCX template renderer (registry wired with shared ProcessDiagramService)."""
    return DocumentTemplateRenderer(
        process_diagram_service=get_process_diagram_service(),
        context_builder=None,
    )


def get_pipeline_orchestrator_service() -> PipelineOrchestratorService:
    """Provide the pipeline orchestration service (fully wired from this composition root)."""
    storage = get_storage_service()
    return PipelineOrchestratorService(
        storage_service=storage,
        step_extraction_service=StepExtractionService(),
        transcript_intelligence_service=TranscriptIntelligenceService(),
        screenshot_mapping_service=ScreenshotMappingService(),
        process_group_service=get_process_group_service(),
    )


def get_document_renderer_service() -> DocumentRendererService:
    """Provide the DOCX/PDF rendering service."""
    storage = get_storage_service()
    return DocumentRendererService(
        storage_service=storage,
        template_renderer=get_document_template_renderer_service(),
        pdf_converter=DocumentPdfConverter(),
    )


def get_draft_session_diagram_service() -> DraftSessionDiagramService:
    """Provide the draft-session diagram mutation service."""
    return DraftSessionDiagramService(action_log_service=get_action_log_service())


def get_draft_session_review_service() -> DraftSessionReviewService:
    """Provide the BA review mutation service."""
    return DraftSessionReviewService(action_log_service=get_action_log_service())


def get_session_chat_service() -> SessionChatService:
    """Provide the session-grounded Q&A service."""
    settings = get_settings()
    llm_client = build_llm_http_client(settings) if settings.ai_enabled else None
    return SessionChatService(
        storage_service=get_storage_service(),
        llm_http_client=llm_client,
    )


def get_job_dispatcher_service() -> JobDispatcherService:
    """Provide the background job dispatcher service."""
    settings = get_settings()
    lock = build_redis_distributed_lock(settings)
    return JobDispatcherService(
        enqueue=build_job_enqueue_port(settings),
        draft_run_guard=build_draft_run_guard(settings, lock=lock),
        screenshot_run_guard=build_screenshot_run_guard(settings, lock=lock),
    )

def get_meeting_service() -> MeetingService:
    """Provide meeting management service."""
    return MeetingService()


def get_process_group_service() -> ProcessGroupService:
    """Provide process-group management service."""
    return ProcessGroupService()


def get_auth_service() -> AuthService:
    """Provide the configured auth facade."""
    settings = get_settings()
    return AuthService(
        identity_provider=build_identity_provider(settings),
        session_service=DatabaseSessionService(),
    )


def get_current_user(
    session_cookie: Annotated[str | None, Cookie(alias=get_settings().auth_cookie_name)] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> UserModel:
    """Resolve the current authenticated user from the configured session transport."""
    if session_cookie:
        user = auth_service.authenticate_token(db, token=session_cookie)
        set_log_context(actor=user.username)
        return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


def require_workspace_user(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """Reject users limited to the admin console (workspace and uploads APIs)."""
    if current_user.admin_console_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is limited to the admin console.",
        )
    return current_user


def get_current_admin_user(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """Resolve the current authenticated admin user."""
    settings = get_settings()
    if current_user.username not in settings.admin_usernames:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def get_payment_gateway_factory() -> PaymentGatewayFactoryPort:
    """Injectable payment gateway factory (Stripe / Razorpay strategies)."""
    return DefaultPaymentGatewayFactory(settings=get_settings())


def get_payment_webhook_processor(
    db: Annotated[Session, Depends(get_db_session)],
) -> PaymentWebhookProcessorPort:
    """Injectable webhook side-effects handler (idempotent billing + entitlements)."""
    return BillingPaymentWebhookProcessor(db=db)


def get_billing_checkout_service(
    db: Annotated[Session, Depends(get_db_session)],
    factory: Annotated[PaymentGatewayFactoryPort, Depends(get_payment_gateway_factory)],
) -> BillingCheckoutService:
    """Catalog + custom checkout orchestration."""
    return BillingCheckoutService(db=db, factory=factory)
