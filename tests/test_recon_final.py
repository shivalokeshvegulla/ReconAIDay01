
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.recon import (
    DataQualityError,
    load_manifest,
    read_rows,
    validate_row,
    load_validate,
    build_index,
    compare_sources,
    summarize_source,
)


class TestReconFinal(unittest.TestCase):

    def setUp(self):
        self.allowed_currencies = {"USD", "EUR", "GBP", "INR"}
        self.required_fields = {
            "txn_ref",
            "value_date",
            "currency",
            "amount",
        }

    # 1. CSV reading
    def test_read_rows_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.csv"
            path.write_text(
                "txn_ref,value_date,currency,amount\n"
                "TXN1001,2026-10-01,USD,100.00\n",
                encoding="utf-8",
            )

            rows = read_rows(path, self.required_fields)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], 2)
            self.assertEqual(rows[0][1]["txn_ref"], "TXN1001")

    def test_read_rows_missing_column(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.csv"
            path.write_text(
                "txn_ref,value_date,currency\n"
                "TXN1001,2026-10-01,USD\n",
                encoding="utf-8",
            )

            with self.assertRaises(DataQualityError):
                read_rows(path, self.required_fields)

    def test_read_rows_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.csv"

            with self.assertRaises(DataQualityError):
                read_rows(path, self.required_fields)

    # 2. Row validation
    def test_valid_row(self):
        row = {
            "txn_ref": "TXN1001",
            "value_date": "2026-10-01",
            "currency": "USD",
            "amount": "100.00",
        }

        errors = validate_row(
            row, 2, "ledger.csv", self.allowed_currencies
        )

        self.assertEqual(errors, [])

    def test_invalid_amount(self):
        row = {
            "txn_ref": "TXN1002",
            "value_date": "2026-10-01",
            "currency": "USD",
            "amount": "not_a_number",
        }

        errors = validate_row(
            row, 3, "bad_amount.csv", self.allowed_currencies
        )

        self.assertIn(
            "Invalid amount: amount must be numeric", errors
        )

    def test_missing_amount(self):
        row = {
            "txn_ref": "TXN1003",
            "value_date": "2026-10-01",
            "currency": "USD",
            "amount": "",
        }

        errors = validate_row(
            row, 4, "bad_amount.csv", self.allowed_currencies
        )

        self.assertIn("Missing required field: amount", errors)

    def test_invalid_date(self):
        row = {
            "txn_ref": "TXN1004",
            "value_date": "2026-02-30",
            "currency": "USD",
            "amount": "20.00",
        }

        errors = validate_row(
            row, 5, "ledger.csv", self.allowed_currencies
        )

        self.assertTrue(any("Invalid date" in error for error in errors))

    def test_unsupported_currency(self):
        row = {
            "txn_ref": "TXN1005",
            "value_date": "2026-10-01",
            "currency": "XYZ",
            "amount": "20.00",
        }

        errors = validate_row(
            row, 6, "ledger.csv", self.allowed_currencies
        )

        self.assertIn("Unsupported currency: XYZ", errors)

    # 3. Manifest loading
    def test_load_manifest_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "schema_manifest.json"
            expected = {"required_fields": ["txn_ref"]}
            path.write_text(json.dumps(expected), encoding="utf-8")

            result = load_manifest(path)

            self.assertEqual(result, expected)

    def test_load_manifest_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "schema_manifest.json"
            path.write_text("{invalid json", encoding="utf-8")

            with self.assertRaises(DataQualityError):
                load_manifest(path)

    # 4. File-level validation
    def test_load_validate_bad_amount_fixture(self):
        project_root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(
            project_root / "schema_manifest.json"
        )

        results = load_validate(
            project_root / "data",
            "bad_amount.csv",
            manifest,
        )

        by_txn = {result["txn_ref"]: result for result in results}

        self.assertTrue(by_txn["TXN3001"]["valid"])
        self.assertFalse(by_txn["TXN3002"]["valid"])
        self.assertFalse(by_txn["TXN3003"]["valid"])

    # 5. Duplicate detection
    def test_duplicate_settlement_fixture(self):
        project_root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(
            project_root / "schema_manifest.json"
        )

        results = load_validate(
            project_root / "data",
            "duplicate_settlement.csv",
            manifest,
        )

        index, duplicates = build_index(results)

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(
            duplicates[0]["key"],
            ("TXN2001", "2026-10-03", "USD"),
        )
        self.assertEqual(duplicates[0]["row_number"], 3)
        self.assertEqual(len(index), 2)

    # 6. Reconciliation comparison
    def test_compare_sources_detects_exceptions(self):
        ledger_results = [
            {
                "source": "ledger.csv",
                "row_number": 2,
                "valid": True,
                "row": {
                    "txn_ref": "TXN1",
                    "value_date": "2026-10-01",
                    "currency": "USD",
                    "amount": "100.00",
                },
            },
            {
                "source": "ledger.csv",
                "row_number": 3,
                "valid": True,
                "row": {
                    "txn_ref": "TXN2",
                    "value_date": "2026-10-01",
                    "currency": "USD",
                    "amount": "50.00",
                },
            },
        ]

        settlement_results = [
            {
                "source": "settlement.csv",
                "row_number": 2,
                "valid": True,
                "row": {
                    "txn_ref": "TXN1",
                    "value_date": "2026-10-01",
                    "currency": "USD",
                    "amount": "99.50",
                },
            },
            {
                "source": "settlement.csv",
                "row_number": 3,
                "valid": True,
                "row": {
                    "txn_ref": "TXN3",
                    "value_date": "2026-10-01",
                    "currency": "USD",
                    "amount": "25.00",
                },
            },
        ]

        ledger_index, _ = build_index(ledger_results)
        settlement_index, _ = build_index(settlement_results)

        result = compare_sources(
            ledger_index,
            settlement_index,
            Decimal("0.01"),
        )

        exception_types = {
            exception["type"]
            for exception in result["exceptions"]
        }

        self.assertIn("amount_mismatch", exception_types)
        self.assertIn("missing_in_settlement", exception_types)
        self.assertIn("missing_in_ledger", exception_types)
        self.assertEqual(result["matched_key_count"], 1)

    # 7. Control-total summary
    def test_summarize_source_totals(self):
        validation_results = [
            {
                "valid": True,
                "row": {
                    "currency": "USD",
                    "amount": "100.00",
                },
            },
            {
                "valid": True,
                "row": {
                    "currency": "USD",
                    "amount": "25.50",
                },
            },
        ]

        summary = summarize_source(validation_results)

        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["valid_count"], 2)
        self.assertEqual(summary["invalid_count"], 0)
        self.assertEqual(
            summary["validated_totals_by_currency"]["USD"],
            "125.50",
        )


if __name__ == "__main__":
    unittest.main()
