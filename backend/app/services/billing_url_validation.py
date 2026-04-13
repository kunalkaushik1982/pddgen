r"""
Validate payment checkout redirect URLs against an optional allowlist (open-redirect mitigation).
"""

from __future__ import annotations

from app.services.billing_exceptions import BillingRuleError


def validate_checkout_redirect_urls(*, success_url: str, cancel_url: str, allowlist: list[str]) -> None:
    """Raise ``BillingRuleError`` if allowlist is set and URLs do not match any prefix."""
    cleaned = [p.strip() for p in allowlist if p and str(p).strip()]
    if not cleaned:
        return
    for label, url in (("success_url", success_url), ("cancel_url", cancel_url)):
        u = (url or "").strip()
        if not any(u.startswith(prefix) for prefix in cleaned):
            raise BillingRuleError(
                f"{label} must start with one of the configured payment_checkout_redirect_allowlist prefixes.",
            )
