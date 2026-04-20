r"""
Billing-specific errors mapped to HTTP by payment routes.
"""


class BillingProductNotFoundError(LookupError):
    """No active ``billing_products`` row for the requested SKU."""

    def __init__(self, sku: str) -> None:
        super().__init__(sku)
        self.sku = sku


class BillingRuleError(ValueError):
    """Checkout blocked by a business rule (provider mismatch, missing price, etc.)."""
