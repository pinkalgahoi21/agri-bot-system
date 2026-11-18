import unittest
from services.table_evidence import linked_entry
from services.vector_rag import table_page


class SourceEvidenceTests(unittest.TestCase):
    def test_real_pdf_split_row(self):
        page = table_page("3._bio_pesticide_mup_as_on_30.09.2025.pdf", 3)
        product, row = linked_entry(page, "Tomato", "early blight")
        self.assertTrue(product.startswith("Bacillus subtilis"))
        self.assertIn("Tomato", row)
        self.assertIsNone(linked_entry(page, "Banana", "early blight"))

    def test_does_not_borrow_next_heading(self):
        self.assertIsNone(linked_entry("Tomato Early blight\nProduct 2% SC", "tomato", "early blight"))
