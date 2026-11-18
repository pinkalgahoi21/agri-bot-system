import unittest
from services.advisory import parse_answer, offline_answer
from services.rag_service import search_rag


class AdvisoryTests(unittest.TestCase):
    def test_localized_sections_survive_provider_blocks(self):
        reply = parse_answer([{'text': '{"title":"फसल","sections":[{"heading":"जाँच","body":"पत्ते देखें"}]}'}])
        self.assertEqual(reply['response'], 'फसल\n\nजाँच\nपत्ते देखें')

    def test_invalid_json_is_not_displayed(self):
        with self.assertRaises(ValueError):
            parse_answer('{"title":"missing sections"}')

    def test_offline_scheme_directory(self):
        reply = offline_answer('बीमा योजना', 'rice', 'Pune')
        self.assertTrue(reply['fallback'])
        self.assertIn('myscheme.gov.in', reply['response'])

    def test_no_cross_crop_treatment(self):
        self.assertFalse(search_rag('early blight', 'unlisted crop'))
