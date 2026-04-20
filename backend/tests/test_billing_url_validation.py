r"""
Tests for checkout redirect URL allowlist validation.
"""

from __future__ import annotations

import unittest

from app.services.billing.billing_exceptions import BillingRuleError
from app.services.billing.billing_url_validation import validate_checkout_redirect_urls


class BillingUrlValidationTests(unittest.TestCase):
    def test_empty_allowlist_allows_any_url(self) -> None:
        validate_checkout_redirect_urls(
            success_url="https://evil.example/phish",
            cancel_url="https://other.example/cancel",
            allowlist=[],
        )

    def test_allowlist_requires_prefix_match(self) -> None:
        with self.assertRaises(BillingRuleError) as ctx:
            validate_checkout_redirect_urls(
                success_url="https://evil.example/ok",
                cancel_url="https://app.example.com/cancel",
                allowlist=["https://app.example.com"],
            )
        self.assertIn("success_url", str(ctx.exception).lower())

    def test_allowlist_accepts_matching_urls(self) -> None:
        validate_checkout_redirect_urls(
            success_url="https://app.example.com/billing?paid=1",
            cancel_url="https://app.example.com/billing",
            allowlist=["https://app.example.com"],
        )


if __name__ == "__main__":
    unittest.main()
