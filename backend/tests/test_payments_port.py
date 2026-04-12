r"""
Tests for payment ports: factory wiring and CSRF exemption for webhooks.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.core.config import Settings
from app.portability.payments import DefaultPaymentGatewayFactory, PaymentProvider
from app.portability.payments.exceptions import PaymentConfigurationError
from app.services.csrf_service import CsrfService


class PaymentPortTests(unittest.TestCase):
    def test_factory_raises_on_missing_stripe_secret(self) -> None:
        settings = Settings(
            payment_stripe_secret_key="",
            payment_stripe_webhook_secret="whsec_x",
        )
        factory = DefaultPaymentGatewayFactory(settings=settings)
        with self.assertRaises(PaymentConfigurationError):
            factory.build(PaymentProvider.STRIPE)

    def test_factory_raises_on_missing_razorpay_keys(self) -> None:
        settings = Settings(
            payment_razorpay_key_id="",
            payment_razorpay_key_secret="",
        )
        factory = DefaultPaymentGatewayFactory(settings=settings)
        with self.assertRaises(PaymentConfigurationError):
            factory.build(PaymentProvider.RAZORPAY)

    def test_csrf_middleware_skips_payment_webhooks(self) -> None:
        settings = Settings(
            auth_csrf_protection_enabled=True,
            api_prefix="/api",
            auth_cookie_name="pdd_generator_session",
            auth_csrf_cookie_name="pdd_generator_csrf",
            auth_csrf_header_name="X-CSRF-Token",
        )
        service = CsrfService(settings=settings)
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/payments/webhooks/stripe"
        request.cookies = {
            settings.auth_cookie_name: "session-token",
        }
        request.headers = {}
        # Without exemption, cookie session + missing CSRF would raise.
        service.validate_request(request)


if __name__ == "__main__":
    unittest.main()
