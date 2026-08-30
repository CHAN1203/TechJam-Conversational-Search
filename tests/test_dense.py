from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starter.dense import DenseIndex


PARENT_ASINS = ["SHOE", "JACKET", "BELT", "HAT"]
TEXTS = [
    "Running shoe athletic sneaker footwear jogging trainer",
    "Winter jacket coat outerwear insulated warm",
    "Leather belt buckle accessory waistband",
    "Wide brim hat sun protection headwear",
]


class DenseIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = DenseIndex(PARENT_ASINS, TEXTS, n_components=2)

    def test_finds_the_closest_matching_document(self) -> None:
        results = self.index.search("jogging trainer shoe", top_k=1)
        self.assertEqual(["SHOE"], results)

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.index.search("", top_k=4), [])

    def test_search_is_deterministic(self) -> None:
        first = self.index.search("warm winter coat", top_k=4)
        second = self.index.search("warm winter coat", top_k=4)
        self.assertEqual(first, second)

    def test_query_with_zero_vocabulary_overlap_returns_no_results(self) -> None:
        # None of these words appear anywhere in the fitted vocabulary, so
        # there is nothing meaningful to rank against -- empty is the
        # correct, safe answer, not a bug to paper over.
        results = self.index.search("zzz qqq xyzzy plugh", top_k=2)
        self.assertEqual([], results)

    def test_partially_matching_query_still_returns_results(self) -> None:
        results = self.index.search("shoe zzz qqq", top_k=2)
        self.assertEqual(2, len(results))

    def test_respects_top_k(self) -> None:
        results = self.index.search("shoe jacket belt hat", top_k=2)
        self.assertEqual(2, len(results))


class EmptyDenseIndexTest(unittest.TestCase):
    def test_empty_document_collection_does_not_crash(self) -> None:
        index = DenseIndex([], [])
        self.assertEqual(index.search("anything", top_k=5), [])
        self.assertIsNone(index.project("anything"))
        self.assertIsNone(index.vector_for("ANY"))


class DenseIndexSimilarityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = DenseIndex(PARENT_ASINS, TEXTS, n_components=2)

    def test_cosine_similarity_is_higher_for_the_related_document(self) -> None:
        query_vector = self.index.project("jogging trainer running")
        shoe_similarity = query_vector @ self.index.vector_for("SHOE")
        hat_similarity = query_vector @ self.index.vector_for("HAT")
        self.assertGreater(shoe_similarity, hat_similarity)

    def test_vector_for_an_unknown_parent_asin_returns_none(self) -> None:
        self.assertIsNone(self.index.vector_for("NOT-A-REAL-ASIN"))

    def test_project_of_an_empty_query_returns_none(self) -> None:
        self.assertIsNone(self.index.project(""))

    def test_project_of_a_zero_overlap_query_returns_none(self) -> None:
        self.assertIsNone(self.index.project("zzz qqq xyzzy"))


class LazyDenseImportTest(unittest.TestCase):
    """scikit-learn is required to build the dense index, not to import the Agent.

    E18 measured at a marginal 0.001723 in the merged system (T37) while being
    the project's entire third-party dependency. Deferring the import keeps the
    gain and makes every non-semantic configuration runnable on the standard
    library alone.
    """

    def _catalog(self, directory: str) -> Path:
        path = Path(directory) / "catalog.jsonl"
        path.write_text(json.dumps({
            "parent_asin": "A", "title": "leather belt", "categories": ["Belts"],
            "features": [], "details": {}, "store": "x", "description": "",
            "rating_number": 10, "average_rating": 4.5,
        }) + "\n", encoding="utf-8")
        return path

    def test_a_non_semantic_agent_builds_without_scikit_learn(self) -> None:
        from starter.agent import Agent
        with tempfile.TemporaryDirectory() as directory:
            catalog = self._catalog(directory)
            with patch.dict(sys.modules, {"starter.dense": None}):
                agent = Agent(catalog, semantic_weight=0.0, retrieval_mode="bm25")
            self.assertIsNone(agent.dense_index)

    def test_the_default_agent_does_need_it(self) -> None:
        # Guards against the deferral quietly turning E18 off.
        from starter.agent import Agent
        with tempfile.TemporaryDirectory() as directory:
            catalog = self._catalog(directory)
            with patch.dict(sys.modules, {"starter.dense": None}):
                with self.assertRaises(ImportError):
                    Agent(catalog)


if __name__ == "__main__":
    unittest.main()
