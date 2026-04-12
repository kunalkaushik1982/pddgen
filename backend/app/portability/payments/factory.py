r"""
Factory for payment gateways (Dependency Inversion: depend on ``PaymentGatewayFactoryPort``).
"""

from __future__ import annotations

from app.core.config import Settings
from app.portability.payments.exceptions import PaymentConfigurationError
from app.portability.payments.protocols import PaymentGatewayFactoryPort, PaymentGatewayPort
from app.portability.payments.types import PaymentProvider
from app.portability.payments.razorpay_gateway import RazorpayPaymentGateway
from app.portability.payments.stripe_gateway import StripePaymentGateway


class DefaultPaymentGatewayFactory(PaymentGatewayFactoryPort):
    """Selects Stripe vs Razorpay strategy based on ``PaymentProvider``."""

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def build(self, provider: PaymentProvider) -> PaymentGatewayPort:
        if provider is PaymentProvider.STRIPE:
            return StripePaymentGateway(settings=self._settings)
        if provider is PaymentProvider.RAZORPAY:
            return RazorpayPaymentGateway(settings=self._settings)
        raise PaymentConfigurationError(f"Unsupported payment provider: {provider!s}.")
