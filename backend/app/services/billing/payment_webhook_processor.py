r"""
Application hook for verified payment webhooks (extend for entitlements / billing records).
"""

from __future__ import annotations

from app.core.observability import get_logger
from app.portability.payments.protocols import PaymentWebhookProcessorPort
from app.portability.payments.types import PaymentWebhookEvent

logger = get_logger(__name__)


class LoggingPaymentWebhookProcessor(PaymentWebhookProcessorPort):
    """Default processor: structured log only (idempotent DB updates go here later)."""

    def process(self, event: PaymentWebhookEvent) -> None:
        logger.info(
            "payment_webhook_received",
            extra={
                "event": "payment.webhook",
                "provider": event.provider.value,
                "event_type": event.event_type,
                "provider_event_id": event.provider_event_id,
                "paid": event.paid,
                "client_reference_id": event.client_reference_id,
            },
        )
