import unittest

from database.medicine import MEDICINE_DB
from services.rag_service import search_rag


class RetrievalTests(unittest.TestCase):
    def test_all_catalogue_records_are_reachable(self):
        for crop, issues in MEDICINE_DB.items():
            for issue, record in issues.items():
                with self.subTest(crop=crop, issue=issue):
                    products = record.get("recommended_products", [])
                    hits = search_rag(issue, crop, len(products) + 1)
                    self.assertEqual(len(hits), len(products))
                    for hit, product in zip(hits, products):
                        metadata = hit["metadata"]
                        self.assertEqual((metadata["crop"], metadata["issue_name"]), (crop, issue))
                        self.assertTrue(metadata["source"])
                        self.assertEqual(metadata["source"], product["source"])
                        self.assertIn(product["active_ingredient"], hit["document"])

    def test_aliases_and_limits(self):
        direct = search_rag("leafspot", "rice", 1)
        self.assertEqual(len(direct), 1)
        self.assertEqual(search_rag("leaf  spot", "Paddy", 1), direct)
        self.assertEqual(search_rag("leafspot", "rice", -1), [])
        self.assertEqual(search_rag("unknown", "rice"), [])
