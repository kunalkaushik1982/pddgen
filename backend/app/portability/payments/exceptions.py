r"""
Payment domain errors (adapters raise these; routes map to HTTP).
"""

from __future__ import annotations


class PaymentError(Exception):
    """Base class for payment failures."""

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class PaymentConfigurationError(PaymentError):
    """Missing or invalid gateway configuration (keys, webhook secrets)."""


class PaymentGatewayRejectedError(PaymentError):
    """Provider API rejected the request (bad params, auth, etc.)."""


class PaymentWebhookVerificationError(PaymentError):
    """Webhook signature or payload could not be verified."""
