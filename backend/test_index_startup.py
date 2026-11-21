import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services import vector_rag as rag


class IndexStartupTest(unittest.TestCase):
    def test_interrupted_build_resume_and_restore_without_embeddings(self):
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            corpus = root / "knowledge"
            corpus.mkdir()
            (corpus / "guide.txt").write_text("tomato early blight " * 1500)
            with patch.object(rag, "KNOWLEDGE", corpus), patch.object(rag, "SEED", root / "seed.gz"), patch.dict(os.environ, VECTOR_DB_DIR=str(root / "first")), patch("services.vector_rag.get_embeddings") as embeddings:
                self.addCleanup(rag.index.cache_clear)
                rag.index.cache_clear()
                model = embeddings.return_value
                model.embed_documents.side_effect = [[[1., 0.] for _ in range(32)], ValueError("interrupted")]
                with self.assertRaisesRegex(ValueError, "interrupted"):
                    rag.ensure_index()
                with self.assertRaises(rag.IncompleteIndex):
                    rag.index()
                model.embed_documents.side_effect = lambda docs: [[1., 0.] for _ in docs]
                count = rag.ensure_index().count()
                self.assertGreater(count, 32)
                rag.export_seed()
                rag.index.cache_clear()
                with patch.dict(os.environ, VECTOR_DB_DIR=str(root / "second")):
                    model.embed_documents.side_effect = AssertionError("unexpected embedding request")
                    model.embed_query.return_value = [1., 0.]
                    self.assertEqual(rag.ensure_index().count(), count)
                    self.assertTrue(rag.search_pdf("early blight", "tomato"))

