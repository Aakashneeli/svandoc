import json
import unittest
import zipfile
from io import BytesIO

from svandoc_backend.tally_connector import build_tally_import_package


class TallyConnectorTests(unittest.TestCase):
    def test_build_tally_import_package_contains_expected_files(self) -> None:
        package = build_tally_import_package(
            {
                "document_type": "receipt",
                "metadata": {"document_id": "doc-1"},
                "merchant": {"name": "Shop A"},
                "receipt": {"receipt_number": "R-100"},
                "amounts": {"currency": "USD", "subtotal": 90, "tax": 10, "total": 100},
            }
        )

        self.assertTrue(package.filename.endswith(".tally.zip"))
        with zipfile.ZipFile(BytesIO(package.content), mode="r") as archive:
            names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("voucher.xml", names)
            self.assertIn("summary.csv", names)
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            self.assertEqual(manifest["provider"], "tally")
            self.assertEqual(manifest["document_type"], "receipt")


if __name__ == "__main__":
    unittest.main()
