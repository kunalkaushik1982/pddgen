r"""
Unit tests for GST inclusive split helper.
"""

from __future__ import annotations

import unittest

from app.services.gst_invoice_service import compute_inclusive_gst_split


class GstInvoiceServiceTests(unittest.TestCase):
    def test_inr_intrastate_18_percent(self) -> None:
        taxable, cgst, sgst, igst, supply = compute_inclusive_gst_split(
            amount_minor=11800,
            currency="INR",
            gst_rate_bps=1800,
            intrastate=True,
        )
        self.assertEqual(supply, "intrastate")
        self.assertEqual(taxable + cgst + sgst + igst, 11800)
        self.assertEqual(igst, 0)
        self.assertEqual(cgst + sgst, 11800 - taxable)

    def test_inr_interstate_uses_igst(self) -> None:
        taxable, cgst, sgst, igst, supply = compute_inclusive_gst_split(
            amount_minor=11800,
            currency="INR",
            gst_rate_bps=1800,
            intrastate=False,
        )
        self.assertEqual(supply, "interstate")
        self.assertEqual(cgst, 0)
        self.assertEqual(sgst, 0)
        self.assertGreater(igst, 0)

    def test_non_inr_no_gst(self) -> None:
        taxable, cgst, sgst, igst, supply = compute_inclusive_gst_split(
            amount_minor=1000,
            currency="USD",
            gst_rate_bps=1800,
            intrastate=True,
        )
        self.assertEqual(supply, "export_or_non_gst")
        self.assertEqual(taxable, 1000)
        self.assertEqual(cgst + sgst + igst, 0)


if __name__ == "__main__":
    unittest.main()
