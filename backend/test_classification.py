import unittest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database.database import Base
from database.models import Farmer
from api.routes import advise
from unittest.mock import patch
from langchain_core.exceptions import OutputParserException
from services.treatment_flow import Classification, assess


class ClassificationTests(unittest.TestCase):
    @patch("services.farm_memory._chat", side_effect=AssertionError("No second model call needed"))
    @patch("services.treatment_flow.model")
    def test_follow_up_routes_with_persisted_question(self, model, summarizer):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        invoke = model.return_value.with_structured_output.return_value.invoke
        def classify(messages):
            turn = json.loads(messages[-1].content)
            first = not turn["previous_farm_note"]
            if not first:
                self.assertEqual(turn["request"], "fruit")
                self.assertIn("tomato black", turn["previous_farm_note"])
                self.assertIn("phal ya patte", turn["previous_farm_note"])
            return Classification(kind="clarify", crop="tomato", disease="", language="Hinglish",
                                  summary="Tomato black", continuity="tomato black",
                                  follow_up="phal ya patte?" if first else "Phal par daag kis jagah hai?")
        invoke.side_effect = classify
        with Session(engine) as db:
            farmer = Farmer(user_id=1, crop="wheat")
            db.add(farmer)
            db.commit()
            advise(db, farmer, "meri tomato crop black ho rhi hai")
        with Session(engine) as db:
            reply = advise(db, db.get(Farmer, 1), "fruit")
            self.assertIn("kis jagah", reply["response"])
            self.assertNotIn("_continuity", reply)
        self.assertEqual(invoke.call_count, 2)
        summarizer.assert_not_called()
        engine.dispose()

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
