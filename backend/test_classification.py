import unittest
from unittest.mock import patch
from langchain_core.exceptions import OutputParserException
from services.treatment_flow import Classification, assess


class ClassificationTests(unittest.TestCase):
    @patch("services.treatment_flow.model")
    def test_malformed_then_valid(self, model):
        invoke = model.return_value.with_structured_output.return_value.invoke
        invoke.side_effect = [OutputParserException("Invalid JSON"), Classification(
            kind="farm", crop="wheat", disease="", language="Hindi", summary="Mausam")]
        self.assertIsNone(assess("Kal ka mausam?", "wheat"))
        self.assertEqual(invoke.call_count, 2)
        model.return_value.with_structured_output.assert_called_once_with(Classification)

    @patch("services.treatment_flow.model")
    def test_invalid_fields_never_trigger_treatment(self, model):
        invoke = model.return_value.with_structured_output.return_value.invoke
        invoke.return_value = {"kind": "unexpected"}
        reply = assess("test", "tomato")
        self.assertTrue(reply["fallback"])
        self.assertIn("clarify", reply["response"])
        self.assertEqual(invoke.call_count, 2)
