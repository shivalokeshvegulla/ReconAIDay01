
import unittest

from src.recon import validate_row


class TestValidateRow(unittest.TestCase):
    #test for missing required field
    def test_missing_amount(self):
        row = {
            "txn_ref": "TXN1001",
            "value_date": "2026-10-01",
            "currency": "USD",
            "amount": "",
        }

        errors = validate_row(row, 2, "ledger.csv", {"USD", "EUR", "GBP", "INR"})

        self.assertIn("Missing required field: amount", errors)
    #test for invalid date format
    def test_invalid_date(self):
        row = {
            "txn_ref": "TXN1001",
            "value_date": "2026-02-30",
            "currency": "USD",
            "amount": "100.00",
        }

        errors = validate_row(row, 2, "ledger.csv", {"USD", "EUR", "GBP", "INR"})

        self.assertIn("Invalid date: value_date", errors)
    #test for unsupported currency
    def test_unsupported_currency(self):
        row = {
            "txn_ref": "TXN1001",
            "value_date": "2026-10-01",
            "currency": "XYZ",
            "amount": "100.00",
        }

        errors = validate_row(
            row, 2, "ledger.csv", {"USD", "EUR", "GBP", "INR"}
        )

        self.assertIn(f"Unsupported currency: XYZ", errors)
    #test for invalid amount
    def test_invalid_amount(self):
        row = {
            "txn_ref": "TXN1001",
            "value_date": "2026-10-01",
            "currency": "USD",
            "amount": "abc",
        }

        errors = validate_row(
            row, 2, "ledger.csv", {"USD", "EUR", "GBP", "INR"}
        )

        self.assertIn(
            "Invalid amount: amount must be numeric",
            errors,
        )







if __name__ == "__main__":
    unittest.main()
