
import unittest
from pathlib import Path

from src.recon import load_manifest


class TestLoadManifest(unittest.TestCase):

    def test_loads_allowed_currencies(self):
        path = Path(__file__).resolve().parent.parent / "schema_manifest.json"

        manifest = load_manifest(path)

        self.assertIn("allowed_currencies", manifest)
        self.assertEqual(
            manifest["allowed_currencies"],
            ["USD", "EUR", "GBP", "INR"],
        )


if __name__ == "__main__":
    unittest.main()
