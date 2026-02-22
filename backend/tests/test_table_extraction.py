import unittest

from svandoc_backend.table_extraction import extract_line_items_from_tables


class TableExtractionTests(unittest.TestCase):
    def test_stitches_multi_page_tables_and_skips_repeated_headers(self) -> None:
        payload = {
            "tables": [
                {
                    "table_id": "line_items",
                    "page_number": 1,
                    "headers": ["Description", "Qty", "Unit Price", "Amount"],
                    "rows": [
                        ["Description", "Qty", "Unit Price", "Amount"],
                        ["Widget A", "2", "10.00", "20.00"],
                    ],
                },
                {
                    "table_id": "line_items",
                    "page_number": 2,
                    "headers": ["Description", "Qty", "Unit Price", "Amount"],
                    "rows": [
                        ["Description", "Qty", "Unit Price", "Amount"],
                        ["Widget B", "1", "5.50", "5.50"],
                    ],
                },
            ]
        }

        items = extract_line_items_from_tables(structured_payload=payload, include_category=False)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["description"], "Widget A")
        self.assertEqual(items[1]["description"], "Widget B")
        self.assertEqual(items[0]["quantity"], 2.0)
        self.assertEqual(items[1]["line_total"], 5.5)

    def test_expands_rowspan_merged_cells(self) -> None:
        payload = {
            "tables": [
                {
                    "table_id": "line_items",
                    "page_number": 1,
                    "headers": ["Description", "Qty", "Unit Price", "Amount"],
                    "rows": [
                        [
                            {"text": "Bundle Plan", "rowspan": 2},
                            {"text": "1"},
                            {"text": "15.00"},
                            {"text": "15.00"},
                        ],
                        [
                            {"text": "2"},
                            {"text": "15.00"},
                            {"text": "30.00"},
                        ],
                    ],
                }
            ]
        }

        items = extract_line_items_from_tables(structured_payload=payload, include_category=False)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["description"], "Bundle Plan")
        self.assertEqual(items[1]["description"], "Bundle Plan")
        self.assertEqual(items[1]["quantity"], 2.0)
        self.assertEqual(items[1]["line_total"], 30.0)

    def test_ignores_summary_rows(self) -> None:
        payload = {
            "tables": [
                {
                    "headers": ["Description", "Qty", "Unit Price", "Amount"],
                    "rows": [
                        ["Consulting", "1", "100.00", "100.00"],
                        ["Subtotal", "", "", "100.00"],
                        ["Tax", "", "", "10.00"],
                        ["Total", "", "", "110.00"],
                    ],
                }
            ]
        }

        items = extract_line_items_from_tables(structured_payload=payload, include_category=False)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["description"], "Consulting")


if __name__ == "__main__":
    unittest.main()
