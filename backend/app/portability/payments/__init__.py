r"""
Payment portability layer: ports, DTOs, Stripe/Razorpay adapters, factory.

Import from here for application wiring.
"""

from app.portability.payments.exceptions import (
    PaymentConfigurationError,
    PaymentError,
    PaymentGatewayRejectedError,
    PaymentWebhookVerificationError,
)
from app.portability.payments.factory import DefaultPaymentGatewayFactory
from app.portability.payments.protocols import PaymentGatewayFactoryPort, PaymentGatewayPort, PaymentWebhookProcessorPort
from app.portability.payments.types import CheckoutSessionRequest, CheckoutSessionResult, PaymentProvider, PaymentWebhookEvent

__all__ = [
    "CheckoutSessionRequest",
    "CheckoutSessionResult",
    "DefaultPaymentGatewayFactory",
    "PaymentConfigurationError",
    "PaymentError",
    "PaymentGatewayFactoryPort",
    "PaymentGatewayPort",
    "PaymentGatewayRejectedError",
    "PaymentProvider",
    "PaymentWebhookEvent",
    "PaymentWebhookProcessorPort",
    "PaymentWebhookVerificationError",
]
