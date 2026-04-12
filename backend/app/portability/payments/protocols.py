r"""
Ports (interface-first): payment checkout + webhook verification per provider.

- ``PaymentGatewayPort``: Strategy interface for Stripe vs Razorpay.
- ``PaymentGatewayFactoryPort``: Factory for resolving a gateway by ``PaymentProvider``.
- ``PaymentWebhookProcessorPort``: Application hook after a verified, normalized event (OCP: swap impl).
"""

from __future__ import annotations

from typing import Mapping, Protocol

from app.portability.payments.types import CheckoutSessionRequest, CheckoutSessionResult, PaymentProvider, PaymentWebhookEvent


class PaymentGatewayPort(Protocol):
    """Provider checkout + signed webhook parsing behind one abstraction (Adapter pattern)."""

    @property
    def provider(self) -> PaymentProvider: ...

    def create_checkout_session(self, request: CheckoutSessionRequest) -> CheckoutSessionResult:
        """Create a hosted checkout or order; returns redirect URL and/or client fields."""
        ...

    def verify_and_parse_webhook(self, *, raw_body: bytes, headers: Mapping[str, str]) -> PaymentWebhookEvent:
        """Verify provider signature and map to a normalized ``PaymentWebhookEvent``."""
        ...


class PaymentGatewayFactoryPort(Protocol):
    """Abstract factory for payment strategies (DIP: depend on this, not concrete gateways)."""

    def build(self, provider: PaymentProvider) -> PaymentGatewayPort:
        """Return a configured gateway for the given provider."""
        ...


class PaymentWebhookProcessorPort(Protocol):
    """Handle business effects of a verified payment event (idempotent updates, entitlements, etc.)."""

    def process(self, event: PaymentWebhookEvent) -> None:
        ...
