import ast
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from pydantic import SecretStr
from app.core.llm import get_llm, invoke, QuotaExceeded
from app.core.config import settings
from app.core.embeddings import metadata, verify_collection


class FactoryTests(unittest.TestCase):
    def tearDown(self):
        get_llm.cache_clear()

    @patch("app.core.llm.init_chat_model")
    def test_router_cache_and_roles(self, constructor):
        with patch.object(settings, "GOOGLE_API_KEY", SecretStr("test")), patch.object(settings, "LLM_MODEL_ROUTER", "router-test"):
            self.assertIs(get_llm("router"), get_llm("router"))
            self.assertEqual(constructor.call_count, 1)
            self.assertEqual(constructor.call_args.kwargs["model"], "router-test")
            self.assertEqual(constructor.call_args.kwargs["temperature"], 0)
            self.assertEqual(constructor.call_args.kwargs["model_provider"], "google_genai")
            get_llm("reasoning")
            self.assertEqual(constructor.call_args.kwargs["model"], settings.name_for("reasoning"))

    def test_missing_key(self):
        with patch.object(settings, "GOOGLE_API_KEY", None), self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY"):
            get_llm()

    def test_quota_retries(self):
        runnable = Mock()
        runnable.invoke.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        with patch.object(settings, "LLM_MAX_RETRIES", 2), patch("app.core.llm.time.sleep") as sleep, self.assertRaises(QuotaExceeded):
            invoke(runnable, [])
        self.assertEqual(runnable.invoke.call_count, 3)
        self.assertEqual([entry.args[0] for entry in sleep.call_args_list], [1, 2])

    def test_embedding_change_requires_reset(self):
        verify_collection(Mock(metadata=metadata()))
        with self.assertRaisesRegex(ValueError, "--reset"):
            verify_collection(Mock(metadata={"embedding_model": "old"}))

    def test_one_chat_constructor(self):
        root = Path(__file__).resolve().parent
        for path in root.rglob("*.py"):
            if ".venv" in path.parts or path == root / "app/core/llm.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                if isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        self.assertFalse(name.name == "init_chat_model" or
                                         ((node.module or "").startswith("langchain_") and name.name.startswith("Chat")), path)
