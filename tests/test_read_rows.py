import unittest
from pathlib import Path
from src.recon import read_rows, DataQualityError
#Tests for the read_rows function in recon.py
class TestReadRows(unittest.TestCase):
    #test for reading rows from a valid CSV file
    def test_reads_ledger_rows(self):
        path = Path(__file__).resolve().parent.parent / "data" / "ledger.csv"
        required_fields = {"txn_ref", "value_date", "currency", "amount",}
        rows = read_rows(path, required_fields)
        self.assertGreater(len(rows), 0)
        line_number, row = rows[0]
        self.assertEqual(line_number, 2)
        self.assertEqual(len(rows), 5)
        self.assertEqual(row["txn_ref"], "TXN1001")
        self.assertEqual(row["currency"], "USD")
    #test for missing required column
    def test_missing_required_column(self):
        path = Path(__file__).resolve().parent.parent / "data" / "ledger.csv"

        required_fields = {
            "txn_ref",
            "value_date",
            "currency",
            "amount",
            "account_id",
        }

        with self.assertRaises(DataQualityError):
            read_rows(path, required_fields)
    #test for CSV without header
    def test_csv_without_header(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.csv"
            path.write_text("", encoding="utf-8")

            with self.assertRaises(DataQualityError):
                read_rows(path, {"txn_ref"})


if __name__ == "__main__":
    unittest.main()
