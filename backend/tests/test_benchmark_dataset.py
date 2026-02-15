import json
import unittest
from pathlib import Path


class BenchmarkDatasetTests(unittest.TestCase):
    def test_manifest_contains_required_invoice_and_receipt_variants(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "datasets/benchmark/v1/manifest.json"
        self.assertTrue(manifest_path.exists())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required_variants = {"clean", "noisy", "rotated", "multilayout"}
        self.assertEqual(set(manifest["required_variants"]), required_variants)

        samples = manifest["samples"]
        by_doc_type: dict[str, set[str]] = {}
        for sample in samples:
            doc_type = sample["doc_type"]
            variant = sample["variant"]
            by_doc_type.setdefault(doc_type, set()).add(variant)

            png_path = repo_root / sample["png_path"]
            pdf_path = repo_root / sample["pdf_path"]
            self.assertTrue(png_path.exists(), f"missing sample file: {png_path}")
            self.assertTrue(pdf_path.exists(), f"missing sample file: {pdf_path}")

        self.assertEqual(set(by_doc_type.keys()), {"invoice", "receipt"})
        self.assertEqual(by_doc_type["invoice"], required_variants)
        self.assertEqual(by_doc_type["receipt"], required_variants)


if __name__ == "__main__":
    unittest.main()
