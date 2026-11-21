import unittest
from unittest.mock import patch
from services.search_service import live_schemes


class SchemeSearchTests(unittest.TestCase):
    @patch("ddgs.DDGS")
    def test_official_results_only(self, search):
        search.return_value.text.return_value = [
            {"href": "https://pmkisan.gov.in/", "title": "PM-KISAN", "body": "Official portal"},
            {"href": "https://example.org/", "title": "Ignore"}]
        result = live_schemes("rice", "Bihar", "income support")
        self.assertIn("pmkisan.gov.in", result)
        self.assertNotIn("example.org", result)
        self.assertIn("Bihar", search.return_value.text.call_args.args[0])

    @patch("ddgs.DDGS")
    def test_search_failure_disclosed(self, search):
        search.return_value.text.side_effect = TimeoutError()
        self.assertIn("Live search unavailable", live_schemes("rice", "Bihar"))
        self.assertEqual(search.return_value.text.call_count, 2)
